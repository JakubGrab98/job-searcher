"""
One-off helper: authenticate to Gmail and dump the most recent justjoin.it
alert email (subject/body) to tests/fixtures/sample_alert_email.* so the
ingestion email parser can be built against a real example instead of a
guess. Not part of the app's runtime pipeline.

Run: .venv/Scripts/python.exe scripts/fetch_sample_alert.py
"""

import os
import sys

from dotenv import load_dotenv

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from jobsearcher.gmail.auth import get_gmail_service  # noqa: E402
from jobsearcher.gmail.messages import extract_bodies, get_header  # noqa: E402

load_dotenv()


def main():
    client_secrets_path = os.environ["GOOGLE_OAUTH_CLIENT_SECRETS_PATH"]
    token_path = os.environ["GOOGLE_OAUTH_TOKEN_PATH"]
    ca_bundle_path = os.environ.get("CA_BUNDLE_PATH") or None

    service = get_gmail_service(client_secrets_path, token_path, ca_bundle_path)

    results = (
        service.users()
        .messages()
        .list(userId="me", q="from:justjoin.it", maxResults=5)
        .execute()
    )
    messages = results.get("messages", [])

    if not messages:
        print("No emails found from justjoin.it. Broadening search to subject containing 'justjoin'...")
        results = (
            service.users()
            .messages()
            .list(userId="me", q="justjoin", maxResults=5)
            .execute()
        )
        messages = results.get("messages", [])

    if not messages:
        print("Still nothing found. Confirm the alert emails exist in this Gmail account.")
        return

    print(f"Found {len(messages)} candidate message(s). Fetching the most recent...")
    msg = service.users().messages().get(userId="me", id=messages[0]["id"], format="full").execute()

    headers = msg["payload"]["headers"]
    subject = get_header(headers, "Subject")
    sender = get_header(headers, "From")
    date = get_header(headers, "Date")

    text_plain, text_html = extract_bodies(msg["payload"])

    print(f"Subject: {subject}")
    print(f"From: {sender}")
    print(f"Date: {date}")

    fixtures_dir = os.path.join(os.path.dirname(__file__), "..", "tests", "fixtures")
    os.makedirs(fixtures_dir, exist_ok=True)

    if text_html:
        with open(os.path.join(fixtures_dir, "sample_alert_email.html"), "w", encoding="utf-8") as f:
            f.write(text_html)
        print(f"Wrote HTML body to tests/fixtures/sample_alert_email.html ({len(text_html)} chars)")
    if text_plain:
        with open(os.path.join(fixtures_dir, "sample_alert_email.txt"), "w", encoding="utf-8") as f:
            f.write(text_plain)
        print(f"Wrote plain-text body to tests/fixtures/sample_alert_email.txt ({len(text_plain)} chars)")
    if not text_html and not text_plain:
        print("Could not find a text/html or text/plain body part. Raw payload:")
        print(msg["payload"])


if __name__ == "__main__":
    main()
