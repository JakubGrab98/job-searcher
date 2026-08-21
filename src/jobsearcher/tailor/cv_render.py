import os
from importlib import resources

from jinja2 import Template

from jobsearcher.tailor.cv_library import get_bullet_by_id


def _resolve_context(library: dict, selection) -> dict:
    summaries = library.get("summaries", {})
    summary_text = summaries[selection.summary_key]["text"].strip() if selection.summary_key in summaries else ""

    experience_ctx = []
    for exp in selection.experience:
        bullets_text = []
        for bullet_id in exp.bullet_ids:
            bullet = get_bullet_by_id(library, bullet_id)
            if bullet:
                bullets_text.append(bullet["text"])
        experience_ctx.append(
            {
                "company": exp.company,
                "team": exp.team,
                "role": exp.role,
                "dates": exp.dates,
                "bullets": bullets_text,
            }
        )

    skills_by_name = {s["name"]: s for s in library.get("skills", [])}
    skills_ctx = [skills_by_name[name] for name in selection.skill_names if name in skills_by_name]

    return {
        "candidate": library["candidate"],
        "summary": summary_text,
        "experience": experience_ctx,
        "education": library.get("education", []) if selection.include_education else [],
        "certifications": library.get("certifications", []) if selection.include_certifications else [],
        "skills": skills_ctx,
    }


def render_cv_html(library: dict, selection) -> str:
    template_str = resources.files("jobsearcher.tailor").joinpath("templates/cv_template.html").read_text(
        encoding="utf-8"
    )
    template = Template(template_str)
    return template.render(**_resolve_context(library, selection))


def _render_pdf_with_browser(browser, html: str, output_path: str) -> None:
    page = browser.new_page()
    try:
        page.set_content(html, wait_until="load")
        page.pdf(
            path=output_path,
            format="A4",
            print_background=True,
            margin={"top": "0", "bottom": "0", "left": "0", "right": "0"},
        )
    finally:
        page.close()


def render_cv_pdf(html: str, output_path: str, browser=None) -> None:
    """Renders html to a PDF at output_path.

    If `browser` is provided, reuses it (just opens/closes a page) instead
    of starting a new Playwright context — required when a caller (e.g.
    run.py, which keeps a browser open across a whole run for enrichment)
    already has one open. Playwright's sync API does not support nested
    sync_playwright() contexts in the same process; calling this without
    `browser` while another sync_playwright() context is already open in
    the same thread raises "you are using Playwright Sync API inside the
    asyncio loop" — confirmed live in production (run.py keeps the
    enrichment browser open while tailoring runs inside the same pass).

    Without `browser`, manages its own standalone Playwright context —
    fine for one-off/standalone use (e.g. validate_cv_render.py) where
    nothing else has Playwright open.
    """
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

    if browser is not None:
        _render_pdf_with_browser(browser, html, output_path)
        return

    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        standalone_browser = p.chromium.launch()
        try:
            _render_pdf_with_browser(standalone_browser, html, output_path)
        finally:
            standalone_browser.close()
