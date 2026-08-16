from jobsearcher.db.repository import update_offer_enrichment
from jobsearcher.enrich.apply_type import detect_apply_type, dismiss_cookie_banner
from jobsearcher.enrich.offer_details import parse_offer_details


def enrich_offer(page, context, conn, offer_id: int, url: str) -> None:
    """Loads an offer page, extracts details, detects apply_type, and
    writes the results to the offer's row (status becomes 'enriched')."""
    page.goto(url, wait_until="domcontentloaded", timeout=30000)
    page.wait_for_timeout(2000)  # let the SPA hydrate
    dismiss_cookie_banner(page)

    body_text = page.locator("body").inner_text()
    details = parse_offer_details(body_text)

    apply_result = detect_apply_type(page, context)

    update_offer_enrichment(
        conn,
        offer_id,
        seniority=details.seniority,
        employment_type=details.contract_type,
        salary_min=details.salary_min,
        salary_max=details.salary_max,
        currency=details.currency,
        remote_type=details.work_mode,
        tech_stack=details.tech_stack,
        apply_type=apply_result.apply_type,
    )
