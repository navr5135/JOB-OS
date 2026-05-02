"""Search and email tools for the JOBOS chat assistant."""
import re
from urllib.parse import quote_plus
from xml.etree import ElementTree

import requests
from bs4 import BeautifulSoup

import config
import llm
from integrations import gmail

EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")


def web_search(query, limit=5):
    res = requests.get(f"https://duckduckgo.com/html/?q={quote_plus(query)}",
                       headers={"User-Agent": "job-search-os"}, timeout=15)
    soup, results = BeautifulSoup(res.text, "html.parser"), []
    for item in soup.select(".result")[:limit]:
        title, snippet = item.select_one(".result__a"), item.select_one(".result__snippet")
        if title:
            results.append(f"- {title.get_text(' ', strip=True)}\n{title.get('href')}\n"
                           f"{snippet.get_text(' ', strip=True) if snippet else ''}")
    return "Web results:\n" + ("\n\n".join(results) if results else "No useful results found.")


def news_items(query, limit=5):
    url = f"https://news.google.com/rss/search?q={quote_plus(query)}&hl=en-US&gl=US&ceid=US:en"
    res = requests.get(url, headers={"User-Agent": "job-search-os"}, timeout=15)
    items = ElementTree.fromstring(res.content).findall(".//item")[:limit]
    return [(i.findtext("title") or "Untitled", i.findtext("link") or "") for i in items]


def news_search(query, limit=5):
    lines = [f"- {title}\n{link}" for title, link in news_items(query, limit)]
    return "Top news:\n" + ("\n\n".join(lines) if lines else "No news results found.")


def send_news_email(user_text, query, limit=10):
    recipient = extract_email(user_text) or config.RECIPIENT_EMAIL
    items = news_items(clean_news_query(query), limit)
    if not items:
        return "I could not find useful news results to email."
    if wants_report(user_text):
        body = news_report(user_text, items)
    else:
        body = "Top latest news\n\n" + "\n\n".join(f"{i}. {t}\n{u}" for i, (t, u) in enumerate(items, 1))
    ok = gmail.send_email(recipient, "JOBOS: Top Latest News", body)
    if not ok:
        return "I found the news, but could not send the email. Check Gmail credentials/logs."
    return f"Sent the top {len(items)} latest news items to {recipient}."


def extract_email(text):
    match = EMAIL_RE.search(text)
    return match.group(0) if match else None


def wants_report(text):
    return any(word in text.lower() for word in ("report", "write", "summary", "summarize", "words"))


def clean_news_query(text):
    if "latest news" in text.lower():
        return "latest news"
    text = EMAIL_RE.sub("", text)
    text = re.sub(r"\b(email|mail|send|share|save|future|personal|me|my)\b", " ", text, flags=re.I)
    return re.sub(r"\s+", " ", text).strip(" .,:;") or "latest news"


def news_report(user_text, items):
    sources = "\n".join(f"- {title}\n{url}" for title, url in items)
    prompt = (
        "Write a concise report of about 200 words for email. Be factual, mention if a claim is framed by reports "
        "rather than confirmed, and include a short Sources section with URLs. User request:\n"
        f"{user_text}\n\nSources:\n{sources}"
    )
    return llm.ask("You write crisp technology news briefings.", prompt) or "Top latest news\n\n" + sources
