import json
import os

from jobsearcher.tailor.cv_library import load_cv_library
from jobsearcher.tailor.llm_selector import build_selection_prompt, parse_selection_response, select_bullets_for_offer

FIXTURE_PATH = os.path.join(os.path.dirname(__file__), "fixtures", "cv_library_sample.yaml")


def test_build_selection_prompt_caches_the_full_library_block():
    library = load_cv_library(FIXTURE_PATH)
    request = build_selection_prompt(library, "Data Engineer", "Looking for dbt experience.", ["dbt"])

    system_blocks = request["system"]
    assert len(system_blocks) >= 1
    cached_block = system_blocks[0]
    assert cached_block["cache_control"] == {"type": "ephemeral", "ttl": "1h"}
    # The cached block carries the reusable candidate profile (experience/
    # skills/summaries — no name/contact needed for selection) — not the
    # offer-specific text, which must stay in the uncached user turn so
    # cache hits aren't broken by per-offer content changing every call.
    assert "Example Corp" in cached_block["text"]
    assert "Looking for dbt experience" not in cached_block["text"]


def test_build_selection_prompt_puts_offer_details_in_user_message():
    library = load_cv_library(FIXTURE_PATH)
    request = build_selection_prompt(library, "Data Engineer", "Looking for dbt experience.", ["dbt"])

    user_message = request["messages"][0]["content"]
    assert "Data Engineer" in user_message
    assert "Looking for dbt experience." in user_message


def test_build_selection_prompt_includes_real_bullet_ids_for_selection():
    library = load_cv_library(FIXTURE_PATH)
    request = build_selection_prompt(library, "Data Engineer", "x", [])

    bullet_id = library["experience"][0]["bullets"][0]["id"]
    assert bullet_id in request["system"][0]["text"]


def test_parse_selection_response_resolves_bullet_ids_to_selection():
    library = load_cv_library(FIXTURE_PATH)
    role_id = library["experience"][0]["id"]
    bullet_id = library["experience"][0]["bullets"][0]["id"]

    response_json = json.dumps(
        {
            "summary_key": "general_data_engineer",
            "experience": [{"role_id": role_id, "bullet_ids": [bullet_id]}],
            "skill_names": ["Python"],
        }
    )
    selection = parse_selection_response(response_json, library)

    assert selection.summary_key == "general_data_engineer"
    assert selection.experience[0].company == "Example Corp"
    assert selection.experience[0].bullet_ids == [bullet_id]
    assert selection.skill_names == ["Python"]


def test_parse_selection_response_disambiguates_roles_sharing_a_company():
    # Regression: two roles at "Example Corp" — a company-name lookup
    # would collapse both onto the same (wrong) role.
    library = load_cv_library(FIXTURE_PATH)
    first_role_id = library["experience"][0]["id"]
    second_role_id = library["experience"][1]["id"]
    first_bullet_id = library["experience"][0]["bullets"][0]["id"]
    second_bullet_id = library["experience"][1]["bullets"][0]["id"]

    response_json = json.dumps(
        {
            "summary_key": "general_data_engineer",
            "experience": [
                {"role_id": first_role_id, "bullet_ids": [first_bullet_id]},
                {"role_id": second_role_id, "bullet_ids": [second_bullet_id]},
            ],
            "skill_names": [],
        }
    )
    selection = parse_selection_response(response_json, library)

    assert len(selection.experience) == 2
    assert selection.experience[0].role == "Data Engineer"
    assert selection.experience[0].bullet_ids == [first_bullet_id]
    assert selection.experience[1].role == "Junior Analyst"
    assert selection.experience[1].bullet_ids == [second_bullet_id]


def test_parse_selection_response_handles_markdown_code_fence():
    library = load_cv_library(FIXTURE_PATH)
    role_id = library["experience"][0]["id"]
    bullet_id = library["experience"][0]["bullets"][0]["id"]
    wrapped = "```json\n" + json.dumps(
        {"summary_key": "general_data_engineer", "experience": [{"role_id": role_id, "bullet_ids": [bullet_id]}], "skill_names": []}
    ) + "\n```"

    selection = parse_selection_response(wrapped, library)
    assert selection.experience[0].bullet_ids == [bullet_id]


def test_parse_selection_response_drops_invented_bullet_ids():
    library = load_cv_library(FIXTURE_PATH)
    role_id = library["experience"][0]["id"]
    real_id = library["experience"][0]["bullets"][0]["id"]

    response_json = json.dumps(
        {
            "summary_key": "general_data_engineer",
            "experience": [{"role_id": role_id, "bullet_ids": [real_id, "made-up-id-999"]}],
            "skill_names": [],
        }
    )
    selection = parse_selection_response(response_json, library)

    # Guardrail: never trust a bullet id that isn't a real id from the
    # library — that would mean rendering text that doesn't exist in it.
    assert selection.experience[0].bullet_ids == [real_id]


def test_parse_selection_response_skips_unrecognized_role_id():
    library = load_cv_library(FIXTURE_PATH)
    response_json = json.dumps(
        {"summary_key": "general_data_engineer", "experience": [{"role_id": "made-up-role", "bullet_ids": []}], "skill_names": []}
    )
    selection = parse_selection_response(response_json, library)
    assert selection.experience == []


class _FakeContentBlock:
    def __init__(self, text):
        self.text = text


class _FakeResponse:
    def __init__(self, text):
        self.content = [_FakeContentBlock(text)]


class _FakeMessages:
    def __init__(self, response_text):
        self._response_text = response_text
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return _FakeResponse(self._response_text)


class _FakeAnthropicClient:
    def __init__(self, response_text):
        self.messages = _FakeMessages(response_text)


def test_select_bullets_for_offer_uses_cheap_model_and_capped_tokens():
    library = load_cv_library(FIXTURE_PATH)
    role_id = library["experience"][0]["id"]
    bullet_id = library["experience"][0]["bullets"][0]["id"]
    response_text = json.dumps(
        {"summary_key": "general_data_engineer", "experience": [{"role_id": role_id, "bullet_ids": [bullet_id]}], "skill_names": ["Python"]}
    )
    client = _FakeAnthropicClient(response_text)

    selection = select_bullets_for_offer(client, library, "Data Engineer", "Looking for dbt.", ["dbt"])

    assert selection.experience[0].bullet_ids == [bullet_id]
    call = client.messages.calls[0]
    assert call["model"] == "claude-haiku-4-5-20251001"
    assert call["max_tokens"] == 1024
    assert call["system"][0]["cache_control"] == {"type": "ephemeral", "ttl": "1h"}
