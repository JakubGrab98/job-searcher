from jobsearcher.db.models import Offer
from jobsearcher.filter.engine import MatchResult
from jobsearcher.notify.notification import build_match_notification


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
