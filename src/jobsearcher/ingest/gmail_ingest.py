from datetime import datetime, timezone

from jobsearcher.db.models import Offer
from jobsearcher.db.repository import insert_offer
from jobsearcher.gmail.messages import extract_bodies
from jobsearcher.ingest.email_parser import parse_category, parse_offer_cards

ALERT_QUERY = 'from:no-reply@justjoin.it subject:"New jobs for you" is:unread'


def fetch_and_store_new_offers(service, conn, query: str = ALERT_QUERY) -> list[int]:
    """Fetch unread justjoin.it alert emails, store their offers, mark each
    email read only after its offers are successfully stored. Returns the
    ids of offers inserted or already present (idempotent on offer URL)."""
    results = service.users().messages().list(userId="me", q=query).execute()
    message_refs = results.get("messages", [])

    offer_ids: list[int] = []
    now = datetime.now(timezone.utc).isoformat()

    for ref in message_refs:
        msg_id = ref["id"]
        msg = service.users().messages().get(userId="me", id=msg_id, format="full").execute()

        _, html = extract_bodies(msg["payload"])
        if html is None:
            continue

        category = parse_category(html)
        cards = parse_offer_cards(html)

        for card in cards:
            offer = Offer(
                id=None,
                gmail_message_id=msg_id,
                url=card.url,
                title=card.title,
                company=card.company,
                category=category,
                description=None,
                seniority=None,
                employment_type=None,
                salary_min=None,
                salary_max=None,
                currency=None,
                location=card.city,
                remote_type=None,
                tech_stack=[],
                apply_type=None,
                status="new",
                filter_reasons=[],
                first_seen_at=now,
                updated_at=now,
            )
            offer_ids.append(insert_offer(conn, offer))

        service.users().messages().modify(
            userId="me", id=msg_id, body={"removeLabelIds": ["UNREAD"]}
        ).execute()

    return offer_ids
