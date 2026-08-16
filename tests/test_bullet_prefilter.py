from jobsearcher.tailor.bullet_prefilter import prefilter_library_for_offer


def make_role(bullets):
    return {"company": "Acme", "team": "Data", "role": "Data Engineer", "dates": "2023 - present", "bullets": bullets}


def test_ranks_bullets_by_tag_overlap_with_offer():
    library = {
        "experience": [
            make_role(
                [
                    {"text": "Built dashboards in Tableau.", "tags": ["tableau", "bi"]},
                    {"text": "Built ETL pipelines with Airflow and dbt.", "tags": ["etl", "airflow", "dbt"]},
                ]
            )
        ]
    }
    filtered = prefilter_library_for_offer(
        library, offer_title="Data Engineer", offer_description="We use Airflow and dbt heavily.",
        offer_tech_stack=["airflow", "dbt"], max_bullets_per_role=1,
    )
    bullets = filtered["experience"][0]["bullets"]
    assert len(bullets) == 1
    assert "Airflow" in bullets[0]["text"]


def test_keeps_only_higher_scoring_bullet_from_a_variant_pair():
    library = {
        "experience": [
            make_role(
                [
                    {"text": "Built ETL pipelines.", "tags": ["etl"]},
                    {"text": "Built ELT pipelines with dbt and CI/CD.", "tags": ["elt", "dbt", "ci_cd"], "variant_of": "etl_bullet"},
                ]
            )
        ]
    }
    filtered = prefilter_library_for_offer(
        library, offer_title="Data Engineer", offer_description="Looking for dbt and CI/CD experience.",
        offer_tech_stack=["dbt", "ci_cd"], max_bullets_per_role=5,
    )
    bullets = filtered["experience"][0]["bullets"]
    # Variant pair collapses to 1 bullet, not 2.
    assert len(bullets) == 1
    assert "ELT" in bullets[0]["text"]


def test_non_variant_bullets_are_not_deduped():
    library = {
        "experience": [
            make_role(
                [
                    {"text": "Built ETL pipelines.", "tags": ["etl"]},
                    {"text": "Managed Kubernetes clusters.", "tags": ["kubernetes"]},
                ]
            )
        ]
    }
    filtered = prefilter_library_for_offer(
        library, offer_title="Data Engineer", offer_description="ETL and Kubernetes.",
        offer_tech_stack=["etl", "kubernetes"], max_bullets_per_role=5,
    )
    assert len(filtered["experience"][0]["bullets"]) == 2


def test_preserves_all_roles_even_with_zero_matching_tags():
    library = {
        "experience": [
            make_role([{"text": "Unrelated bullet.", "tags": ["cobol"]}]),
        ]
    }
    filtered = prefilter_library_for_offer(
        library, offer_title="Data Engineer", offer_description="Python and dbt.",
        offer_tech_stack=["python", "dbt"], max_bullets_per_role=5,
    )
    assert len(filtered["experience"]) == 1
    assert len(filtered["experience"][0]["bullets"]) == 1


def test_does_not_mutate_the_original_library():
    library = {"experience": [make_role([{"text": "A bullet.", "tags": ["python"]}])]}
    original_bullet_count = len(library["experience"][0]["bullets"])

    prefilter_library_for_offer(
        library, offer_title="x", offer_description="y", offer_tech_stack=["python"], max_bullets_per_role=0,
    )

    assert len(library["experience"][0]["bullets"]) == original_bullet_count
