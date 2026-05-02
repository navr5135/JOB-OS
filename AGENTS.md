# Job Search OS - Agent Instructions

## Project Overview
An autonomous, cloud-triggered job search agent for a solo portfolio project.
It discovers listings, scores fit, drafts application material, syncs state, and
reports back through Telegram.

## Current Architecture
- Language: Python 3.11+
- LLM: Gemini API through `llm.py`
- Database: Supabase Postgres through `db.py`
- Trigger: Telegram webhook hosted as a Supabase Edge Function
- Runner: GitHub Actions workflow, started on demand or by schedule
- Integrations: Telegram, Gmail API, Notion API
- Scraping: requests + BeautifulSoup

## Runtime Flow
1. User sends `/run <password>` to Telegram.
2. Supabase Edge Function validates `TELEGRAM_CHAT_ID` and `COMMAND_PASSWORD`.
3. Edge Function starts `.github/workflows/agent-run.yml`.
4. GitHub Actions runs `python main.py --once`.
5. The Python agent calls Gemini, writes to Supabase, and sends Telegram reports.
6. The workflow exits, so there is no always-on Python server.

## Rules For Agents
- All AI calls must go through `llm.py`.
- Never call Claude or OpenAI APIs from this project.
- Store secrets in environment variables or platform secrets, never in code.
- Use Supabase as the cloud database when Supabase env vars are present.
- SQLite fallback is allowed only for local development/testing.
- Every agent should log actions to console with timestamps where practical.
- Keep each file under 200 lines when editing or creating files.
- Update `requirements.txt` after adding dependencies.

## Security Rules
- Telegram commands must validate both chat id and command password.
- Never expose service-role keys in frontend/client code.
- Do not commit `.env`, `token.json`, `credentials.json`, or database files.
- Treat generated application content and email data as private.
