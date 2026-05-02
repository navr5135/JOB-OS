"""Context-aware Telegram chat assistant for Job Search OS."""
import re
from urllib.parse import quote_plus
from xml.etree import ElementTree

import requests
from bs4 import BeautifulSoup

import config
import db
import llm
from integrations import gmail, telegram

SYSTEM_PROMPT = """
You are the Job Search OS assistant for Navaditya. Classify the user's intent.
Return JSON only with keys: intent, query, limit.
Valid intents: status, top_jobs, email_top_jobs, email_report, recent_email,
web_search, news_search, run_discovery, run_apply, run_pipeline, help, general.
Prefer command intents when the user asks you to do something concrete.
"""


def _pending_messages():
    if db.USE_SUPABASE:
        rows = db._request("GET", "chat_history", params={
            "select": "id,role,content",
            "order": "id.desc",
            "limit": "20",
        })
        rows = list(reversed(rows))
        last_assistant = max((r["id"] for r in rows if r["role"] == "assistant"), default=0)
        pending = [r["content"] for r in rows if r["role"] == "user" and r["id"] > last_assistant]
        return pending or ([rows[-1]["content"]] if rows and rows[-1]["role"] == "user" else [])

    rows = db.get_recent_chat_history(limit=10)
    return [rows[-1]["content"]] if rows and rows[-1]["role"] == "user" else []


def _top_jobs(limit=5):
    jobs = [j for j in db.get_all_jobs() if j.get("status") in ("new", "applied")]
    jobs.sort(key=lambda j: int(j.get("score") or 0), reverse=True)
    return jobs[:limit]


def _format_jobs(jobs):
    if not jobs:
        return "No matching jobs are saved yet."
    lines = []
    for i, job in enumerate(jobs, 1):
        lines.append(
            f"{i}. {job['title']} @ {job['company']} | Score: {job.get('score', 'n/a')}\n{job['url']}"
        )
    return "\n\n".join(lines)


def _status_text():
    stats = db.get_database_stats()
    jobs = _top_jobs(3)
    parts = [f"{k}: {v}" for k, v in sorted(stats.items())]
    return (
        "JOBOS status\n"
        f"Jobs by status: {', '.join(parts) if parts else 'none yet'}\n"
        f"LLM calls left this run: {llm.calls_remaining()}\n\n"
        f"Top matches:\n{_format_jobs(jobs)}"
    )


def _send_top_jobs_email(limit=10):
    jobs = _top_jobs(limit)
    if not jobs:
        return "I could not find saved jobs to email yet."
    body = "Job Search OS - Top Matches\n\n" + _format_jobs(jobs)
    ok = gmail.send_email(config.RECIPIENT_EMAIL, "Job Search OS: Top Matches", body)
    return "Sent your top jobs over email." if ok else "I could not send the email. Check Gmail credentials/logs."


def _send_report_email():
    body = _status_text()
    ok = gmail.send_email(config.RECIPIENT_EMAIL, "Job Search OS: Status Report", body)
    return "Sent the JOBOS status report over email." if ok else "I could not send the report email."


def _recent_email_text():
    messages = gmail.get_recent_emails(
        query='newer_than:14d (recruiter OR hiring OR interview OR application OR "next steps")',
        limit=5,
    )
    return "Recent relevant emails:\n" + "\n\n".join(f"- {m}" for m in messages)


def _web_search(query, limit=5):
    url = f"https://duckduckgo.com/html/?q={quote_plus(query)}"
    res = requests.get(url, headers={"User-Agent": "job-search-os"}, timeout=15)
    soup = BeautifulSoup(res.text, "html.parser")
    results = []
    for item in soup.select(".result")[:limit]:
        title = item.select_one(".result__a")
        snippet = item.select_one(".result__snippet")
        if title:
            results.append(f"- {title.get_text(' ', strip=True)}\n{title.get('href')}\n{snippet.get_text(' ', strip=True) if snippet else ''}")
    return "Web results:\n" + ("\n\n".join(results) if results else "No useful results found.")


