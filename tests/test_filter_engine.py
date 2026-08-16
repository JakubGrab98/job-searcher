from jobsearcher.db.models import Offer
from jobsearcher.filter.config import FilterConfig
from jobsearcher.filter.engine import evaluate


def make_offer(**overrides) -> Offer:
    base = dict(
        id=1,
        gmail_message_id=None,
        url="https://justjoin.it/job-offer/x",
        title="Senior Data Engineer",
        company="Acme",
        category="data",
        seniority="senior",
        employment_type="b2b",
        salary_min=180,
        salary_max=220,
        currency="PLN",
        location="Warszawa",
        remote_type="hybrid",
        tech_stack=["python", "airflow", "dbt", "snowflake"],
        apply_type="native",
        status="enriched",
        filter_reasons=[],
        first_seen_at="2026-08-15T00:00:00+00:00",
        updated_at="2026-08-15T00:00:00+00:00",
    )
    base.update(overrides)
    return Offer(**base)


def base_config(**overrides) -> FilterConfig:
    base = dict(
        role_keywords=["data engineer"],
        contract_types=["b2b"],
        seniority=["mid", "senior"],
        salary_floor=150,
        salary_period="hour",
        currency="PLN",
        locations=["Warszawa"],
        remote_ok=True,
        tech_must_have=["python"],
        tech_nice_to_have=["dbt"],
        excluded_companies=[],
        excluded_industries=[],
    )
    base.update(overrides)
    return FilterConfig(**base)


def test_offer_matching_all_criteria_passes():
    result = evaluate(make_offer(), base_config())
    assert result.matched is True
    assert result.reasons == []
    assert "dbt" in result.matched_criteria


def test_offer_below_salary_floor_is_filtered():
    result = evaluate(make_offer(salary_max=120), base_config(salary_floor=150))
    assert result.matched is False
    assert any("salary" in r for r in result.reasons)


def test_offer_missing_role_keyword_is_filtered():
    result = evaluate(make_offer(title="Backend Java Developer", tech_stack=["java"]), base_config())
    assert result.matched is False
    assert any("role keyword" in r for r in result.reasons)


def test_offer_missing_must_have_tech_is_filtered():
    result = evaluate(make_offer(tech_stack=["java"]), base_config(tech_must_have=["python", "airflow"]))
    assert result.matched is False
    assert any("must-have tech" in r for r in result.reasons)


def test_offer_from_excluded_company_is_filtered():
    result = evaluate(make_offer(company="BadCo"), base_config(excluded_companies=["BadCo"]))
    assert result.matched is False
    assert any("excluded company" in r for r in result.reasons)


def test_remote_offer_bypasses_location_restriction():
    result = evaluate(
        make_offer(location="Krakow", remote_type="remote"),
        base_config(locations=["Warszawa"], remote_ok=True),
    )
    assert result.matched is True


def test_offer_wrong_contract_type_is_filtered():
    result = evaluate(make_offer(employment_type="uop"), base_config(contract_types=["b2b"]))
    assert result.matched is False
    assert any("contract type" in r for r in result.reasons)


def test_real_world_contract_type_text_matches_via_substring():
    # Real enrichment extracts free text like "B2B, Permanent", not a clean
    # "b2b" token — must match via substring, not exact equality.
    result = evaluate(make_offer(employment_type="B2B, Permanent"), base_config(contract_types=["b2b"]))
    assert result.matched is True


def test_capitalized_seniority_matches_case_insensitively():
    # Real enrichment extracts capitalized values like "Senior".
    result = evaluate(make_offer(seniority="Senior"), base_config(seniority=["mid", "senior"]))
    assert result.matched is True


def test_empty_config_lists_mean_no_restriction():
    result = evaluate(
        make_offer(employment_type="uop", seniority="junior", location="Gdansk", remote_type="onsite"),
        base_config(contract_types=[], seniority=[], locations=[], remote_ok=False, tech_must_have=[]),
    )
    assert result.matched is True
