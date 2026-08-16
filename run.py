"""
Real production entrypoint: one full pass of ingest -> enrich -> filter ->
notify against live Gmail and justjoin.it. Intended to be run on a schedule
(e.g. Windows Task Scheduler).

Run: .venv/Scripts/python.exe run.py
"""

import os

from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

from jobsearcher.db.database import connect, init_db
from jobsearcher.enrich.enrichment import enrich_offer
from jobsearcher.filter.config import load_filter_config
from jobsearcher.gmail.auth import get_gmail_service
from jobsearcher.gmail.send import send_email
from jobsearcher.notify.notification import build_match_notification
from jobsearcher.pipeline import run_once

load_dotenv()


def main():
    db_path = os.environ.get("DATABASE_PATH", "./data/jobsearcher.db")
    os.makedirs(os.path.dirname(db_path) or ".", exist_ok=True)
    conn = connect(db_path)
    init_db(conn)

    filter_config = load_filter_config("config/filters.yaml")

    client_secrets_path = os.environ["GOOGLE_OAUTH_CLIENT_SECRETS_PATH"]
    token_path = os.environ["GOOGLE_OAUTH_TOKEN_PATH"]
    ca_bundle_path = os.environ.get("CA_BUNDLE_PATH") or None
    gmail_service = get_gmail_service(client_secrets_path, token_path, ca_bundle_path)

    notify_email = os.environ["NOTIFY_EMAIL"]

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()

        def enrich_fn(conn, offer_id, url):
            page = context.new_page()
            try:
                enrich_offer(page, context, conn, offer_id, url)
            finally:
                page.close()

        def send_notification_fn(offer, match_result):
            subject, body = build_match_notification(offer, match_result)
            send_email(gmail_service, notify_email, subject, body)

        stats = run_once(conn, gmail_service, enrich_fn, filter_config, send_notification_fn)

        browser.close()

    conn.close()
    print(f"Run complete: {stats}")


if __name__ == "__main__":
    main()
