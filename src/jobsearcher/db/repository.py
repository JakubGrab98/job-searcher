import json
import sqlite3
from datetime import datetime, timezone

from jobsearcher.db.models import Offer, CvVersion, Application


def _row_to_offer(row: sqlite3.Row) -> Offer:
    return Offer(
        id=row["id"],
        gmail_message_id=row["gmail_message_id"],
        url=row["url"],
        title=row["title"],
        company=row["company"],
        category=row["category"],
        seniority=row["seniority"],
        employment_type=row["employment_type"],
        salary_min=row["salary_min"],
        salary_max=row["salary_max"],
        currency=row["currency"],
        location=row["location"],
        remote_type=row["remote_type"],
        tech_stack=json.loads(row["tech_stack"]),
        apply_type=row["apply_type"],
        status=row["status"],
        filter_reasons=json.loads(row["filter_reasons"]),
        first_seen_at=row["first_seen_at"],
        updated_at=row["updated_at"],
    )


def insert_offer(conn: sqlite3.Connection, offer: Offer) -> int:
    existing = get_offer_by_url(conn, offer.url)
    if existing is not None:
        return existing.id

    cursor = conn.execute(
        """
        INSERT INTO offers (
            gmail_message_id, url, title, company, category, seniority,
            employment_type, salary_min, salary_max, currency, location,
            remote_type, tech_stack, apply_type, status, filter_reasons,
            first_seen_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            offer.gmail_message_id, offer.url, offer.title, offer.company,
            offer.category, offer.seniority, offer.employment_type,
            offer.salary_min, offer.salary_max, offer.currency, offer.location,
            offer.remote_type, json.dumps(offer.tech_stack), offer.apply_type,
            offer.status, json.dumps(offer.filter_reasons),
            offer.first_seen_at, offer.updated_at,
        ),
    )
    conn.commit()
    return cursor.lastrowid


def get_offer_by_url(conn: sqlite3.Connection, url: str) -> Offer | None:
    row = conn.execute("SELECT * FROM offers WHERE url = ?", (url,)).fetchone()
    return _row_to_offer(row) if row else None


def get_offer(conn: sqlite3.Connection, offer_id: int) -> Offer | None:
    row = conn.execute("SELECT * FROM offers WHERE id = ?", (offer_id,)).fetchone()
    return _row_to_offer(row) if row else None


def update_offer_enrichment(conn: sqlite3.Connection, offer_id: int, **fields) -> None:
    allowed = {
        "seniority", "employment_type", "salary_min", "salary_max", "currency",
        "location", "remote_type", "tech_stack", "apply_type",
    }
    unknown = set(fields) - allowed
    if unknown:
        raise ValueError(f"Unknown enrichment fields: {unknown}")

    columns = []
    values = []
    for key, value in fields.items():
        columns.append(f"{key} = ?")
        values.append(json.dumps(value) if key == "tech_stack" else value)

    columns.append("status = ?")
    values.append("enriched")
    columns.append("updated_at = ?")
    values.append(datetime.now(timezone.utc).isoformat())
    values.append(offer_id)

    conn.execute(f"UPDATE offers SET {', '.join(columns)} WHERE id = ?", values)
    conn.commit()


def update_offer_status(
    conn: sqlite3.Connection,
    offer_id: int,
    status: str,
    filter_reasons: list[str] | None = None,
) -> None:
    if filter_reasons is not None:
        conn.execute(
            "UPDATE offers SET status = ?, filter_reasons = ?, updated_at = ? WHERE id = ?",
            (status, json.dumps(filter_reasons), datetime.now(timezone.utc).isoformat(), offer_id),
        )
    else:
        conn.execute(
            "UPDATE offers SET status = ?, updated_at = ? WHERE id = ?",
            (status, datetime.now(timezone.utc).isoformat(), offer_id),
        )
    conn.commit()


def list_offers_by_status(conn: sqlite3.Connection, status: str) -> list[Offer]:
    rows = conn.execute("SELECT * FROM offers WHERE status = ? ORDER BY id", (status,)).fetchall()
    return [_row_to_offer(row) for row in rows]


def _row_to_cv_version(row: sqlite3.Row) -> CvVersion:
    return CvVersion(
        id=row["id"],
        offer_id=row["offer_id"],
        generated_at=row["generated_at"],
        local_file_path=row["local_file_path"],
        drive_file_id=row["drive_file_id"],
        drive_web_view_link=row["drive_web_view_link"],
        bullet_ids_used=json.loads(row["bullet_ids_used"]),
        llm_model_used=row["llm_model_used"],
    )


def insert_cv_version(conn: sqlite3.Connection, cv: CvVersion) -> int:
    cursor = conn.execute(
        """
        INSERT INTO cv_versions (
            offer_id, generated_at, local_file_path, drive_file_id,
            drive_web_view_link, bullet_ids_used, llm_model_used
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            cv.offer_id, cv.generated_at, cv.local_file_path, cv.drive_file_id,
            cv.drive_web_view_link, json.dumps(cv.bullet_ids_used), cv.llm_model_used,
        ),
    )
    conn.commit()
    return cursor.lastrowid


def get_cv_version_by_offer(conn: sqlite3.Connection, offer_id: int) -> CvVersion | None:
    """Used to skip re-tailoring an offer that already has a CV version —
    the whole point being to never spend LLM credits twice on the same offer."""
    row = conn.execute(
        "SELECT * FROM cv_versions WHERE offer_id = ? ORDER BY id DESC LIMIT 1", (offer_id,)
    ).fetchone()
    return _row_to_cv_version(row) if row else None


def insert_application(conn: sqlite3.Connection, app: Application) -> int:
    cursor = conn.execute(
        """
        INSERT INTO applications (offer_id, cv_version_id, sent_at, method, status, error_message)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (app.offer_id, app.cv_version_id, app.sent_at, app.method, app.status, app.error_message),
    )
    conn.commit()
    return cursor.lastrowid
