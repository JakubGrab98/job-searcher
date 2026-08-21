import os
import re
from importlib import resources

from jinja2 import Template

from jobsearcher.tailor.cv_library import get_bullet_by_id

# Skills without an explicit self-rating (e.g. "present but not a primary
# strength") still get a bar in the sidebar, just a modest one, for visual
# consistency with rated skills — no skill should render as unstyled plain
# text next to a column of bars.
DEFAULT_PROFICIENCY_WHEN_UNSPECIFIED = 40


def _build_keyword_pattern(skills_ctx: list[dict]) -> re.Pattern | None:
    """Builds a single regex that bolds sidebar skill names wherever they
    also appear in prose (summary/bullets) — mirrors the reference CV's
    style of bolding key technologies inline, not just listing them in a
    sidebar. Compound names ("Azure (Data Factory, Synapse)") are split into
    their individual parts so each is independently matchable, since prose
    text mentions "Data Factory" on its own, never the full compound string.
    """
    keywords = set()
    for skill in skills_ctx:
        for part in re.split(r"[/,()]", skill["name"]):
            part = part.strip()
            if len(part) > 1:
                keywords.add(part)
    if not keywords:
        return None

    # Longest-first: at a shared start position (e.g. "Azure" vs "Azure
    # SQL"), the regex engine tries alternatives in listed order, so this
    # ordering makes it prefer the longer/more specific match.
    sorted_keywords = sorted(keywords, key=len, reverse=True)
    escaped = [re.escape(kw) for kw in sorted_keywords]
    return re.compile(r"\b(" + "|".join(escaped) + r")\b", re.IGNORECASE)


def _bold_keywords(text: str, pattern: re.Pattern | None) -> str:
    if not pattern or not text:
        return text
    return pattern.sub(lambda m: f"<strong>{m.group(0)}</strong>", text)


def _resolve_context(library: dict, selection) -> dict:
    skills_by_name = {s["name"]: s for s in library.get("skills", [])}
    skills_ctx = []
    for name in selection.skill_names:
        skill = skills_by_name.get(name)
        if skill is None:
            continue
        proficiency = skill.get("proficiency") or DEFAULT_PROFICIENCY_WHEN_UNSPECIFIED
        skills_ctx.append({**skill, "proficiency": proficiency})

    keyword_pattern = _build_keyword_pattern(skills_ctx)

    summaries = library.get("summaries", {})
    summary_text = summaries[selection.summary_key]["text"].strip() if selection.summary_key in summaries else ""
    summary_text = _bold_keywords(summary_text, keyword_pattern)

    experience_ctx = []
    for exp in selection.experience:
        bullets_text = []
        for bullet_id in exp.bullet_ids:
            bullet = get_bullet_by_id(library, bullet_id)
            if bullet:
                bullets_text.append(_bold_keywords(bullet["text"], keyword_pattern))
        experience_ctx.append(
            {
                "company": exp.company,
                "team": exp.team,
                "role": exp.role,
                "dates": exp.dates,
                "bullets": bullets_text,
            }
        )

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
