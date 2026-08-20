from jobsearcher.db.repository import get_offer, update_offer_status
from jobsearcher.filter.engine import evaluate
from jobsearcher.ingest.gmail_ingest import fetch_and_store_new_offers


def run_once(conn, gmail_service, enrich_fn, filter_config, tailor_fn, send_notification_fn) -> dict:
    """One full pass: ingest new offers, enrich each, filter, tailor a CV for
    matches, notify.

    enrich_fn(conn, offer_id, url) -> None: mutates the offer's enrichment
    fields via the repository. Decoupled from Playwright specifics so this
    orchestration is testable without a live browser.

    tailor_fn(conn, offer) -> CvVersion: generates and logs a tailored CV
    for a matched offer. A failure here does NOT block the match
    notification — the offer stays notified with cv_version=None so you
    still hear about a good match even if CV generation had an issue.

    send_notification_fn(offer, match_result, cv_version) -> None: sends
    the match notification. Decoupled from Gmail specifics for the same
    reason as enrich_fn.
    """
    stats = {
        "ingested": 0, "enriched": 0, "matched": 0, "filtered_out": 0,
        "tailored": 0, "tailoring_failed": 0, "notified": 0, "enrichment_failed": 0,
    }

    new_offer_ids = fetch_and_store_new_offers(gmail_service, conn)
    stats["ingested"] = len(new_offer_ids)

    for offer_id in new_offer_ids:
        offer = get_offer(conn, offer_id)

        try:
            enrich_fn(conn, offer_id, offer.url)
            stats["enriched"] += 1
        except Exception as e:
            update_offer_status(conn, offer_id, "failed", filter_reasons=[f"enrichment failed: {e}"])
            stats["enrichment_failed"] += 1
            continue

        offer = get_offer(conn, offer_id)  # reload with enrichment fields
        result = evaluate(offer, filter_config)

        if not result.matched:
            update_offer_status(conn, offer_id, "filtered_out", filter_reasons=result.reasons)
            stats["filtered_out"] += 1
            continue

        update_offer_status(conn, offer_id, "matched")
        stats["matched"] += 1

        cv_version = None
        try:
            cv_version = tailor_fn(conn, offer)
            stats["tailored"] += 1
            update_offer_status(conn, offer_id, "tailored")
        except Exception as e:
            stats["tailoring_failed"] += 1
            update_offer_status(conn, offer_id, "matched", filter_reasons=[f"tailoring failed: {e}"])

        send_notification_fn(offer, result, cv_version)
        update_offer_status(conn, offer_id, "notified")
        stats["notified"] += 1

    return stats
