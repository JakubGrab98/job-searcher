from datetime import datetime, timezone

from jobsearcher.db.models import Offer, CvVersion, Application
from jobsearcher.db.repository import (
    insert_offer,
    get_offer_by_url,
    get_offer,
    update_offer_enrichment,
    update_offer_status,
    list_offers_by_status,
    insert_cv_version,
    insert_application,
)


def make_offer(url="https://justjoin.it/job-offer/example-data-engineer"):
    now = datetime.now(timezone.utc).isoformat()
    return Offer(
        id=None,
        gmail_message_id="msg-1",
        url=url,
        title="Data Engineer",
        company="Acme",
        category="data",
        seniority=None,
        employment_type=None,
        salary_min=None,
        salary_max=None,
        currency=None,
        location=None,
        remote_type=None,
        tech_stack=[],
        apply_type=None,
        status="new",
        filter_reasons=[],
        first_seen_at=now,
        updated_at=now,
    )


def test_insert_and_get_offer_by_url(conn):
    offer_id = insert_offer(conn, make_offer())
    fetched = get_offer_by_url(conn, "https://justjoin.it/job-offer/example-data-engineer")
    assert fetched is not None
    assert fetched.id == offer_id
    assert fetched.title == "Data Engineer"
    assert fetched.tech_stack == []


def test_insert_offer_is_idempotent_on_url(conn):
    first_id = insert_offer(conn, make_offer())
    second_id = insert_offer(conn, make_offer())
    assert first_id == second_id
    assert len(list_offers_by_status(conn, "new")) == 1


def test_update_offer_enrichment(conn):
    offer_id = insert_offer(conn, make_offer())
    update_offer_enrichment(
        conn,
        offer_id,
        seniority="mid",
        employment_type="b2b",
        salary_min=150,
        salary_max=200,
        currency="PLN",
        location="Warszawa",
        remote_type="hybrid",
        tech_stack=["python", "airflow", "snowflake"],
        apply_type="native",
    )
    fetched = get_offer(conn, offer_id)
    assert fetched.status == "enriched"
    assert fetched.tech_stack == ["python", "airflow", "snowflake"]
    assert fetched.apply_type == "native"


def test_update_offer_status_with_reasons(conn):
    offer_id = insert_offer(conn, make_offer())
    update_offer_status(conn, offer_id, "filtered_out", filter_reasons=["salary below floor"])
    fetched = get_offer(conn, offer_id)
    assert fetched.status == "filtered_out"
    assert fetched.filter_reasons == ["salary below floor"]


def test_list_offers_by_status(conn):
    insert_offer(conn, make_offer("https://justjoin.it/job-offer/a"))
    second = insert_offer(conn, make_offer("https://justjoin.it/job-offer/b"))
    update_offer_status(conn, second, "matched")
    assert [o.status for o in list_offers_by_status(conn, "new")] == ["new"]
    assert [o.id for o in list_offers_by_status(conn, "matched")] == [second]


def test_insert_cv_version_and_application(conn):
    offer_id = insert_offer(conn, make_offer())
    now = datetime.now(timezone.utc).isoformat()
    cv_id = insert_cv_version(
        conn,
        CvVersion(
            id=None,
            offer_id=offer_id,
            generated_at=now,
            file_path="generated_cvs/2026-08-15_acme_data-engineer_v1.pdf",
            bullet_ids_used=["example-1"],
            llm_model_used="claude-sonnet-5",
        ),
    )
    assert cv_id is not None

    app_id = insert_application(
        conn,
        Application(
            id=None,
            offer_id=offer_id,
            cv_version_id=cv_id,
            sent_at=now,
            method="native_auto",
            status="sent",
            error_message=None,
        ),
    )
    assert app_id is not None
