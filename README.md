# Job Search OS

Telegram-triggered job search agent for discovering remote roles, scoring fit with Gemini, saving matches to Supabase, and reporting back through Telegram. Plain Telegram messages are routed to a context-aware JOBOS chat assistant.

## Cloud Flow

```text
Telegram command
-> Supabase Edge Function
-> GitHub Actions workflow
-> Python agent
-> Supabase database + Telegram report
```

The Python runner is not always on. It starts when `/run` is sent through Telegram from the allowed chat, completes the pipeline, then exits.
Non-command Telegram messages are saved to Supabase and processed by a one-shot chat run.

## Repository

- GitHub: https://github.com/navr5135/JOB-OS
- Supabase project URL: https://yfxrysqwcacxwibilqvl.supabase.co

## Commands

```text
/run
/discover
/apply
/stop
/status
/jobs
/help
```

You can also send normal text, for example:

```text
What is going on inside JOBOS?
Send me the top jobs over email.
Find top AI operations news.
Check recent recruiter emails.
```

## Deployment Files

- `.github/workflows/agent-run.yml` - GitHub Actions runner
- `supabase/schema.sql` - Supabase database schema
- `supabase/functions/telegram-webhook/index.ts` - Telegram webhook trigger
- `CLOUD_DEPLOYMENT.md` - step-by-step deployment guide

## Secrets

Secrets are not committed. Use GitHub Actions secrets and Supabase Edge Function secrets for API keys and tokens.
