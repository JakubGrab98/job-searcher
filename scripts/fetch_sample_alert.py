"""
One-off helper: authenticate to Gmail and inspect/download a justjoin.it
alert email. Not part of the app's runtime pipeline.

By default this only LISTS candidate messages (subject/from/date) — it does
NOT write anything, so it's safe to run repeatedly while investigating an
inbox. Use --save-index N to download message N (0-based, from the listed
results) to a scratch file, and --save-fixture on top of that to overwrite
the committed test fixture (tests/fixtures/sample_alert_email.html) — only
do that deliberately, since that file is depended on by the test suite.

Run: .venv/Scripts/python.exe scripts/fetch_sample_alert.py
     .venv/Scripts/python.exe scripts/fetch_sample_alert.py --query "subject:New jobs for you"
     .venv/Scripts/python.exe scripts/fetch_sample_alert.py --save-index 0
     .venv/Scripts/python.exe scripts/fetch_sample_alert.py --save-index 0 --save-fixture
"""

import argparse
import os
import sys

from dotenv import load_dotenv

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from jobsearcher.gmail.auth import get_gmail_service  # noqa: E402
from jobsearcher.gmail.messages import extract_bodies, get_header  # noqa: E402

load_dotenv()

DEFAULT_QUERY = "from:justjoin.it"
SCRATCH_HTML_PATH = "scripts/_last_fetched_alert.html"
SCRATCH_TXT_PATH = "scripts/_last_fetched_alert.txt"
FIXTURE_HTML_PATH = "tests/fixtures/sample_alert_email.html"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--query", default=DEFAULT_QUERY, help="Gmail search query")
    parser.add_argument("--max-results", type=int, default=10)
    parser.add_argument("--save-index", type=int, default=None, help="Download the Nth listed message (0-based)")
    parser.add_argument(
        "--save-fixture", action="store_true",
        help="Also overwrite the committed test fixture (only with --save-index)",
    )
    args = parser.parse_args()

    client_secrets_path = os.environ["GOOGLE_OAUTH_CLIENT_SECRETS_PATH"]
    token_path = os.environ["GOOGLE_OAUTH_TOKEN_PATH"]
    ca_bundle_path = os.environ.get("CA_BUNDLE_PATH") or None

    service = get_gmail_service(client_secrets_path, token_path, ca_bundle_path)

    results = service.users().messages().list(userId="me", q=args.query, maxResults=args.max_results).execute()
    message_refs = results.get("messages", [])

    if not message_refs:
        print(f"No messages matched query: {args.query!r}")
        return

    print(f"{len(message_refs)} message(s) matched query {args.query!r}:\n")
    messages = []
    for i, ref in enumerate(message_refs):
        msg = service.users().messages().get(userId="me", id=ref["id"], format="full").execute()
        headers = msg["payload"]["headers"]
        subject = get_header(headers, "Subject")
        sender = get_header(headers, "From")
        date = get_header(headers, "Date")
        print(f"  [{i}] {date} | {sender} | {subject}")
        messages.append(msg)

    if args.save_index is None:
        print("\nPass --save-index N to download one of these.")
        return

    msg = messages[args.save_index]
    text_plain, text_html = extract_bodies(msg["payload"])

    os.makedirs("scripts", exist_ok=True)
    if text_html:
        with open(SCRATCH_HTML_PATH, "w", encoding="utf-8") as f:
            f.write(text_html)
        print(f"\nWrote HTML body to {SCRATCH_HTML_PATH} ({len(text_html)} chars)")
    if text_plain:
        with open(SCRATCH_TXT_PATH, "w", encoding="utf-8") as f:
            f.write(text_plain)
        print(f"Wrote plain-text body to {SCRATCH_TXT_PATH} ({len(text_plain)} chars)")
    if not text_html and not text_plain:
        print("Could not find a text/html or text/plain body part.")
        return

    if args.save_fixture and text_html:
        os.makedirs(os.path.dirname(FIXTURE_HTML_PATH), exist_ok=True)
        with open(FIXTURE_HTML_PATH, "w", encoding="utf-8") as f:
            f.write(text_html)
        print(f"Also overwrote committed fixture: {FIXTURE_HTML_PATH}")


if __name__ == "__main__":
    main()
