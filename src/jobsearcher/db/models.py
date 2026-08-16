from dataclasses import dataclass, field


@dataclass
class Offer:
    id: int | None
    gmail_message_id: str | None
    url: str
    title: str
    company: str | None
    category: str | None
    seniority: str | None
    employment_type: str | None
    salary_min: int | None
    salary_max: int | None
    currency: str | None
    location: str | None
    remote_type: str | None
    tech_stack: list[str] = field(default_factory=list)
    apply_type: str | None = None
    status: str = "new"
    filter_reasons: list[str] = field(default_factory=list)
    first_seen_at: str = ""
    updated_at: str = ""


@dataclass
class CvVersion:
    id: int | None
    offer_id: int
    generated_at: str
    local_file_path: str
    drive_file_id: str | None = None
    drive_web_view_link: str | None = None
    bullet_ids_used: list[str] = field(default_factory=list)
    llm_model_used: str | None = None


@dataclass
class Application:
    id: int | None
    offer_id: int
    cv_version_id: int | None
    sent_at: str
    method: str
    status: str
    error_message: str | None = None
