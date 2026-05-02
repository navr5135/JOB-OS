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

EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
SYSTEM_PROMPT = """
You are the Job Search OS assistant for Navaditya. Classify the user's intent.
Return JSON only with keys: intent, query, limit. Valid intents: status,
top_jobs, email_top_jobs, email_report, recent_email, email_news, web_search,
news_search, run_discovery, run_apply, run_pipeline, help, general.
"""


def _pending_messages():
    if db.USE_SUPABASE:
        rows = db._request("GET", "chat_history", params={
            "select": "id,role,content", "order": "id.desc", "limit": "20",
        })
        rows = list(reversed(rows))
        last = max((r["id"] for r in rows if r["role"] == "assistant"), default=0)
        pending = [r["content"] for r in rows if r["role"] == "user" and r["id"] > last]
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
    return "\n\n".join(
        f"{i}. {j['title']} @ {j['company']} | Score: {j.get('score', 'n/a')}\n{j['url']}"
        for i, j in enumerate(jobs, 1)
    )


def _status_text():
    stats = db.get_database_stats()
    parts = [f"{k}: {v}" for k, v in sorted(stats.items())]
    return (
        "JOBOS status\n"
        f"Jobs by status: {', '.join(parts) if parts else 'none yet'}\n"
        f"LLM calls left this run: {llm.calls_remaining()}\n\n"
        f"Top matches:\n{_format_jobs(_top_jobs(3))}"
    )


def _send_top_jobs_email(limit=10):
    jobs = _top_jobs(limit)
    if not jobs:
        return "I could not find saved jobs to email yet."
    ok = gmail.send_email(config.RECIPIENT_EMAIL, "Job Search OS: Top Matches",
                          "Job Search OS - Top Matches\n\n" + _format_jobs(jobs))
    return "Sent your top jobs over email." if ok else "I could not send the email. Check Gmail credentials/logs."


def _send_report_email():
    ok = gmail.send_email(config.RECIPIENT_EMAIL, "Job Search OS: Status Report", _status_text())
    return "Sent the JOBOS status report over email." if ok else "I could not send the report email."


def _recent_email_text():
    msgs = gmail.get_recent_emails(
        query='newer_than:14d (recruiter OR hiring OR interview OR application OR "next steps")',
        limit=5,
    )
    return "Recent relevant emails:\n" + "\n\n".join(f"- {m}" for m in msgs)


def _extract_email(text):
    match = EMAIL_RE.search(text)
    return match.group(0) if match else None


def _web_search(query, limit=5):
    res = requests.get(
        f"https://duckduckgo.com/html/?q={quote_plus(query)}",
        headers={"User-Agent": "job-search-os"},
        timeout=15,
    )
    soup, results = BeautifulSoup(res.text, "html.parser"), []
    for item in soup.select(".result")[:limit]:
        title, snippet = item.select_one(".result__a"), item.select_one(".result__snippet")
        if title:
            results.append(
                f"- {title.get_text(' ', strip=True)}\n{title.get('href')}\n"
                f"{snippet.get_text(' ', strip=True) if snippet else ''}"
            )
    return "Web results:\n" + ("\n\n".join(results) if results else "No useful results found.")


def _news_items(query, limit=5):
    url = f"https://news.google.com/rss/search?q={quote_plus(query)}&hl=en-US&gl=US&ceid=US:en"
    res = requests.get(url, headers={"User-Agent": "job-search-os"}, timeout=15)
    items = ElementTree.fromstring(res.content).findall(".//item")[:limit]
    return [(i.findtext("title") or "Untitled", i.findtext("link") or "") for i in items]


def _news_search(query, limit=5):
    lines = [f"- {title}\n{link}" for title, link in _news_items(query, limit)]
    return "Top news:\n" + ("\n\n".join(lines) if lines else "No news results found.")


def _clean_news_query(text):
    if "latest news" in text.lower():
        return "latest news"
    text = EMAIL_RE.sub("", text)
    text = re.sub(r"\b(email|mail|send|share|save|future|personal|me|my)\b", " ", text, flags=re.I)
    return re.sub(r"\s+", " ", text).strip(" .,:;") or "latest news"


def _send_news_email(user_text, query, limit=10):
    recipient = _extract_email(user_text) or config.RECIPIENT_EMAIL
    items = _news_items(_clean_news_query(query), limit)
    if not items:
        return "I could not find useful news results to email."
    body = "Top latest news\n\n" + "\n\n".join(f"{i}. {t}\n{u}" for i, (t, u) in enumerate(items, 1))
    ok = gmail.send_email(recipient, "JOBOS: Top Latest News", body)
    if not ok:
        return "I found the news, but could not send the email. Check Gmail credentials/logs."
    return f"Sent the top {len(items)} latest news items to {recipient}."


def _safe_limit(value):
    try:
        return max(1, min(int(value), 10))
    except (TypeError, ValueError):
        return 5


def _heuristic_intent(text):
    lower, intent = text.lower(), "general"
    limit_match = re.search(r"\btop\s+(\d{1,2})\b", lower)
    if ("email" in lower or "mail" in lower or "send" in lower) and "news" in lower:
        intent = "email_news"
    elif "email" in lower and ("top job" in lower or "best job" in lower):
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
    return {"intent": intent, "query": text, "limit": _safe_limit(limit_match.group(1) if limit_match else 5)}


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


def _general_answer(user_text):
    prompt = ("You are JOBOS, a context-aware job-search operating assistant. "
              "Answer briefly, use the OS context, and suggest a next action when useful.\n\n"
              f"Current OS context:\n{_status_text()}")
    return llm.ask(prompt, user_text, history=db.get_recent_chat_history(limit=10)) or "I could not reach Gemini."


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
        "email_news": lambda: _send_news_email(user_text, query, limit=10),
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
    return ("I can talk through JOBOS state, explain matches, show top jobs, email reports, "
            "check recent recruiter-like Gmail messages, search the web/news, and trigger runs.")
