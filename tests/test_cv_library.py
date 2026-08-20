import os

from jobsearcher.tailor.cv_library import get_bullet_by_id, get_role_by_id, load_cv_library

FIXTURE_PATH = os.path.join(os.path.dirname(__file__), "fixtures", "cv_library_sample.yaml")


def test_loads_candidate_and_summary():
    library = load_cv_library(FIXTURE_PATH)
    assert library["candidate"]["name"] == "Jane Example"
    assert library["summaries"]["general_data_engineer"]["text"].startswith("Example summary")


def test_every_bullet_gets_a_stable_id():
    library = load_cv_library(FIXTURE_PATH)
    bullets = library["experience"][0]["bullets"]
    assert bullets[0]["id"] != bullets[1]["id"]
    assert len(bullets[0]["id"]) == 12


def test_bullet_id_is_deterministic_across_loads():
    library1 = load_cv_library(FIXTURE_PATH)
    library2 = load_cv_library(FIXTURE_PATH)
    assert library1["experience"][0]["bullets"][0]["id"] == library2["experience"][0]["bullets"][0]["id"]


def test_get_bullet_by_id_finds_bullet():
    library = load_cv_library(FIXTURE_PATH)
    target_id = library["experience"][0]["bullets"][0]["id"]
    bullet = get_bullet_by_id(library, target_id)
    assert bullet is not None
    assert "ETL pipeline" in bullet["text"]


def test_get_bullet_by_id_returns_none_when_not_found():
    library = load_cv_library(FIXTURE_PATH)
    assert get_bullet_by_id(library, "nonexistent") is None


def test_roles_sharing_a_company_get_distinct_ids():
    # The fixture has two "Example Corp" roles (Data Engineer, Junior
    # Analyst) — company name alone can't disambiguate them.
    library = load_cv_library(FIXTURE_PATH)
    roles = library["experience"]
    assert roles[0]["company"] == roles[1]["company"] == "Example Corp"
    assert roles[0]["id"] != roles[1]["id"]


def test_get_role_by_id_finds_correct_role_despite_shared_company_name():
    library = load_cv_library(FIXTURE_PATH)
    target_id = library["experience"][1]["id"]
    role = get_role_by_id(library, target_id)
    assert role is not None
    assert role["role"] == "Junior Analyst"


def test_get_role_by_id_returns_none_when_not_found():
    library = load_cv_library(FIXTURE_PATH)
    assert get_role_by_id(library, "nonexistent") is None
