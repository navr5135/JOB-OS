# Cloud Deployment

This setup runs Job Search OS without keeping your laptop on.

## Architecture

Telegram command -> Supabase Edge Function -> GitHub Actions -> Python agent -> Supabase + Telegram report.

The Python process only exists while GitHub Actions is running. After the run finishes, it shuts down automatically.

## Project Values

```text
GitHub owner: navr5135
GitHub repo: JOB-OS
GitHub URL: https://github.com/navr5135/JOB-OS
Supabase URL: https://yfxrysqwcacxwibilqvl.supabase.co
Supabase project ref: yfxrysqwcacxwibilqvl
Telegram webhook URL: https://yfxrysqwcacxwibilqvl.supabase.co/functions/v1/telegram-webhook
```

## 1. Supabase

1. Create a free Supabase project.
2. Open the SQL editor.
3. Run `supabase/schema.sql`.
4. Copy your project URL, anon key, and service role key.

## 2. GitHub Secrets

Add these repository secrets:

```text
GEMINI_API_KEY
SUPABASE_URL
SUPABASE_SERVICE_ROLE_KEY
TELEGRAM_BOT_TOKEN
TELEGRAM_CHAT_ID
NOTION_API_KEY
NOTION_DATABASE_ID
RECIPIENT_EMAIL
```

Notion and recipient email are optional if you do not use those reports.

## 3. Supabase Edge Function Secrets

Set these for `telegram-webhook`:

```text
TELEGRAM_BOT_TOKEN
TELEGRAM_CHAT_ID
COMMAND_PASSWORD
GITHUB_OWNER
GITHUB_REPO
GITHUB_PAT
GITHUB_WORKFLOW_FILE=agent-run.yml
GITHUB_REF=main
SUPABASE_URL
SUPABASE_SERVICE_ROLE_KEY
```

`GITHUB_PAT` needs permission to trigger and cancel Actions workflows.

## 4. Deploy The Edge Function

```bash
supabase functions deploy telegram-webhook --no-verify-jwt
```

Telegram cannot attach a Supabase JWT to webhook calls, so the function uses
your Telegram chat id and command password as the access gate.

Then set your Telegram webhook:

```bash
curl "https://api.telegram.org/bot<TELEGRAM_BOT_TOKEN>/setWebhook?url=https://<PROJECT_REF>.supabase.co/functions/v1/telegram-webhook"
```

Or set `TELEGRAM_WEBHOOK_URL` locally and run:

```bash
python scripts/set_telegram_webhook.py
```

## 5. Telegram Commands

```text
/run <password>
/stop <password>
/status <password>
/jobs <password>
/help <password>
```

`/run` starts the GitHub Actions workflow. `/stop` cancels active runs for the workflow. The runner exits automatically after each job, so there is no idle server to pay for.
