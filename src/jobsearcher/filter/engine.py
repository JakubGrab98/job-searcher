from dataclasses import dataclass, field

from jobsearcher.db.models import Offer
from jobsearcher.filter.config import FilterConfig


@dataclass
class MatchResult:
    matched: bool
    reasons: list[str] = field(default_factory=list)
    matched_criteria: list[str] = field(default_factory=list)


def _is_remote(offer: Offer) -> bool:
    return (offer.remote_type or "").lower() == "remote"


def evaluate(offer: Offer, config: FilterConfig) -> MatchResult:
    reasons: list[str] = []
    matched_criteria: list[str] = []

    if config.excluded_companies and offer.company in config.excluded_companies:
        reasons.append(f"excluded company: {offer.company}")

    if config.contract_types:
        # Real extracted values are free text like "B2B, Permanent" or
        # "B2B Contract", not a clean "b2b" token — substring match, not
        # equality, or a filters.yaml entry of "b2b" would never match.
        offer_contract_lower = (offer.employment_type or "").lower()
        contract_matches = any(ct.lower() in offer_contract_lower for ct in config.contract_types)
        if not contract_matches:
            reasons.append(f"contract type '{offer.employment_type}' doesn't match any of {config.contract_types}")

    if config.seniority:
        # Extracted values are capitalized ("Senior") — compare case-insensitively.
        seniority_lower = (offer.seniority or "").lower()
        if seniority_lower not in [s.lower() for s in config.seniority]:
            reasons.append(f"seniority '{offer.seniority}' not in {config.seniority}")

    if config.salary_floor is not None:
        best_salary = offer.salary_max if offer.salary_max is not None else offer.salary_min
        currency_matches = (offer.currency or "").upper() == config.currency.upper()
        if best_salary is None:
            reasons.append("salary unknown, cannot verify floor")
        elif currency_matches and best_salary < config.salary_floor:
            reasons.append(f"salary {best_salary} {offer.currency} below floor {config.salary_floor}")
        elif currency_matches:
            matched_criteria.append("salary floor")

    if config.locations:
        location_matches = any(
            loc.lower() in (offer.location or "").lower() for loc in config.locations
        )
        if not location_matches and not (config.remote_ok and _is_remote(offer)):
            reasons.append(f"location '{offer.location}' not in {config.locations} and not remote")
        elif location_matches:
            matched_criteria.append("location")
        elif config.remote_ok and _is_remote(offer):
            matched_criteria.append("remote")

    if config.tech_must_have:
        offer_tech_lower = {t.lower() for t in offer.tech_stack}
        missing = [t for t in config.tech_must_have if t.lower() not in offer_tech_lower]
        if missing:
            reasons.append(f"missing must-have tech: {missing}")
        else:
            matched_criteria.append("must-have tech")

    if config.role_keywords:
        haystack = (offer.title + " " + " ".join(offer.tech_stack)).lower()
        hit_keywords = [kw for kw in config.role_keywords if kw.lower() in haystack]
        if not hit_keywords:
            reasons.append(f"no role keyword matched from {config.role_keywords}")
        else:
            matched_criteria.extend(hit_keywords)

    if config.tech_nice_to_have:
        offer_tech_lower = {t.lower() for t in offer.tech_stack}
        matched_criteria.extend(
            t for t in config.tech_nice_to_have if t.lower() in offer_tech_lower
        )

    return MatchResult(matched=len(reasons) == 0, reasons=reasons, matched_criteria=matched_criteria)
