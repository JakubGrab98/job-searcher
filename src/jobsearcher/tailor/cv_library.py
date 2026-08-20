import hashlib

import yaml


def _content_id(text: str) -> str:
    """Content-addressed id — the source YAML has no stable id field, so a
    short hash of identifying text is used instead. Stable as long as the
    wording doesn't change; changes yield a new id, which is correct (it's
    different content)."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]


def load_cv_library(path: str) -> dict:
    with open(path, encoding="utf-8") as f:
        library = yaml.safe_load(f)

    for role in library.get("experience", []):
        # Two roles can share a company name (e.g. a promotion, or a
        # company with multiple stints) — company name alone isn't a
        # reliable lookup key, so each role gets its own id too.
        role["id"] = _content_id(f"{role['company']}|{role['role']}|{role['dates']}")
        for bullet in role.get("bullets", []):
            bullet["id"] = _content_id(bullet["text"])

    return library


def get_bullet_by_id(library: dict, bullet_id: str) -> dict | None:
    for role in library.get("experience", []):
        for bullet in role.get("bullets", []):
            if bullet["id"] == bullet_id:
                return bullet
    return None


def get_role_by_id(library: dict, role_id: str) -> dict | None:
    for role in library.get("experience", []):
        if role["id"] == role_id:
            return role
    return None
