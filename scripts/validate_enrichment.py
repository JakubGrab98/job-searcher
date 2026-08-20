"""
One-off validation: run enrich_offer end-to-end against a real offer page
and a throwaway in-memory DB, then print the resulting stored offer.
Not part of the app's runtime pipeline.
"""

import os
import sys
from datetime import datetime, timezone

from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from jobsearcher.db.database import connect, init_db  # noqa: E402
from jobsearcher.db.models import Offer  # noqa: E402
from jobsearcher.db.repository import get_offer, insert_offer  # noqa: E402
from jobsearcher.enrich.enrichment import enrich_offer  # noqa: E402

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
            category="Analytics", description=None, seniority=None, employment_type=None, salary_min=None, salary_max=None,
            currency=None, location="Katowice", remote_type=None, tech_stack=[], apply_type=None,
            status="new", filter_reasons=[], first_seen_at=now, updated_at=now,
        ),
    )

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()
        enrich_offer(page, context, conn, offer_id, URL)
        browser.close()

    offer = get_offer(conn, offer_id)
    print("status:", offer.status)
    print("seniority:", offer.seniority)
    print("employment_type:", offer.employment_type)
    print("salary_min/max/currency:", offer.salary_min, offer.salary_max, offer.currency)
    print("remote_type:", offer.remote_type)
    print("tech_stack:", offer.tech_stack)
    print("apply_type:", offer.apply_type)
    print("location (should be untouched):", offer.location)


if __name__ == "__main__":
    main()
