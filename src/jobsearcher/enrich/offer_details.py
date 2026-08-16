import re
from dataclasses import dataclass, field

EMPLOYMENT_TIME_VALUES = {"Full-time", "Part-time"}
KNOWN_SENIORITY = {
    "Trainee", "Junior", "Junior+", "Mid", "Mid+", "Senior", "Senior+",
    "Expert", "Lead", "Manager / C-level",
}
KNOWN_WORK_MODES = {"Remote", "Hybrid", "Office", "Stationary"}

SALARY_RANGE_RE = re.compile(r"([\d\xa0]+)(?:\s*-\s*([\d\xa0]+))?\s*([A-Z]{3})")
SALARY_PERIOD_RE = re.compile(r"per\s+(month|hour|day)", re.IGNORECASE)


@dataclass
class OfferDetails:
    description: str = ""
    tech_stack: list[str] = field(default_factory=list)
    salary_min: int | None = None
    salary_max: int | None = None
    currency: str | None = None
    salary_period: str | None = None
    seniority: str | None = None
    employment_time: str | None = None
    contract_type: str | None = None
    work_mode: str | None = None


def _classify_chip_lines(text: str) -> dict:
    result = {"employment_time": None, "contract_type": None, "seniority": None, "work_mode": None}
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line in EMPLOYMENT_TIME_VALUES:
            result["employment_time"] = line
        elif line in KNOWN_WORK_MODES:
            result["work_mode"] = line
        elif line in KNOWN_SENIORITY:
            result["seniority"] = line
        elif line == "Permanent" or "B2B" in line or "Contract" in line:
            result["contract_type"] = line
    return result


def _parse_salary(text: str) -> dict:
    idx = text.find("\nSALARY\n")
    if idx == -1:
        return {"salary_min": None, "salary_max": None, "currency": None, "salary_period": None}

    block = text[idx + len("\nSALARY\n"):idx + len("\nSALARY\n") + 200]
    lines = [l.strip() for l in block.splitlines() if l.strip()]
    if not lines:
        return {"salary_min": None, "salary_max": None, "currency": None, "salary_period": None}

    amount_match = SALARY_RANGE_RE.search(lines[0])
    if not amount_match:
        return {"salary_min": None, "salary_max": None, "currency": None, "salary_period": None}

    low_raw, high_raw, currency = amount_match.groups()
    low = int(low_raw.replace("\xa0", ""))
    high = int(high_raw.replace("\xa0", "")) if high_raw else low

    period = None
    if len(lines) > 1:
        period_match = SALARY_PERIOD_RE.search(lines[1])
        if period_match:
            period = period_match.group(1).lower()

    return {"salary_min": low, "salary_max": high, "currency": currency, "salary_period": period}


def _parse_tech_stack(text: str) -> list[str]:
    start = text.find("TECH STACK")
    if start == -1:
        return []
    start += len("TECH STACK")
    end = text.find("OFFICE LOCATION", start)
    if end == -1:
        end = start + 2000
    block = text[start:end]
    lines = [l.strip() for l in block.splitlines() if l.strip()]
    # Alternating (skill name, level) pairs — take every even-indexed line.
    return lines[0::2]


def _parse_description(text: str) -> str:
    start = text.find("JOB DESCRIPTION")
    if start == -1:
        return ""
    start += len("JOB DESCRIPTION")
    end = text.find("TECH STACK", start)
    if end == -1:
        end = len(text)
    return text[start:end].strip()


def parse_offer_details(body_text: str) -> OfferDetails:
    chips = _classify_chip_lines(body_text[: body_text.find("JOB DESCRIPTION")])
    salary = _parse_salary(body_text)

    return OfferDetails(
        description=_parse_description(body_text),
        tech_stack=_parse_tech_stack(body_text),
        seniority=chips["seniority"],
        employment_time=chips["employment_time"],
        contract_type=chips["contract_type"],
        work_mode=chips["work_mode"],
        **salary,
    )
