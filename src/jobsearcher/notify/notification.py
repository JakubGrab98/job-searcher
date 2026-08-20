from jobsearcher.db.models import CvVersion, Offer
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


def build_match_notification(
    offer: Offer, match_result: MatchResult, cv_version: CvVersion | None = None
) -> tuple[str, str]:
    """Returns (subject, body) for a new-match notification email."""
    subject = f"[job-searcher] New match: {offer.title} at {offer.company}"

    criteria_line = ", ".join(match_result.matched_criteria) if match_result.matched_criteria else "(none recorded)"

    if cv_version is not None:
        cv_line = cv_version.drive_web_view_link or cv_version.local_file_path
    else:
        cv_line = "not available yet (tailoring pending or failed — check the logs)"

    body = (
        f"New matching offer found:\n\n"
        f"{offer.title} at {offer.company}\n"
        f"Location: {offer.location or 'unknown'} ({offer.remote_type or 'unknown'})\n"
        f"Salary: {_format_salary(offer)}\n"
        f"Contract: {offer.employment_type or 'unknown'}\n"
        f"Seniority: {offer.seniority or 'unknown'}\n"
        f"Apply type: {offer.apply_type or 'unknown'}\n\n"
        f"Link: {offer.url}\n\n"
        f"Matched criteria: {criteria_line}\n\n"
        f"Tailored CV: {cv_line}\n"
    )

    return subject, body


def build_failure_alert(error_message: str, run_id: int | None = None) -> tuple[str, str]:
    """Returns (subject, body) for a whole-run-failed alert email — the
    single most important hardening feature for an unattended scheduled
    script: a broken pipeline gets noticed instead of silently stopping
    forever."""
    subject = "[job-searcher] Run failed — needs attention"

    body = (
        "A job-searcher run did not complete.\n\n"
        f"Run id: {run_id if run_id is not None else 'unknown'}\n"
        f"Error: {error_message}\n\n"
        "Check logs/run.log for the full traceback, or query the `runs` table "
        "for history. Common causes: justjoin.it changed page markup (breaks "
        "enrichment selectors), the alert email template changed (breaks "
        "parsing), an expired/revoked Google token, or an API outage.\n"
    )

    return subject, body