def _news_search(query, limit=5):
    url = f"https://news.google.com/rss/search?q={quote_plus(query)}&hl=en-US&gl=US&ceid=US:en"
    res = requests.get(url, headers={"User-Agent": "job-search-os"}, timeout=15)
    root = ElementTree.fromstring(res.content)
    items = root.findall(".//item")[:limit]
    lines = [f"- {i.findtext('title')}\n{i.findtext('link')}" for i in items]
    return "Top news:\n" + ("\n\n".join(lines) if lines else "No news results found.")


def _classify(user_text):
    fallback = _heuristic_intent(user_text)
    if not llm.can_call():
        return fallback
    payload = llm.ask_json(SYSTEM_PROMPT, user_text, model=llm.FAST_MODEL)
    if not payload:
        return fallback
    return {
        "intent": payload.get("intent") or fallback["intent"],
        "query": payload.get("query") or fallback["query"],
        "limit": _safe_limit(payload.get("limit") or fallback["limit"]),
    }


def _safe_limit(value):
    try:
        return max(1, min(int(value), 10))
    except (TypeError, ValueError):
        return 5


def _heuristic_intent(text):
    lower = text.lower()
    intent = "general"
    if "email" in lower and ("top job" in lower or "best job" in lower):
        intent = "email_top_jobs"
    elif "report" in lower and "email" in lower:
        intent = "email_report"
    elif "gmail" in lower or "email" in lower or "inbox" in lower:
        intent = "recent_email"
    elif "news" in lower:
        intent = "news_search"
    elif "search" in lower or "web" in lower or "latest" in lower:
        intent = "web_search"
    elif "discover" in lower:
        intent = "run_discovery"
    elif "apply" in lower or "application" in lower:
        intent = "run_apply"
    elif "run" in lower and "pipeline" in lower:
        intent = "run_pipeline"
    elif "status" in lower or "going on" in lower or "inside" in lower:
        intent = "status"
    elif "top job" in lower or "best job" in lower or "matches" in lower:
        intent = "top_jobs"
    elif "help" in lower or "what can you do" in lower:
        intent = "help"
    return {"intent": intent, "query": text, "limit": 5}


def _general_answer(user_text):
    history = db.get_recent_chat_history(limit=10)
    context = _status_text()
    prompt = (
        "You are JOBOS, a context-aware job-search operating assistant. "
        "Answer briefly, use the OS context, and suggest a next action when useful.\n\n"
        f"Current OS context:\n{context}"
    )
    return llm.ask(prompt, user_text, history=history) or "I could not reach Gemini for that answer right now."


def run_chat_once():
    messages = _pending_messages()
    if not messages:
        telegram.send_message("I do not see a new chat message to answer.")
        return
    user_text = "\n".join(messages).strip()
    decision = _classify(user_text)
    intent, query, limit = decision["intent"], decision["query"], decision["limit"]
    print(f"Chat intent: {intent} | query={query}")
    actions = {
        "status": lambda: _status_text(),
        "top_jobs": lambda: _format_jobs(_top_jobs(limit)),
        "email_top_jobs": lambda: _send_top_jobs_email(limit=10),
        "email_report": _send_report_email,
        "recent_email": _recent_email_text,
        "web_search": lambda: _web_search(query),
        "news_search": lambda: _news_search(query),
        "run_discovery": lambda: "Starting discovery now.\n" + _run_os_command("discover"),
        "run_apply": lambda: "Starting application writing now.\n" + _run_os_command("apply"),
        "run_pipeline": lambda: "Starting the full pipeline now.\n" + _run_os_command("run"),
        "help": _help_text,
    }
    response = actions.get(intent, lambda: _general_answer(user_text))()
    db.append_chat_history("assistant", response)
    telegram.send_message(response)


def _run_os_command(command):
    import orchestrator
    orchestrator.run_now(command)
    return "Done. I sent the run report separately if Telegram reporting is configured."


def _help_text():
    return re.sub(r"\n{3,}", "\n\n", """
I can talk through JOBOS state, explain matches, show top jobs, email reports,
check recent recruiter-like Gmail messages, search the web/news, and trigger
discovery, application writing, or the full pipeline.
""").strip()
