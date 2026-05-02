# Job Search OS

Telegram-triggered job search agent for discovering remote roles, scoring fit with Gemini, saving matches to Supabase, and reporting back through Telegram.

## Cloud Flow

```text
Telegram command
-> Supabase Edge Function
-> GitHub Actions workflow
-> Python agent
-> Supabase database + Telegram report
```

The Python runner is not always on. It starts when `/run <password>` is sent through Telegram, completes the pipeline, then exits.

## Repository

- GitHub: https://github.com/navr5135/JOB-OS
- Supabase project URL: https://yfxrysqwcacxwibilqvl.supabase.co

## Commands

```text
/run <password>
/discover <password>
/apply <password>
/stop <password>
/status <password>
/jobs <password>
/help <password>
```

## Deployment Files

- `.github/workflows/agent-run.yml` - GitHub Actions runner
- `supabase/schema.sql` - Supabase database schema
- `supabase/functions/telegram-webhook/index.ts` - Telegram webhook trigger
- `CLOUD_DEPLOYMENT.md` - step-by-step deployment guide

## Secrets

Secrets are not committed. Use GitHub Actions secrets and Supabase Edge Function secrets for API keys, tokens, and passwords.
