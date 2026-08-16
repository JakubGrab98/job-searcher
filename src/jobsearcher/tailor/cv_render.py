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


def render_cv_pdf(html: str, output_path: str) -> None:
    from playwright.sync_api import sync_playwright

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.set_content(html, wait_until="load")
        page.pdf(
            path=output_path,
            format="A4",
            print_background=True,
            margin={"top": "0", "bottom": "0", "left": "0", "right": "0"},
        )
        browser.close()
