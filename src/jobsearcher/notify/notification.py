from jobsearcher.db.models import Offer
from jobsearcher.filter.engine import MatchResult


def _format_salary(offer: Offer) -> str:
    if offer.salary_min is None and offer.salary_max is None:
        return "Undisclosed"
    if offer.salary_min == offer.salary_max or offer.salary_max is None:
        amount = offer.salary_min
    else:
        amount = f"{offer.salary_min} - {offer.salary_max}"
    currency = offer.currency or ""
    return f"{amount} {currency}".strip()


def build_match_notification(offer: Offer, match_result: MatchResult) -> tuple[str, str]:
    """Returns (subject, body) for a new-match notification email."""
    subject = f"[job-searcher] New match: {offer.title} at {offer.company}"

    criteria_line = ", ".join(match_result.matched_criteria) if match_result.matched_criteria else "(none recorded)"

    body = (
        f"New matching offer found:\n\n"
        f"{offer.title} at {offer.company}\n"
        f"Location: {offer.location or 'unknown'} ({offer.remote_type or 'unknown'})\n"
        f"Salary: {_format_salary(offer)}\n"
        f"Contract: {offer.employment_type or 'unknown'}\n"
        f"Seniority: {offer.seniority or 'unknown'}\n"
        f"Apply type: {offer.apply_type or 'unknown'}\n\n"
        f"Link: {offer.url}\n\n"
        f"Matched criteria: {criteria_line}\n"
    )

    return subject, body
