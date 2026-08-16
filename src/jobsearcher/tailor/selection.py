from dataclasses import dataclass, field


@dataclass
class SelectedExperience:
    company: str
    team: str | None
    role: str
    dates: str
    bullet_ids: list[str] = field(default_factory=list)


@dataclass
class CvSelection:
    summary_key: str | None
    experience: list[SelectedExperience] = field(default_factory=list)
    skill_names: list[str] = field(default_factory=list)
    include_education: bool = True
    include_certifications: bool = True


def default_selection(library: dict) -> CvSelection:
    """Includes everything in the library — used as-is until the LLM-driven
    selective picking (needs ANTHROPIC_API_KEY) is wired in."""
    experience = [
        SelectedExperience(
            company=role["company"],
            team=role.get("team"),
            role=role["role"],
            dates=role["dates"],
            bullet_ids=[b["id"] for b in role.get("bullets", [])],
        )
        for role in library.get("experience", [])
    ]
    summaries = library.get("summaries", {})
    summary_key = next(iter(summaries), None)
    skill_names = [s["name"] for s in library.get("skills", [])]

    return CvSelection(summary_key=summary_key, experience=experience, skill_names=skill_names)
