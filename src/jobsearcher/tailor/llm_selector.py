import json
import re

from jobsearcher.tailor.cv_library import get_bullet_by_id
from jobsearcher.tailor.selection import CvSelection, SelectedExperience

# Cheapest current model capable of this structured selection/light-rephrase
# task — this isn't open-ended generation, it's picking from a fixed
# candidate set, well within a small model's ability.
DEFAULT_MODEL = "claude-haiku-4-5-20251001"

# Output is just a small JSON selection, not long-form content.
MAX_OUTPUT_TOKENS = 1024


def _serialize_candidate_profile(library: dict) -> str:
    summaries = {key: val["text"] for key, val in library.get("summaries", {}).items()}
    experience = [
        {
            "company": role["company"],
            "role": role["role"],
            "dates": role["dates"],
            "bullets": [{"id": b["id"], "text": b["text"]} for b in role.get("bullets", [])],
        }
        for role in library.get("experience", [])
    ]
    skills = [{"name": s["name"]} for s in library.get("skills", [])]

    return json.dumps({"summaries": summaries, "experience": experience, "skills": skills}, indent=2)


def build_selection_prompt(
    library: dict, offer_title: str, offer_description: str, offer_tech_stack: list[str]
) -> dict:
    """Builds the request payload for the bullet-selection call.

    The candidate's full profile is the SYSTEM block, marked with a 1-hour
    ephemeral cache — the pipeline runs on a schedule (~every 30 min), so
    a 1-hour TTL means this content stays cached across consecutive runs,
    not just within a single run's back-to-back offers. It deliberately
    contains no offer-specific text, so cache hits aren't broken by
    per-offer content changing on every call. Offer details go in the
    (uncached) user turn instead.
    """
    candidate_profile_text = (
        "You are helping tailor a CV. Below is the candidate's full truthful "
        "profile (summaries, experience bullets with ids, skills). You may ONLY "
        "select from these bullet ids — never invent new ones, never alter their "
        "meaning.\n\n" + _serialize_candidate_profile(library)
    )

    instructions = (
        f"Job offer:\nTitle: {offer_title}\n"
        f"Tech stack: {', '.join(offer_tech_stack)}\n"
        f"Description: {offer_description}\n\n"
        "Select the best-fitting summary key, up to 5 most relevant bullet ids per "
        "role (fewer for less relevant or older roles), and up to 8 relevant skill "
        "names. Respond with ONLY a JSON object of this exact shape, no other text:\n"
        '{"summary_key": "...", "experience": [{"company": "...", "bullet_ids": ["..."]}], '
        '"skill_names": ["..."]}'
    )

    return {
        "system": [
            {"type": "text", "text": candidate_profile_text, "cache_control": {"type": "ephemeral", "ttl": "1h"}}
        ],
        "messages": [{"role": "user", "content": instructions}],
    }


def parse_selection_response(response_text: str, library: dict) -> CvSelection:
    cleaned = response_text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```[a-zA-Z]*\n", "", cleaned)
        cleaned = re.sub(r"\n```$", "", cleaned)

    data = json.loads(cleaned)
    experience_by_company = {role["company"]: role for role in library.get("experience", [])}

    selected_experience = []
    for exp in data.get("experience", []):
        company = exp["company"]
        role_info = experience_by_company.get(company, {})
        # Guardrail: drop any bullet id that isn't a real id from the
        # library — rendering one would mean displaying text that doesn't
        # exist in the truthful source, exactly what this can't do.
        valid_ids = [bid for bid in exp.get("bullet_ids", []) if get_bullet_by_id(library, bid) is not None]
        selected_experience.append(
            SelectedExperience(
                company=company,
                team=role_info.get("team"),
                role=role_info.get("role", ""),
                dates=role_info.get("dates", ""),
                bullet_ids=valid_ids,
            )
        )

    return CvSelection(
        summary_key=data.get("summary_key"),
        experience=selected_experience,
        skill_names=data.get("skill_names", []),
    )


def select_bullets_for_offer(
    client,
    library: dict,
    offer_title: str,
    offer_description: str,
    offer_tech_stack: list[str],
    model: str = DEFAULT_MODEL,
) -> CvSelection:
    request = build_selection_prompt(library, offer_title, offer_description, offer_tech_stack)
    response = client.messages.create(
        model=model,
        max_tokens=MAX_OUTPUT_TOKENS,
        system=request["system"],
        messages=request["messages"],
    )
    return parse_selection_response(response.content[0].text, library)
