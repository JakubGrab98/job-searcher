from dataclasses import dataclass, field

import yaml


@dataclass
class FilterConfig:
    role_keywords: list[str] = field(default_factory=list)
    contract_types: list[str] = field(default_factory=list)
    seniority: list[str] = field(default_factory=list)
    salary_floor: int | None = None
    salary_period: str = "hour"
    currency: str = "PLN"
    locations: list[str] = field(default_factory=list)
    remote_ok: bool = True
    tech_must_have: list[str] = field(default_factory=list)
    tech_nice_to_have: list[str] = field(default_factory=list)
    excluded_companies: list[str] = field(default_factory=list)
    excluded_industries: list[str] = field(default_factory=list)


def load_filter_config(path: str) -> FilterConfig:
    with open(path, encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}
    return FilterConfig(**raw)
