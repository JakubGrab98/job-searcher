import hashlib

import yaml


def _bullet_id(text: str) -> str:
    """Content-addressed id — the source YAML has no stable id field, so a
    short hash of the bullet text is used instead. Stable as long as the
    bullet's wording doesn't change; changes yield a new id, which is
    correct (it's a different bullet)."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]


def load_cv_library(path: str) -> dict:
    with open(path, encoding="utf-8") as f:
        library = yaml.safe_load(f)

    for role in library.get("experience", []):
        for bullet in role.get("bullets", []):
            bullet["id"] = _bullet_id(bullet["text"])

    return library


def get_bullet_by_id(library: dict, bullet_id: str) -> dict | None:
    for role in library.get("experience", []):
        for bullet in role.get("bullets", []):
            if bullet["id"] == bullet_id:
                return bullet
    return None
