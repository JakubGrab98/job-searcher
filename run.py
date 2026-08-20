"""
Real production entrypoint: one full pass of ingest -> enrich -> filter ->
notify against live Gmail and justjoin.it. Intended to be run on a schedule
(e.g. Windows Task Scheduler).

Every run is logged to logs/run.log and recorded in the `runs` table. If
the run fails outright, a failure alert email is sent (best-effort — if
Gmail itself is what's broken, this can't succeed, and that failure is
just logged) so a broken pipeline gets noticed instead of silently
stopping forever.

Run: .venv/Scripts/python.exe run.py
"""

import logging
import logging.handlers
import os
import sys
import traceback

import anthropic
import httpx
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

from jobsearcher.db.database import connect, init_db
from jobsearcher.db.repository import fail_run, finish_run, start_run
from jobsearcher.enrich.enrichment import enrich_offer
from jobsearcher.filter.config import load_filter_config
from jobsearcher.gmail.auth import get_drive_service, get_gmail_service
from jobsearcher.gmail.send import send_email
from jobsearcher.notify.notification import build_failure_alert, build_match_notification
from jobsearcher.pipeline import run_once
from jobsearcher.ssl_utils import build_combined_ca_bundle
from jobsearcher.tailor.cv_library import load_cv_library
from jobsearcher.tailor.tailor import tailor_cv_for_offer

load_dotenv()


def _setup_logging() -> logging.Logger:
    os.makedirs("logs", exist_ok=True)
    file_handler = logging.handlers.RotatingFileHandler(
        "logs/run.log", maxBytes=2_000_000, backupCount=5, encoding="utf-8"
    )
    file_handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(logging.Formatter("%(message)s"))

    logger = logging.getLogger("jobsearcher")
    logger.setLevel(logging.INFO)
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    return logger


def main():
    logger = _setup_logging()

    db_path = os.environ.get("DATABASE_PATH", "./data/jobsearcher.db")
    os.makedirs(os.path.dirname(db_path) or ".", exist_ok=True)
    conn = connect(db_path)
    init_db(conn)

    run_id = start_run(conn)
    logger.info(f"Run {run_id} started")

    notify_email = os.environ["NOTIFY_EMAIL"]
    client_secrets_path = os.environ["GOOGLE_OAUTH_CLIENT_SECRETS_PATH"]
    token_path = os.environ["GOOGLE_OAUTH_TOKEN_PATH"]
    ca_bundle_path = os.environ.get("CA_BUNDLE_PATH") or None

    # Built first and outside the main try block: if Gmail auth itself is
    # what's broken, nothing below can send a failure alert either — that
    # failure just gets logged, since there's no way to email about email
    # being broken.
    gmail_service = get_gmail_service(client_secrets_path, token_path, ca_bundle_path)

    try:
        filter_config = load_filter_config("config/filters.yaml")
        drive_service = get_drive_service(client_secrets_path, token_path, ca_bundle_path)

        # anthropic's SDK uses httpx, which has its own cert handling
        # separate from requests (OAuth token exchange) and httplib2
        # (actual Gmail/Drive API calls) — same TLS-intercepting-AV story,
        # needs its own verify= override. Combined bundle, not the raw
        # intercepting cert alone — see ssl_utils.build_combined_ca_bundle.
        http_client = (
            httpx.Client(verify=build_combined_ca_bundle(ca_bundle_path)) if ca_bundle_path else None
        )
        anthropic_client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"], http_client=http_client)
        cv_library = load_cv_library("config/cv_library.yaml")

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context()

            def enrich_fn(conn, offer_id, url):
                page = context.new_page()
                try:
                    enrich_offer(page, context, conn, offer_id, url)
                finally:
                    page.close()

            def tailor_fn(conn, offer):
                return tailor_cv_for_offer(anthropic_client, drive_service, cv_library, conn, offer)

            def send_notification_fn(offer, match_result, cv_version):
                subject, body = build_match_notification(offer, match_result, cv_version)
                send_email(gmail_service, notify_email, subject, body)

            stats = run_once(conn, gmail_service, enrich_fn, filter_config, tailor_fn, send_notification_fn)

            browser.close()

        finish_run(conn, run_id, stats)
        logger.info(f"Run {run_id} completed: {stats}")

    except Exception as e:
        error_text = f"{e}\n{traceback.format_exc()}"
        logger.error(f"Run {run_id} failed: {error_text}")
        fail_run(conn, run_id, str(e))

        try:
            subject, body = build_failure_alert(str(e), run_id)
            send_email(gmail_service, notify_email, subject, body)
            logger.info("Failure alert sent")
        except Exception as alert_error:
            logger.error(f"Could not send failure alert: {alert_error}")

        raise
    finally:
        conn.close()


if __name__ == "__main__":
    main()
