"""
One-off validation: run the full tailor_cv_for_offer pipeline against one
real offer — real LLM call, real PDF render, real Drive upload. Not part
of the app's runtime pipeline.
"""

import os
import sys
from datetime import datetime, timezone

import anthropic
import httpx
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from jobsearcher.db.database import connect, init_db  # noqa: E402
from jobsearcher.db.models import Offer  # noqa: E402
from jobsearcher.db.repository import get_offer, insert_offer  # noqa: E402
from jobsearcher.enrich.enrichment import enrich_offer  # noqa: E402
from jobsearcher.gmail.auth import get_drive_service  # noqa: E402
from jobsearcher.ssl_utils import build_combined_ca_bundle  # noqa: E402
from jobsearcher.tailor.cv_library import load_cv_library  # noqa: E402
from jobsearcher.tailor.tailor import tailor_cv_for_offer  # noqa: E402

load_dotenv()

URL = sys.argv[1] if len(sys.argv) > 1 else (
    "https://justjoin.it/job-offer/reply-polska-sp-z-o-o--senior-business-analyst-katowice-analytics-229f90b9"
)


def main():
    conn = connect(":memory:")
    init_db(conn)
    now = datetime.now(timezone.utc).isoformat()
    offer_id = insert_offer(
        conn,
        Offer(
            id=None, gmail_message_id="test", url=URL, title="placeholder", company="placeholder",
            category="test", description=None, seniority=None, employment_type=None, salary_min=None,
            salary_max=None, currency=None, location="placeholder", remote_type=None, tech_stack=[],
            apply_type=None, status="new", filter_reasons=[], first_seen_at=now, updated_at=now,
        ),
    )

    ca_bundle_path = os.environ.get("CA_BUNDLE_PATH") or None
    drive_service = get_drive_service(
        os.environ["GOOGLE_OAUTH_CLIENT_SECRETS_PATH"], os.environ["GOOGLE_OAUTH_TOKEN_PATH"], ca_bundle_path
    )
    http_client = httpx.Client(verify=build_combined_ca_bundle(ca_bundle_path)) if ca_bundle_path else None
    anthropic_client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"], http_client=http_client)
    library = load_cv_library("config/cv_library.yaml")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()
        enrich_offer(page, context, conn, offer_id, URL)
        browser.close()

    offer = get_offer(conn, offer_id)
    print(f"Enriched offer: {offer.title} at {offer.company}")
    print(f"Description length: {len(offer.description or '')} chars")

    cv = tailor_cv_for_offer(anthropic_client, drive_service, library, conn, offer, output_dir="scripts/_tailor_test_output")

    print(f"\nCV generated:")
    print(f"  local_file_path: {cv.local_file_path}")
    print(f"  drive_web_view_link: {cv.drive_web_view_link}")
    print(f"  bullet_ids_used: {cv.bullet_ids_used}")
    print(f"  llm_model_used: {cv.llm_model_used}")

    # Cleanup: remove the Drive file, since this is just a validation run.
    if cv.drive_file_id:
        drive_service.files().delete(fileId=cv.drive_file_id).execute()
        print("\nCleaned up test file from Drive.")


if __name__ == "__main__":
    main()
