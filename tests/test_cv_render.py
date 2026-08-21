import os

from jobsearcher.tailor.cv_library import load_cv_library
from jobsearcher.tailor.cv_render import render_cv_html
from jobsearcher.tailor.selection import CvSelection, SelectedExperience, default_selection

FIXTURE_PATH = os.path.join(os.path.dirname(__file__), "fixtures", "cv_library_sample.yaml")


def test_render_includes_candidate_name_and_headline():
    library = load_cv_library(FIXTURE_PATH)
    html = render_cv_html(library, default_selection(library))
    assert "Jane Example" in html
    assert "Data Engineer" in html


def test_render_includes_selected_summary_text():
    library = load_cv_library(FIXTURE_PATH)
    html = render_cv_html(library, default_selection(library))
    assert "Example summary text for a data engineer." in html


def test_render_includes_only_selected_bullets():
    library = load_cv_library(FIXTURE_PATH)
    first_bullet_id = library["experience"][0]["bullets"][0]["id"]

    selection = CvSelection(
        summary_key="general_data_engineer",
        experience=[
            SelectedExperience(
                company="Example Corp", team="Data Team", role="Data Engineer",
                dates="2023 - present", bullet_ids=[first_bullet_id],
            )
        ],
        skill_names=["Python"],
    )
    html = render_cv_html(library, selection)

    assert "Built an ETL pipeline moving data from Postgres to Snowflake." in html
    assert "Delivered ELT pipelines with dbt" not in html


def test_render_includes_only_selected_skills():
    library = load_cv_library(FIXTURE_PATH)
    selection = default_selection(library)
    selection.skill_names = ["Python"]

    html = render_cv_html(library, selection)
    assert "Python" in html
    assert ">SQL<" not in html


def test_render_omits_education_when_excluded():
    library = load_cv_library(FIXTURE_PATH)
    selection = default_selection(library)
    selection.include_education = False

    html = render_cv_html(library, selection)
    assert "Example University" not in html


def test_render_produces_valid_html_document():
    library = load_cv_library(FIXTURE_PATH)
    html = render_cv_html(library, default_selection(library))
    assert html.strip().startswith("<!DOCTYPE html>")
    assert "</html>" in html


def test_render_gives_every_selected_skill_a_proficiency_bar():
    # "Tableau" has no explicit proficiency in the fixture (mirrors real
    # cv_library.yaml entries like "PySpark / Delta Lake" that are marked
    # present-but-not-primary with no numeric self-rating). Every skill in
    # the sidebar should still render with a bar for visual consistency,
    # not fall back to plain text.
    library = load_cv_library(FIXTURE_PATH)
    selection = default_selection(library)
    selection.skill_names = ["Tableau"]

    html = render_cv_html(library, selection)
    assert "plain-skill" not in html
    assert "skill-bar-fill" in html


def test_render_bolds_skill_keywords_within_summary_text():
    library = load_cv_library(FIXTURE_PATH)
    selection = default_selection(library)
    selection.skill_names = ["Python", "SQL"]

    html = render_cv_html(library, selection)
    assert "<strong>Python</strong>" in html
    assert "<strong>SQL</strong>" in html


def test_render_bolds_skill_keywords_within_experience_bullets():
    library = load_cv_library(FIXTURE_PATH)
    first_bullet_id = library["experience"][0]["bullets"][0]["id"]
    selection = CvSelection(
        summary_key=None,
        experience=[
            SelectedExperience(
                company="Example Corp", team="Data Team", role="Data Engineer",
                dates="2023 - present", bullet_ids=[first_bullet_id],
            )
        ],
        skill_names=["Snowflake"],
    )

    html = render_cv_html(library, selection)
    assert "<strong>Snowflake</strong>" in html


def test_render_bolds_each_part_of_a_compound_skill_name():
    # "ETL / ELT" in the fixture must split into independently-matchable
    # keywords, since prose text says "ELT pipelines", never the full
    # compound "ETL / ELT" string.
    library = load_cv_library(FIXTURE_PATH)
    second_bullet_id = library["experience"][0]["bullets"][1]["id"]
    selection = CvSelection(
        summary_key=None,
        experience=[
            SelectedExperience(
                company="Example Corp", team="Data Team", role="Data Engineer",
                dates="2023 - present", bullet_ids=[second_bullet_id],
            )
        ],
        skill_names=["ETL / ELT"],
    )

    html = render_cv_html(library, selection)
    assert "<strong>ELT</strong>" in html


def test_render_does_not_bold_keywords_outside_summary_and_bullets():
    library = load_cv_library(FIXTURE_PATH)
    selection = default_selection(library)
    selection.skill_names = ["Python", "SQL"]

    html = render_cv_html(library, selection)
    assert "<strong>Data</strong>" not in html
