param(
    [string]$ProjectRef = "yfxrysqwcacxwibilqvl"
)

$ErrorActionPreference = "Stop"

$envPath = Join-Path (Get-Location) ".env"
if (Test-Path $envPath) {
    Get-Content $envPath | ForEach-Object {
        $line = $_.Trim()
        if (-not $line -or $line.StartsWith("#") -or -not $line.Contains("=")) {
            return
        }
        $parts = $line.Split("=", 2)
        $name = $parts[0].Trim()
        $value = $parts[1].Trim().Trim('"').Trim("'")
        [Environment]::SetEnvironmentVariable($name, $value, "Process")
    }
}

$required = @(
    "SUPABASE_ACCESS_TOKEN",
    "SUPABASE_SERVICE_ROLE_KEY",
    "TELEGRAM_BOT_TOKEN",
    "TELEGRAM_CHAT_ID",
    "GITHUB_PAT"
)

foreach ($name in $required) {
    if (-not [Environment]::GetEnvironmentVariable($name)) {
        throw "Missing environment variable: $name"
    }
}

npx supabase login --token ${env:SUPABASE_ACCESS_TOKEN}
npx supabase link --project-ref $ProjectRef
npx supabase db push

npx supabase secrets set `
    TELEGRAM_BOT_TOKEN="${env:TELEGRAM_BOT_TOKEN}" `
    TELEGRAM_CHAT_ID="${env:TELEGRAM_CHAT_ID}" `
    GITHUB_OWNER="navr5135" `
    GITHUB_REPO="JOB-OS" `
    GITHUB_PAT="${env:GITHUB_PAT}" `
    GITHUB_WORKFLOW_FILE="agent-run.yml" `
    GITHUB_REF="main" `
    SUPABASE_URL="https://yfxrysqwcacxwibilqvl.supabase.co" `
    SUPABASE_SERVICE_ROLE_KEY="${env:SUPABASE_SERVICE_ROLE_KEY}"

npx supabase functions deploy telegram-webhook --no-verify-jwt

$webhookUrl = "https://yfxrysqwcacxwibilqvl.supabase.co/functions/v1/telegram-webhook"
Invoke-RestMethod `
    -Method Post `
    -Uri "https://api.telegram.org/bot${env:TELEGRAM_BOT_TOKEN}/setWebhook" `
    -ContentType "application/json" `
    -Body (@{ url = $webhookUrl } | ConvertTo-Json)
