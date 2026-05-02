"""
Database access layer for Job Search OS.

Uses Supabase PostgREST when SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY are set.
Falls back to local SQLite so the project remains easy to test on a laptop.
"""
import json
import os
import sqlite3
from datetime import datetime

import requests
from dotenv import load_dotenv

load_dotenv()

DB_NAME = "jobs.db"
SUPABASE_URL = os.getenv("SUPABASE_URL", "").rstrip("/")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_ANON_KEY")
USE_SUPABASE = bool(SUPABASE_URL and SUPABASE_KEY)


def _headers(extra=None):
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
    }
    if extra:
        headers.update(extra)
    return headers


def _endpoint(table):
    return f"{SUPABASE_URL}/rest/v1/{table}"


def _request(method, table, params=None, payload=None, prefer=None):
    headers = _headers({"Prefer": prefer} if prefer else None)
    response = requests.request(
        method,
        _endpoint(table),
        headers=headers,
        params=params,
        json=payload,
        timeout=30,
    )
    if response.status_code >= 400:
        raise RuntimeError(f"Supabase {method} {table} failed: {response.status_code} {response.text}")
    if response.text:
        return response.json()
    return []


def get_connection():
    return sqlite3.connect(DB_NAME)


def init_db():
    if USE_SUPABASE:
        print("Supabase database configured. Run supabase/schema.sql once in the dashboard.")
        return

    query = """
    CREATE TABLE IF NOT EXISTS jobs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        company TEXT NOT NULL,
        url TEXT UNIQUE NOT NULL,
        description TEXT,
        score INTEGER,
        status TEXT DEFAULT 'new',
        applied_at TEXT,
        notes TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        last_seen DATE DEFAULT CURRENT_DATE
    )
    """
    with get_connection() as conn:
        conn.execute(query)
        conn.execute("""
        CREATE TABLE IF NOT EXISTS chat_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
        conn.execute("""
        CREATE TABLE IF NOT EXISTS vector_memory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            topic TEXT NOT NULL,
            content TEXT NOT NULL,
            embedding TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
    print(f"Database '{DB_NAME}' initialized.")


def insert_job(title, company, url, description=None, score=None, status="new", notes=None):
    if USE_SUPABASE:
        payload = {
            "title": title,
            "company": company,
            "url": url,
            "description": description,
            "score": score,
            "status": status,
            "notes": notes,
        }
        try:
            _request("POST", "jobs", payload=payload, prefer="return=minimal")
            return True
        except RuntimeError as exc:
            if "23505" in str(exc) or "duplicate key" in str(exc):
                update_last_seen(url)
                return False
            raise

    query = "INSERT INTO jobs (title, company, url, description, score, status, notes) VALUES (?, ?, ?, ?, ?, ?, ?)"
    try:
        with get_connection() as conn:
            conn.execute(query, (title, company, url, description, score, status, notes))
        return True
    except sqlite3.IntegrityError:
        update_last_seen(url)
        return False


def update_last_seen(url):
    today = datetime.now().date().isoformat()
    if USE_SUPABASE:
        _request("PATCH", "jobs", params={"url": f"eq.{url}"}, payload={"last_seen": today}, prefer="return=minimal")
        return
    with get_connection() as conn:
        conn.execute("UPDATE jobs SET last_seen = CURRENT_DATE WHERE url = ?", (url,))


def get_seen_urls():
    if USE_SUPABASE:
        rows = _request("GET", "jobs", params={"select": "url"})
        return {row["url"] for row in rows if row.get("url")}
    with get_connection() as conn:
        cursor = conn.execute("SELECT url FROM jobs")
        return {row[0] for row in cursor.fetchall()}


def update_status(job_id, status, notes=None):
    applied_at = datetime.now().isoformat() if status == "applied" else None
    if USE_SUPABASE:
        current = _request("GET", "jobs", params={"id": f"eq.{job_id}", "select": "notes"})
        old_notes = (current[0].get("notes") if current else "") or ""
        payload = {"status": status}
        if applied_at:
            payload["applied_at"] = applied_at
        if notes:
            payload["notes"] = f"{old_notes}\n{notes}".strip()
        _request("PATCH", "jobs", params={"id": f"eq.{job_id}"}, payload=payload, prefer="return=minimal")
        return

    if notes:
        query = "UPDATE jobs SET status = ?, applied_at = COALESCE(?, applied_at), notes = COALESCE(notes, '') || '\n' || ? WHERE id = ?"
        params = (status, applied_at, notes, job_id)
    else:
        query = "UPDATE jobs SET status = ?, applied_at = COALESCE(?, applied_at) WHERE id = ?"
        params = (status, applied_at, job_id)
    with get_connection() as conn:
        conn.execute(query, params)


def get_jobs_by_status(status):
    if USE_SUPABASE:
        return _request("GET", "jobs", params={"status": f"eq.{status}", "select": "*", "order": "created_at.asc"})
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        return [dict(row) for row in conn.execute("SELECT * FROM jobs WHERE status = ?", (status,)).fetchall()]


def get_all_jobs():
    if USE_SUPABASE:
        return _request("GET", "jobs", params={"select": "*", "order": "created_at.asc"})
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        return [dict(row) for row in conn.execute("SELECT * FROM jobs").fetchall()]


def get_database_stats():
    stats = {}
    for job in get_all_jobs():
        status = job.get("status") or "unknown"
        stats[status] = stats.get(status, 0) + 1
    return stats


def append_chat_history(role, content):
    if USE_SUPABASE:
        _request("POST", "chat_history", payload={"role": role, "content": content}, prefer="return=minimal")
        return
    with get_connection() as conn:
        conn.execute("INSERT INTO chat_history (role, content) VALUES (?, ?)", (role, content))


def get_recent_chat_history(limit=10):
    if USE_SUPABASE:
        rows = _request("GET", "chat_history", params={"select": "role,content", "order": "id.desc", "limit": str(limit)})
        return list(reversed(rows))
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        rows = [dict(row) for row in conn.execute("SELECT role, content FROM chat_history ORDER BY id DESC LIMIT ?", (limit,))]
        return list(reversed(rows))


def insert_vector_memory(topic, content, embedding_list):
    if USE_SUPABASE:
        _request("POST", "vector_memory", payload={"topic": topic, "content": content, "embedding": embedding_list}, prefer="return=minimal")
        return
    with get_connection() as conn:
        conn.execute("INSERT INTO vector_memory (topic, content, embedding) VALUES (?, ?, ?)", (topic, content, json.dumps(embedding_list)))


def get_all_vector_memories():
    if USE_SUPABASE:
        return _request("GET", "vector_memory", params={"select": "id,topic,content,embedding,created_at"})
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        rows = []
        for row in conn.execute("SELECT id, topic, content, embedding, created_at FROM vector_memory"):
            item = dict(row)
            item["embedding"] = json.loads(item["embedding"])
            rows.append(item)
        return rows
