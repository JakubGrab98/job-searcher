import os

import pytest

from jobsearcher.enrich.offer_details import parse_offer_details

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures")


def _load(name):
    with open(os.path.join(FIXTURES_DIR, name), encoding="utf-8") as f:
        return f.read()


@pytest.fixture
def external_offer_text():
    return _load("offer_page_external.txt")


@pytest.fixture
def native_offer_text():
    return _load("offer_page_native.txt")


def test_parses_disclosed_salary_range(external_offer_text):
    details = parse_offer_details(external_offer_text)
    assert details.salary_min == 14000
    assert details.salary_max == 20000
    assert details.currency == "PLN"
    assert details.salary_period == "month"


def test_parses_none_when_salary_undisclosed(native_offer_text):
    details = parse_offer_details(native_offer_text)
    assert details.salary_min is None
    assert details.salary_max is None
    assert details.currency is None


def test_parses_employment_chips(external_offer_text):
    details = parse_offer_details(external_offer_text)
    assert details.employment_time == "Full-time"
    assert details.contract_type == "Permanent"
    assert details.seniority == "Senior"
    assert details.work_mode == "Hybrid"


def test_parses_employment_chips_with_extra_schedule_line(native_offer_text):
    # This offer has an extra "3 onsite / 2 remote" line that isn't any of
    # the known chip categories — must be ignored, not misclassified.
    details = parse_offer_details(native_offer_text)
    assert details.employment_time == "Full-time"
    assert details.contract_type == "Permanent"
    assert details.seniority == "Junior"
    assert details.work_mode == "Hybrid"


def test_parses_tech_stack_as_flat_name_list(external_offer_text):
    details = parse_offer_details(external_offer_text)
    assert details.tech_stack == ["Business Analysis", "Agile", "UX"]


def test_parses_tech_stack_ignoring_nice_to_have_levels(native_offer_text):
    details = parse_offer_details(native_offer_text)
    assert details.tech_stack == [
        "English",
        "Bulgarian",
        "Helpdesk",
        "Customer Support",
        "IT Support",
    ]


def test_parses_description_between_headings(external_offer_text):
    details = parse_offer_details(external_offer_text)
    assert "Elicit, analyze, and document business requirements" in details.description
    assert "TECH STACK" not in details.description
