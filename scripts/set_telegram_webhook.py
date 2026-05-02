"""
Registers the Supabase Edge Function as the Telegram webhook.
"""
import os
import sys

import requests
from dotenv import load_dotenv

load_dotenv()


def main():
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    webhook_url = os.getenv("TELEGRAM_WEBHOOK_URL")

    if not token or not webhook_url:
        print("Set TELEGRAM_BOT_TOKEN and TELEGRAM_WEBHOOK_URL first.")
        sys.exit(1)

    response = requests.post(
        f"https://api.telegram.org/bot{token}/setWebhook",
        json={"url": webhook_url},
        timeout=20,
    )
    print(response.status_code)
    print(response.text)
    response.raise_for_status()


if __name__ == "__main__":
    main()
