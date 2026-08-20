from jobsearcher.db.models import CvVersion, Offer
from jobsearcher.filter.engine import MatchResult
from jobsearcher.notify.notification import build_failure_alert, build_match_notification


def make_offer(**overrides) -> Offer:
    base = dict(
        id=1,
        gmail_message_id=None,
        url="https://justjoin.it/job-offer/acme-data-engineer",
        title="Senior Data Engineer",
        company="Acme",
        category="data",
        description=None,
        seniority="Senior",
        employment_type="B2B",
        salary_min=180,
        salary_max=220,
        currency="PLN",
        location="Warszawa",
        remote_type="Hybrid",
        tech_stack=["python", "airflow"],
        apply_type="native",
        status="matched",
        filter_reasons=[],
        first_seen_at="2026-08-15T00:00:00+00:00",
        updated_at="2026-08-15T00:00:00+00:00",
    )
    base.update(overrides)
    return Offer(**base)


def test_subject_includes_title_and_company():
    subject, _ = build_match_notification(make_offer(), MatchResult(matched=True, matched_criteria=["python"]))
    assert "Senior Data Engineer" in subject
    assert "Acme" in subject


def test_body_includes_offer_link():
    _, body = build_match_notification(make_offer(), MatchResult(matched=True, matched_criteria=["python"]))
    assert "https://justjoin.it/job-offer/acme-data-engineer" in body


def test_body_includes_matched_criteria():
    _, body = build_match_notification(
        make_offer(), MatchResult(matched=True, matched_criteria=["python", "airflow", "location"])
    )
    assert "python" in body
    assert "airflow" in body
    assert "location" in body


def test_body_includes_salary_when_known():
    _, body = build_match_notification(make_offer(), MatchResult(matched=True, matched_criteria=[]))
    assert "180" in body
    assert "220" in body
    assert "PLN" in body


def test_body_handles_unknown_salary_gracefully():
    offer = make_offer(salary_min=None, salary_max=None, currency=None)
    _, body = build_match_notification(offer, MatchResult(matched=True, matched_criteria=[]))
    assert "Undisclosed" in body or "unknown" in body.lower()


def test_body_includes_cv_link_when_tailored():
    cv = CvVersion(
        id=1, offer_id=1, generated_at="2026-08-20T00:00:00+00:00",
        local_file_path="generated_cvs/x.pdf",
        drive_web_view_link="https://drive.google.com/file/d/abc123/view",
    )
    _, body = build_match_notification(make_offer(), MatchResult(matched=True, matched_criteria=[]), cv_version=cv)
    assert "https://drive.google.com/file/d/abc123/view" in body


def test_body_notes_when_cv_not_yet_available():
    _, body = build_match_notification(make_offer(), MatchResult(matched=True, matched_criteria=[]), cv_version=None)
    assert "not" in body.lower() or "pending" in body.lower()


def test_failure_alert_includes_run_id_and_error():
    subject, body = build_failure_alert("Playwright crashed: timeout", run_id=42)
    assert "failed" in subject.lower()
    assert "42" in body
    assert "Playwright crashed: timeout" in body


def test_failure_alert_handles_missing_run_id():
    subject, body = build_failure_alert("Gmail auth expired")
    assert "Gmail auth expired" in body
