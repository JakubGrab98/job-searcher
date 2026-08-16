import copy


def _tag_overlap_score(tags: list[str], searchable_text: str) -> int:
    return sum(1 for tag in tags if tag.lower().replace("_", " ") in searchable_text)


def _dedupe_variants(bullets: list[dict], searchable_text: str) -> list[dict]:
    """Adjacent bullets where the second has `variant_of` are alternate
    phrasings of the same underlying fact — the source YAML has no real
    linkable ids (variant_of values are descriptive labels, not ids), so
    adjacency is the actual pairing signal in how the file is authored.
    Keeps whichever phrasing scores higher against the offer, since sending
    both to the LLM wastes tokens on redundant content."""
    result = []
    i = 0
    while i < len(bullets):
        current = bullets[i]
        if i + 1 < len(bullets) and bullets[i + 1].get("variant_of"):
            variant = bullets[i + 1]
            current_score = _tag_overlap_score(current.get("tags", []), searchable_text)
            variant_score = _tag_overlap_score(variant.get("tags", []), searchable_text)
            result.append(variant if variant_score > current_score else current)
            i += 2
        else:
            result.append(current)
            i += 1
    return result


def prefilter_library_for_offer(
    library: dict,
    offer_title: str,
    offer_description: str,
    offer_tech_stack: list[str],
    max_bullets_per_role: int = 5,
) -> dict:
    """Trims the bullet library down to the most relevant candidates for a
    given offer before it ever reaches the LLM — smaller prompt, lower
    cost, and a cleaner candidate set for the model to choose from. Pure
    deterministic logic, no API calls. Does not mutate the input library."""
    searchable_text = " ".join(
        [offer_title or "", offer_description or "", " ".join(offer_tech_stack or [])]
    ).lower()

    filtered = copy.deepcopy(library)
    for role in filtered.get("experience", []):
        deduped = _dedupe_variants(role.get("bullets", []), searchable_text)
        ranked = sorted(
            deduped, key=lambda b: _tag_overlap_score(b.get("tags", []), searchable_text), reverse=True
        )
        role["bullets"] = ranked[:max_bullets_per_role]

    return filtered
