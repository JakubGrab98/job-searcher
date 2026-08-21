"""
One-off recovery: re-tailor the offers that got notified today with
"CV not available" due to the nested-Playwright bug (now fixed), and send
a follow-up email with the actual CV link for each. Not part of the app's
runtime pipeline — a fixed pipeline run will never revisit these offers on
its own, since their source alert emails are already marked read.
"""

import os
import sys

import anthropic
import httpx
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from jobsearcher.db.database import connect  # noqa: E402
from jobsearcher.db.repository import get_offer, list_offers_by_status  # noqa: E402
from jobsearcher.gmail.auth import get_drive_service, get_gmail_service  # noqa: E402
from jobsearcher.gmail.send import send_email  # noqa: E402
from jobsearcher.ssl_utils import build_combined_ca_bundle  # noqa: E402
from jobsearcher.tailor.cv_library import load_cv_library  # noqa: E402
from jobsearcher.tailor.cv_render import render_cv_pdf  # noqa: E402
from jobsearcher.tailor.tailor import tailor_cv_for_offer  # noqa: E402

load_dotenv()


def main():
    db_path = os.environ.get("DATABASE_PATH", "./data/jobsearcher.db")
    conn = connect(db_path)

    notified_offers = list_offers_by_status(conn, "notified")
    print(f"Found {len(notified_offers)} 'notified' offers to check.")

    client_secrets_path = os.environ["GOOGLE_OAUTH_CLIENT_SECRETS_PATH"]
    token_path = os.environ["GOOGLE_OAUTH_TOKEN_PATH"]
    ca_bundle_path = os.environ.get("CA_BUNDLE_PATH") or None
    notify_email = os.environ["NOTIFY_EMAIL"]

    gmail_service = get_gmail_service(client_secrets_path, token_path, ca_bundle_path)
    drive_service = get_drive_service(client_secrets_path, token_path, ca_bundle_path)

    http_client = httpx.Client(verify=build_combined_ca_bundle(ca_bundle_path)) if ca_bundle_path else None
    anthropic_client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"], http_client=http_client)
    cv_library = load_cv_library("config/cv_library.yaml")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)

        def render_pdf_fn(html, output_path):
            render_cv_pdf(html, output_path, browser=browser)

        for offer in notified_offers:
            print(f"\nTailoring offer {offer.id}: {offer.title} at {offer.company}")
            try:
                cv = tailor_cv_for_offer(
                    anthropic_client, drive_service, cv_library, conn, offer, render_pdf_fn=render_pdf_fn
                )
            except Exception as e:
                print(f"  FAILED again: {e}")
                continue

            print(f"  CV ready: {cv.drive_web_view_link}")

            subject = f"[job-searcher] CV now ready: {offer.title} at {offer.company}"
            body = (
                f"The CV that failed to generate earlier today is ready now "
                f"(fixed a bug in the tailoring pipeline).\n\n"
                f"{offer.title} at {offer.company}\n"
                f"Link: {offer.url}\n\n"
                f"Tailored CV: {cv.drive_web_view_link}\n"
            )
            send_email(gmail_service, notify_email, subject, body)
            print("  Follow-up email sent.")

        browser.close()

    conn.close()


if __name__ == "__main__":
    main()
