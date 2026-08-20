import os
import re
from datetime import datetime, timezone

from jobsearcher.db.models import CvVersion
from jobsearcher.db.repository import get_cv_version_by_offer, insert_cv_version
from jobsearcher.tailor.cv_render import render_cv_html, render_cv_pdf
from jobsearcher.tailor.drive_upload import upload_cv
from jobsearcher.tailor.llm_selector import DEFAULT_MODEL, select_bullets_for_offer


def _slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", (text or "").lower()).strip("-")


def tailor_cv_for_offer(
    anthropic_client,
    drive_service,
    library: dict,
    conn,
    offer,
    render_pdf_fn=render_cv_pdf,
    output_dir: str = "generated_cvs",
) -> CvVersion:
    """Full tailoring pipeline for one offer: LLM bullet selection -> HTML/PDF
    render -> Drive upload -> cv_versions row. Idempotent — an offer that
    already has a CV version is returned as-is without calling the LLM
    again, so a pipeline rerun never spends credits twice on the same offer.
    """
    existing = get_cv_version_by_offer(conn, offer.id)
    if existing is not None:
        return existing

    selection = select_bullets_for_offer(
        anthropic_client, library, offer.title, offer.description or "", offer.tech_stack
    )

    html = render_cv_html(library, selection)

    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    filename = f"{date_str}_{_slugify(offer.company)}_{_slugify(offer.title)}_v1.pdf"
    local_path = os.path.join(output_dir, filename)
    render_pdf_fn(html, local_path)

    drive_file_id, drive_web_view_link = upload_cv(drive_service, local_path, filename, offer.url)

    bullet_ids_used = [bullet_id for exp in selection.experience for bullet_id in exp.bullet_ids]

    insert_cv_version(
        conn,
        CvVersion(
            id=None,
            offer_id=offer.id,
            generated_at=datetime.now(timezone.utc).isoformat(),
            local_file_path=local_path,
            drive_file_id=drive_file_id,
            drive_web_view_link=drive_web_view_link,
            bullet_ids_used=bullet_ids_used,
            llm_model_used=DEFAULT_MODEL,
        ),
    )
    return get_cv_version_by_offer(conn, offer.id)
