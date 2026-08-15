# Foundations: Scaffolding, DB Layer, Filter Engine Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stand up the project skeleton, the SQLite persistence layer, and the offer-filtering engine — the parts of the architecture plan (`C:\Users\kubag\.claude\plans\planning-session-job-groovy-flurry.md`) that need no external secrets (no Gmail OAuth, no LLM key, no live justjoin.it session) and can be fully unit-tested today.

**Architecture:** A `jobsearcher` Python package under `src/`, SQLite for offer/CV/application state, YAML for user-editable filter config. This plan covers only the DB layer and filter engine; ingestion (Gmail), enrichment (Playwright), CV tailoring (LLM), and sending are separate follow-on plans blocked on user-supplied inputs (see the architecture plan's "Open decisions" section).

**Tech Stack:** Python 3.11, stdlib `sqlite3`, `PyYAML`, `pytest`. No network or browser dependencies in this slice.

## Global Constraints

- Python 3.11 (confirmed installed on this machine).
- Package layout uses `src/` layout with `pyproject.toml` (no `setup.py`).
- All dates/timestamps stored as ISO-8601 UTC strings (`datetime.now(timezone.utc).isoformat()`).
- `tech_stack` and other list-valued offer fields are stored as JSON text in SQLite (`sqlite3` has no native array type) and decoded to Python lists in `models.py`.
- Offer `status` is one of: `new`, `enriched`, `matched`, `filtered_out`, `tailored`, `sent`, `notified`, `failed`.

---

## File Structure

```
job-searcher/
  pyproject.toml
  .env.example
  .gitignore
  README.md
  config/
    filters.example.yaml
    cv_library.example.yaml
  src/
    jobsearcher/
      __init__.py
      db/
        __init__.py
        schema.sql
        database.py
        models.py
        repository.py
      filter/
        __init__.py
        config.py
        engine.py
  tests/
    __init__.py
    conftest.py
    test_repository.py
    test_filter_engine.py
```

---

### Task 1: Project scaffolding

**Files:**
- Create: `pyproject.toml`
- Create: `.env.example`
- Create: `.gitignore`
- Create: `src/jobsearcher/__init__.py`
- Create: `config/filters.example.yaml`
- Create: `config/cv_library.example.yaml`

**Interfaces:**
- Produces: an installable `jobsearcher` package (`pip install -e .`) that later tasks add modules to.

- [ ] **Step 1: Create `pyproject.toml`**

```toml
[project]
name = "jobsearcher"
version = "0.1.0"
description = "Personal justjoin.it offer ingestion, filtering, CV tailoring, and application tool"
requires-python = ">=3.11"
dependencies = [
    "PyYAML>=6.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
]

[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[tool.setuptools.packages.find]
where = ["src"]
```

- [ ] **Step 2: Create `.gitignore`**

```
__pycache__/
*.pyc
.venv/
venv/
.env
*.db
*.sqlite3
data/
generated_cvs/
```

- [ ] **Step 3: Create `.env.example`**

```
# Copy to .env and fill in — .env is gitignored, never commit real secrets.

# Google Cloud OAuth client (Gmail API) — from Google Cloud Console credentials.json
GOOGLE_OAUTH_CLIENT_SECRETS_PATH=./secrets/gmail_client_secret.json
GOOGLE_OAUTH_TOKEN_PATH=./secrets/gmail_token.json

# LLM provider key used for CV tailoring
ANTHROPIC_API_KEY=

# SQLite database file location
DATABASE_PATH=./data/jobsearcher.db
```

- [ ] **Step 4: Create `src/jobsearcher/__init__.py`**

```python
__version__ = "0.1.0"
```

- [ ] **Step 5: Create `config/filters.example.yaml`**

```yaml
# Copy to config/filters.yaml and edit — this file is your actual filter criteria.
# Any list left empty means "no restriction" for that criterion.

role_keywords:            # offer title or tech stack must contain at least one (case-insensitive)
  - data engineer
  - analytics engineer
  - etl
  - pipeline
  - finance data

contract_types: []        # e.g. ["b2b"] — empty = accept any employment type

seniority: []              # e.g. ["mid", "senior"] — empty = accept any seniority

salary_floor: null         # e.g. 150 — minimum acceptable rate/salary, null = no floor
salary_period: hour        # hour | day | month — must match how you read justjoin.it rates
currency: PLN               # only enforced if the offer's currency matches; mismatches are not filtered

locations: []               # e.g. ["Warszawa", "remote"] — empty = accept any location
remote_ok: true             # if true, remote offers always pass the location check

tech_must_have: []          # ALL of these must appear in the offer's tech stack
tech_nice_to_have: []       # informational only — recorded in match reasons, doesn't filter

excluded_companies: []      # exact company name matches to always reject
excluded_industries: []     # informational for now — no industry field from ingestion yet
```

- [ ] **Step 6: Create `config/cv_library.example.yaml`**

```yaml
# Copy to config/cv_library.yaml and fill in with YOUR real, truthful experience.
# Each bullet is tagged with keywords the tailoring step matches against offer content.
# Do not add anything here that isn't true — the tailoring step only reorders/selects
# from this library, it never invents content.

summary: "Data engineer specializing in automating financial reporting and analytics pipelines."

experience:
  - company: "Example Corp"
    title: "Data Engineer"
    start_date: "2023-01"
    end_date: "present"
    bullets:
      - id: "example-1"
        text: "Built an ETL pipeline moving daily transaction data from Postgres to a Snowflake warehouse, cutting manual reporting time by 80%."
        tags: [etl, pipeline, finance, snowflake, postgres, reporting]

skills:
  - name: "Python"
    tags: [python]
  - name: "SQL"
    tags: [sql]
```

- [ ] **Step 7: Verify scaffolding installs**

Run: `cd "c:/Projects/job-searcher" && python -m venv .venv && .venv/Scripts/pip install -e ".[dev]"`
Expected: package installs with no errors, `pytest` and `PyYAML` present in `.venv`.

- [ ] **Step 8: Commit**

```bash
git init
git add pyproject.toml .gitignore .env.example config/ src/jobsearcher/__init__.py
git commit -m "chore: project scaffolding"
```

---

### Task 2: SQLite schema and database connection

**Files:**
- Create: `src/jobsearcher/db/__init__.py`
- Create: `src/jobsearcher/db/schema.sql`
- Create: `src/jobsearcher/db/database.py`
- Test: `tests/conftest.py`
- Test: `tests/test_repository.py` (connection portion only in this task)

**Interfaces:**
- Produces: `connect(db_path: str) -> sqlite3.Connection`, `init_db(conn: sqlite3.Connection) -> None`

- [ ] **Step 1: Create `src/jobsearcher/db/__init__.py`** (empty file)

- [ ] **Step 2: Create `src/jobsearcher/db/schema.sql`**

```sql
CREATE TABLE IF NOT EXISTS offers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    gmail_message_id TEXT,
    url TEXT NOT NULL UNIQUE,
    title TEXT NOT NULL,
    company TEXT,
    category TEXT,
    seniority TEXT,
    employment_type TEXT,
    salary_min INTEGER,
    salary_max INTEGER,
    currency TEXT,
    location TEXT,
    remote_type TEXT,
    tech_stack TEXT NOT NULL DEFAULT '[]',
    apply_type TEXT,
    status TEXT NOT NULL DEFAULT 'new',
    filter_reasons TEXT NOT NULL DEFAULT '[]',
    first_seen_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS cv_versions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    offer_id INTEGER NOT NULL REFERENCES offers(id),
    generated_at TEXT NOT NULL,
    file_path TEXT NOT NULL,
    bullet_ids_used TEXT NOT NULL DEFAULT '[]',
    llm_model_used TEXT
);

CREATE TABLE IF NOT EXISTS applications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    offer_id INTEGER NOT NULL REFERENCES offers(id),
    cv_version_id INTEGER REFERENCES cv_versions(id),
    sent_at TEXT NOT NULL,
    method TEXT NOT NULL,
    status TEXT NOT NULL,
    error_message TEXT
);
```

- [ ] **Step 3: Create `tests/__init__.py`** (empty file)

- [ ] **Step 4: Write `tests/conftest.py` (failing until Step 5)**

```python
import pytest

from jobsearcher.db.database import connect, init_db


@pytest.fixture
def conn():
    connection = connect(":memory:")
    init_db(connection)
    yield connection
    connection.close()
```

- [ ] **Step 5: Run to verify it fails**

Run: `.venv/Scripts/pytest tests/ -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'jobsearcher.db.database'`

- [ ] **Step 6: Write `src/jobsearcher/db/database.py`**

```python
import sqlite3
from importlib import resources


def connect(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    schema_sql = resources.files("jobsearcher.db").joinpath("schema.sql").read_text()
    conn.executescript(schema_sql)
    conn.commit()
```

- [ ] **Step 7: Add package data config so `schema.sql` ships with the package**

In `pyproject.toml`, add under `[tool.setuptools.packages.find]`:

```toml
[tool.setuptools.package-data]
jobsearcher = ["db/schema.sql"]
```

Run: `.venv/Scripts/pip install -e ".[dev]"` again to pick up the package-data change.

- [ ] **Step 8: Run to verify conftest now loads**

Run: `.venv/Scripts/pytest tests/ -v`
Expected: `no tests ran` (collection succeeds, no test functions yet) — confirms import chain works.

- [ ] **Step 9: Commit**

```bash
git add src/jobsearcher/db/__init__.py src/jobsearcher/db/schema.sql src/jobsearcher/db/database.py tests/__init__.py tests/conftest.py pyproject.toml
git commit -m "feat: sqlite schema and connection layer"
```

---

### Task 3: Models and repository functions

**Files:**
- Create: `src/jobsearcher/db/models.py`
- Create: `src/jobsearcher/db/repository.py`
- Test: `tests/test_repository.py`

**Interfaces:**
- Consumes: `connect`, `init_db` from Task 2 (`jobsearcher.db.database`)
- Produces:
  - `Offer` dataclass with fields: `id, gmail_message_id, url, title, company, category, seniority, employment_type, salary_min, salary_max, currency, location, remote_type, tech_stack, apply_type, status, filter_reasons, first_seen_at, updated_at`
  - `CvVersion` dataclass: `id, offer_id, generated_at, file_path, bullet_ids_used, llm_model_used`
  - `Application` dataclass: `id, offer_id, cv_version_id, sent_at, method, status, error_message`
  - `insert_offer(conn, offer: Offer) -> int` (idempotent on `url`, returns existing id if already present)
  - `get_offer_by_url(conn, url: str) -> Offer | None`
  - `get_offer(conn, offer_id: int) -> Offer | None`
  - `update_offer_enrichment(conn, offer_id: int, **fields) -> None`
  - `update_offer_status(conn, offer_id: int, status: str, filter_reasons: list[str] | None = None) -> None`
  - `list_offers_by_status(conn, status: str) -> list[Offer]`
  - `insert_cv_version(conn, cv: CvVersion) -> int`
  - `insert_application(conn, app: Application) -> int`

- [ ] **Step 1: Write failing tests in `tests/test_repository.py`**

```python
from datetime import datetime, timezone

from jobsearcher.db.models import Offer, CvVersion, Application
from jobsearcher.db.repository import (
    insert_offer,
    get_offer_by_url,
    get_offer,
    update_offer_enrichment,
    update_offer_status,
    list_offers_by_status,
    insert_cv_version,
    insert_application,
)


def make_offer(url="https://justjoin.it/job-offer/example-data-engineer"):
    now = datetime.now(timezone.utc).isoformat()
    return Offer(
        id=None,
        gmail_message_id="msg-1",
        url=url,
        title="Data Engineer",
        company="Acme",
        category="data",
        seniority=None,
        employment_type=None,
        salary_min=None,
        salary_max=None,
        currency=None,
        location=None,
        remote_type=None,
        tech_stack=[],
        apply_type=None,
        status="new",
        filter_reasons=[],
        first_seen_at=now,
        updated_at=now,
    )


def test_insert_and_get_offer_by_url(conn):
    offer_id = insert_offer(conn, make_offer())
    fetched = get_offer_by_url(conn, "https://justjoin.it/job-offer/example-data-engineer")
    assert fetched is not None
    assert fetched.id == offer_id
    assert fetched.title == "Data Engineer"
    assert fetched.tech_stack == []


def test_insert_offer_is_idempotent_on_url(conn):
    first_id = insert_offer(conn, make_offer())
    second_id = insert_offer(conn, make_offer())
    assert first_id == second_id
    assert len(list_offers_by_status(conn, "new")) == 1


def test_update_offer_enrichment(conn):
    offer_id = insert_offer(conn, make_offer())
    update_offer_enrichment(
        conn,
        offer_id,
        seniority="mid",
        employment_type="b2b",
        salary_min=150,
        salary_max=200,
        currency="PLN",
        location="Warszawa",
        remote_type="hybrid",
        tech_stack=["python", "airflow", "snowflake"],
        apply_type="native",
    )
    fetched = get_offer(conn, offer_id)
    assert fetched.status == "enriched"
    assert fetched.tech_stack == ["python", "airflow", "snowflake"]
    assert fetched.apply_type == "native"


def test_update_offer_status_with_reasons(conn):
    offer_id = insert_offer(conn, make_offer())
    update_offer_status(conn, offer_id, "filtered_out", filter_reasons=["salary below floor"])
    fetched = get_offer(conn, offer_id)
    assert fetched.status == "filtered_out"
    assert fetched.filter_reasons == ["salary below floor"]


def test_list_offers_by_status(conn):
    insert_offer(conn, make_offer("https://justjoin.it/job-offer/a"))
    second = insert_offer(conn, make_offer("https://justjoin.it/job-offer/b"))
    update_offer_status(conn, second, "matched")
    assert [o.status for o in list_offers_by_status(conn, "new")] == ["new"]
    assert [o.id for o in list_offers_by_status(conn, "matched")] == [second]


def test_insert_cv_version_and_application(conn):
    offer_id = insert_offer(conn, make_offer())
    now = datetime.now(timezone.utc).isoformat()
    cv_id = insert_cv_version(
        conn,
        CvVersion(
            id=None,
            offer_id=offer_id,
            generated_at=now,
            file_path="generated_cvs/2026-08-15_acme_data-engineer_v1.pdf",
            bullet_ids_used=["example-1"],
            llm_model_used="claude-sonnet-5",
        ),
    )
    assert cv_id is not None

    app_id = insert_application(
        conn,
        Application(
            id=None,
            offer_id=offer_id,
            cv_version_id=cv_id,
            sent_at=now,
            method="native_auto",
            status="sent",
            error_message=None,
        ),
    )
    assert app_id is not None
```

- [ ] **Step 2: Run to verify it fails**

Run: `.venv/Scripts/pytest tests/test_repository.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'jobsearcher.db.models'`

- [ ] **Step 3: Write `src/jobsearcher/db/models.py`**

```python
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
    file_path: str
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
```

- [ ] **Step 4: Write `src/jobsearcher/db/repository.py`**

```python
import json
import sqlite3
from datetime import datetime, timezone

from jobsearcher.db.models import Offer, CvVersion, Application


def _row_to_offer(row: sqlite3.Row) -> Offer:
    return Offer(
        id=row["id"],
        gmail_message_id=row["gmail_message_id"],
        url=row["url"],
        title=row["title"],
        company=row["company"],
        category=row["category"],
        seniority=row["seniority"],
        employment_type=row["employment_type"],
        salary_min=row["salary_min"],
        salary_max=row["salary_max"],
        currency=row["currency"],
        location=row["location"],
        remote_type=row["remote_type"],
        tech_stack=json.loads(row["tech_stack"]),
        apply_type=row["apply_type"],
        status=row["status"],
        filter_reasons=json.loads(row["filter_reasons"]),
        first_seen_at=row["first_seen_at"],
        updated_at=row["updated_at"],
    )


def insert_offer(conn: sqlite3.Connection, offer: Offer) -> int:
    existing = get_offer_by_url(conn, offer.url)
    if existing is not None:
        return existing.id

    cursor = conn.execute(
        """
        INSERT INTO offers (
            gmail_message_id, url, title, company, category, seniority,
            employment_type, salary_min, salary_max, currency, location,
            remote_type, tech_stack, apply_type, status, filter_reasons,
            first_seen_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            offer.gmail_message_id, offer.url, offer.title, offer.company,
            offer.category, offer.seniority, offer.employment_type,
            offer.salary_min, offer.salary_max, offer.currency, offer.location,
            offer.remote_type, json.dumps(offer.tech_stack), offer.apply_type,
            offer.status, json.dumps(offer.filter_reasons),
            offer.first_seen_at, offer.updated_at,
        ),
    )
    conn.commit()
    return cursor.lastrowid


def get_offer_by_url(conn: sqlite3.Connection, url: str) -> Offer | None:
    row = conn.execute("SELECT * FROM offers WHERE url = ?", (url,)).fetchone()
    return _row_to_offer(row) if row else None


def get_offer(conn: sqlite3.Connection, offer_id: int) -> Offer | None:
    row = conn.execute("SELECT * FROM offers WHERE id = ?", (offer_id,)).fetchone()
    return _row_to_offer(row) if row else None


def update_offer_enrichment(conn: sqlite3.Connection, offer_id: int, **fields) -> None:
    allowed = {
        "seniority", "employment_type", "salary_min", "salary_max", "currency",
        "location", "remote_type", "tech_stack", "apply_type",
    }
    unknown = set(fields) - allowed
    if unknown:
        raise ValueError(f"Unknown enrichment fields: {unknown}")

    columns = []
    values = []
    for key, value in fields.items():
        columns.append(f"{key} = ?")
        values.append(json.dumps(value) if key == "tech_stack" else value)

    columns.append("status = ?")
    values.append("enriched")
    columns.append("updated_at = ?")
    values.append(datetime.now(timezone.utc).isoformat())
    values.append(offer_id)

    conn.execute(f"UPDATE offers SET {', '.join(columns)} WHERE id = ?", values)
    conn.commit()


def update_offer_status(
    conn: sqlite3.Connection,
    offer_id: int,
    status: str,
    filter_reasons: list[str] | None = None,
) -> None:
    if filter_reasons is not None:
        conn.execute(
            "UPDATE offers SET status = ?, filter_reasons = ?, updated_at = ? WHERE id = ?",
            (status, json.dumps(filter_reasons), datetime.now(timezone.utc).isoformat(), offer_id),
        )
    else:
        conn.execute(
            "UPDATE offers SET status = ?, updated_at = ? WHERE id = ?",
            (status, datetime.now(timezone.utc).isoformat(), offer_id),
        )
    conn.commit()


def list_offers_by_status(conn: sqlite3.Connection, status: str) -> list[Offer]:
    rows = conn.execute("SELECT * FROM offers WHERE status = ? ORDER BY id", (status,)).fetchall()
    return [_row_to_offer(row) for row in rows]


def insert_cv_version(conn: sqlite3.Connection, cv: CvVersion) -> int:
    cursor = conn.execute(
        """
        INSERT INTO cv_versions (offer_id, generated_at, file_path, bullet_ids_used, llm_model_used)
        VALUES (?, ?, ?, ?, ?)
        """,
        (cv.offer_id, cv.generated_at, cv.file_path, json.dumps(cv.bullet_ids_used), cv.llm_model_used),
    )
    conn.commit()
    return cursor.lastrowid


def insert_application(conn: sqlite3.Connection, app: Application) -> int:
    cursor = conn.execute(
        """
        INSERT INTO applications (offer_id, cv_version_id, sent_at, method, status, error_message)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (app.offer_id, app.cv_version_id, app.sent_at, app.method, app.status, app.error_message),
    )
    conn.commit()
    return cursor.lastrowid
```

- [ ] **Step 5: Run to verify tests pass**

Run: `.venv/Scripts/pytest tests/test_repository.py -v`
Expected: PASS — all 6 tests green.

- [ ] **Step 6: Commit**

```bash
git add src/jobsearcher/db/models.py src/jobsearcher/db/repository.py tests/test_repository.py
git commit -m "feat: offer/cv/application repository with idempotent inserts"
```

---

### Task 4: Filter engine

**Files:**
- Create: `src/jobsearcher/filter/__init__.py`
- Create: `src/jobsearcher/filter/config.py`
- Create: `src/jobsearcher/filter/engine.py`
- Test: `tests/test_filter_engine.py`

**Interfaces:**
- Consumes: `Offer` from `jobsearcher.db.models` (Task 3)
- Produces:
  - `FilterConfig` dataclass with fields matching `config/filters.example.yaml` (`role_keywords, contract_types, seniority, salary_floor, salary_period, currency, locations, remote_ok, tech_must_have, tech_nice_to_have, excluded_companies, excluded_industries`)
  - `load_filter_config(path: str) -> FilterConfig`
  - `MatchResult` dataclass: `matched: bool, reasons: list[str], matched_criteria: list[str]`
  - `evaluate(offer: Offer, config: FilterConfig) -> MatchResult`

- [ ] **Step 1: Create `src/jobsearcher/filter/__init__.py`** (empty file)

- [ ] **Step 2: Write failing tests in `tests/test_filter_engine.py`**

```python
from jobsearcher.db.models import Offer
from jobsearcher.filter.config import FilterConfig
from jobsearcher.filter.engine import evaluate


def make_offer(**overrides) -> Offer:
    base = dict(
        id=1,
        gmail_message_id=None,
        url="https://justjoin.it/job-offer/x",
        title="Senior Data Engineer",
        company="Acme",
        category="data",
        seniority="senior",
        employment_type="b2b",
        salary_min=180,
        salary_max=220,
        currency="PLN",
        location="Warszawa",
        remote_type="hybrid",
        tech_stack=["python", "airflow", "dbt", "snowflake"],
        apply_type="native",
        status="enriched",
        filter_reasons=[],
        first_seen_at="2026-08-15T00:00:00+00:00",
        updated_at="2026-08-15T00:00:00+00:00",
    )
    base.update(overrides)
    return Offer(**base)


def base_config(**overrides) -> FilterConfig:
    base = dict(
        role_keywords=["data engineer"],
        contract_types=["b2b"],
        seniority=["mid", "senior"],
        salary_floor=150,
        salary_period="hour",
        currency="PLN",
        locations=["Warszawa"],
        remote_ok=True,
        tech_must_have=["python"],
        tech_nice_to_have=["dbt"],
        excluded_companies=[],
        excluded_industries=[],
    )
    base.update(overrides)
    return FilterConfig(**base)


def test_offer_matching_all_criteria_passes():
    result = evaluate(make_offer(), base_config())
    assert result.matched is True
    assert result.reasons == []
    assert "dbt" in result.matched_criteria


def test_offer_below_salary_floor_is_filtered():
    result = evaluate(make_offer(salary_max=120), base_config(salary_floor=150))
    assert result.matched is False
    assert any("salary" in r for r in result.reasons)


def test_offer_missing_role_keyword_is_filtered():
    result = evaluate(make_offer(title="Backend Java Developer", tech_stack=["java"]), base_config())
    assert result.matched is False
    assert any("role keyword" in r for r in result.reasons)


def test_offer_missing_must_have_tech_is_filtered():
    result = evaluate(make_offer(tech_stack=["java"]), base_config(tech_must_have=["python", "airflow"]))
    assert result.matched is False
    assert any("must-have tech" in r for r in result.reasons)


def test_offer_from_excluded_company_is_filtered():
    result = evaluate(make_offer(company="BadCo"), base_config(excluded_companies=["BadCo"]))
    assert result.matched is False
    assert any("excluded company" in r for r in result.reasons)


def test_remote_offer_bypasses_location_restriction():
    result = evaluate(
        make_offer(location="Krakow", remote_type="remote"),
        base_config(locations=["Warszawa"], remote_ok=True),
    )
    assert result.matched is True


def test_offer_wrong_contract_type_is_filtered():
    result = evaluate(make_offer(employment_type="uop"), base_config(contract_types=["b2b"]))
    assert result.matched is False
    assert any("contract type" in r for r in result.reasons)


def test_empty_config_lists_mean_no_restriction():
    result = evaluate(
        make_offer(employment_type="uop", seniority="junior", location="Gdansk", remote_type="onsite"),
        base_config(contract_types=[], seniority=[], locations=[], remote_ok=False, tech_must_have=[]),
    )
    assert result.matched is True
```

- [ ] **Step 3: Run to verify it fails**

Run: `.venv/Scripts/pytest tests/test_filter_engine.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'jobsearcher.filter.config'`

- [ ] **Step 4: Write `src/jobsearcher/filter/config.py`**

```python
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
```

- [ ] **Step 5: Write `src/jobsearcher/filter/engine.py`**

```python
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

    if config.contract_types and (offer.employment_type or "") not in config.contract_types:
        reasons.append(f"contract type '{offer.employment_type}' not in {config.contract_types}")

    if config.seniority and (offer.seniority or "") not in config.seniority:
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
```

- [ ] **Step 6: Run to verify tests pass**

Run: `.venv/Scripts/pytest tests/test_filter_engine.py -v`
Expected: PASS — all 8 tests green.

- [ ] **Step 7: Commit**

```bash
git add src/jobsearcher/filter/ tests/test_filter_engine.py
git commit -m "feat: config-driven offer filter engine"
```

---

### Task 5: README and full-suite verification

**Files:**
- Create: `README.md`

**Interfaces:**
- None — documentation only.

- [ ] **Step 1: Write `README.md`**

```markdown
# job-searcher

Personal tool that ingests justjoin.it "data" category job-alert emails, filters
offers against `config/filters.yaml`, tailors a CV per matching offer, and applies
to offers with justjoin.it's native quick-apply.

## Status

Foundations only: SQLite persistence layer and the filter engine are implemented
and tested. Ingestion (Gmail), enrichment (Playwright), CV tailoring (LLM), and
sending are not yet built — see `docs/superpowers/plans/` for the architecture
plan and follow-on implementation plans.

## Setup

\`\`\`bash
python -m venv .venv
.venv/Scripts/pip install -e ".[dev]"
cp config/filters.example.yaml config/filters.yaml   # then edit with your real criteria
cp config/cv_library.example.yaml config/cv_library.yaml   # then fill with your real CV content
cp .env.example .env   # then fill in secrets once later plans add Gmail/LLM integration
\`\`\`

## Tests

\`\`\`bash
.venv/Scripts/pytest tests/ -v
\`\`\`
```

- [ ] **Step 2: Run full test suite**

Run: `.venv/Scripts/pytest tests/ -v`
Expected: PASS — all tests from Tasks 3 and 4 green (14 tests total).

- [ ] **Step 3: Commit**

```bash
git add README.md
git commit -m "docs: project README and setup instructions"
```
