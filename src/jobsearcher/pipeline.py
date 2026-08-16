from jobsearcher.db.repository import get_offer, update_offer_status
from jobsearcher.filter.engine import evaluate
from jobsearcher.ingest.gmail_ingest import fetch_and_store_new_offers


def run_once(conn, gmail_service, enrich_fn, filter_config, send_notification_fn) -> dict:
    """One full pass: ingest new offers, enrich each, filter, notify matches.

    enrich_fn(conn, offer_id, url) -> None: mutates the offer's enrichment
    fields via the repository. Decoupled from Playwright specifics so this
    orchestration is testable without a live browser.

    send_notification_fn(offer, match_result) -> None: sends the match
    notification. Decoupled from Gmail specifics for the same reason.
    """
    stats = {
        "ingested": 0, "enriched": 0, "matched": 0,
        "filtered_out": 0, "notified": 0, "enrichment_failed": 0,
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

        if result.matched:
            update_offer_status(conn, offer_id, "matched")
            stats["matched"] += 1
            send_notification_fn(offer, result)
            update_offer_status(conn, offer_id, "notified")
            stats["notified"] += 1
        else:
            update_offer_status(conn, offer_id, "filtered_out", filter_reasons=result.reasons)
            stats["filtered_out"] += 1

    return stats
