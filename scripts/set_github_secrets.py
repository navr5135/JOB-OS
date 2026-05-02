"""
Sets GitHub Actions secrets for the Job Search OS repository.

Requires:
    pip install -r requirements-deploy.txt
"""
import base64
import os
import sys

import requests
from dotenv import load_dotenv
from nacl import encoding, public

load_dotenv()

OWNER = os.getenv("GITHUB_OWNER", "navr5135")
REPO = os.getenv("GITHUB_REPO", "JOB-OS")
TOKEN = os.getenv("GITHUB_PAT")

SECRET_NAMES = [
    "GEMINI_API_KEY",
    "SUPABASE_URL",
    "SUPABASE_SERVICE_ROLE_KEY",
    "TELEGRAM_BOT_TOKEN",
    "TELEGRAM_CHAT_ID",
    "NOTION_API_KEY",
    "NOTION_DATABASE_ID",
    "RECIPIENT_EMAIL",
]
OPTIONAL_SECRET_NAMES = [
    "GMAIL_TOKEN_JSON",
]


def github_headers():
    if not TOKEN:
        print("Missing GITHUB_PAT.")
        sys.exit(1)
    return {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {TOKEN}",
        "X-GitHub-Api-Version": "2022-11-28",
    }


def encrypt_secret(public_key, value):
    key = public.PublicKey(public_key.encode("utf-8"), encoding.Base64Encoder())
    sealed_box = public.SealedBox(key)
    encrypted = sealed_box.encrypt(value.encode("utf-8"))
    return base64.b64encode(encrypted).decode("utf-8")


def main():
    headers = github_headers()
    key_url = f"https://api.github.com/repos/{OWNER}/{REPO}/actions/secrets/public-key"
    key_res = requests.get(key_url, headers=headers, timeout=20)
    key_res.raise_for_status()
    key_data = key_res.json()

    missing = [name for name in SECRET_NAMES if not os.getenv(name)]
    if missing:
        print("Missing local env vars: " + ", ".join(missing))
        sys.exit(1)

    for name in [*SECRET_NAMES, *OPTIONAL_SECRET_NAMES]:
        if not os.getenv(name):
            print(f"Skipping optional GitHub secret: {name}")
            continue
        encrypted_value = encrypt_secret(key_data["key"], os.environ[name])
        payload = {"encrypted_value": encrypted_value, "key_id": key_data["key_id"]}
        url = f"https://api.github.com/repos/{OWNER}/{REPO}/actions/secrets/{name}"
        res = requests.put(url, headers=headers, json=payload, timeout=20)
        res.raise_for_status()
        print(f"Set GitHub secret: {name}")


if __name__ == "__main__":
    main()
