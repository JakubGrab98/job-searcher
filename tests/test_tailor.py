import json
import os
from datetime import datetime, timezone

from jobsearcher.db.models import Offer
from jobsearcher.db.repository import get_cv_version_by_offer, insert_offer
from jobsearcher.tailor.cv_library import load_cv_library
from jobsearcher.tailor.tailor import tailor_cv_for_offer

FIXTURE_PATH = os.path.join(os.path.dirname(__file__), "fixtures", "cv_library_sample.yaml")


def make_offer(**overrides):
    now = datetime.now(timezone.utc).isoformat()
    base = dict(
        id=None, gmail_message_id="msg-1", url="https://justjoin.it/job-offer/acme-data-engineer",
        title="Data Engineer", company="Acme Corp", category="data", description="Looking for dbt experience.",
        seniority="Senior", employment_type="B2B", salary_min=180, salary_max=220, currency="PLN",
        location="Warszawa", remote_type="Remote", tech_stack=["dbt"], apply_type="native",
        status="matched", filter_reasons=[], first_seen_at=now, updated_at=now,
    )
    base.update(overrides)
    return Offer(**base)


class _FakeContentBlock:
    def __init__(self, text):
        self.text = text


class _FakeAnthropicClient:
    def __init__(self, library):
        role_id = library["experience"][0]["id"]
        bullet_id = library["experience"][0]["bullets"][0]["id"]
        self._response_text = json.dumps(
            {"summary_key": "general_data_engineer", "experience": [{"role_id": role_id, "bullet_ids": [bullet_id]}], "skill_names": ["Python"]}
        )
        self.call_count = 0

    class _Messages:
        def __init__(self, outer):
            self._outer = outer

        def create(self, **kwargs):
            self._outer.call_count += 1
            return type("R", (), {"content": [_FakeContentBlock(self._outer._response_text)]})()

    @property
    def messages(self):
        return self._Messages(self)


class _FakeExecutable:
    def __init__(self, response):
        self._response = response

    def execute(self):
        return self._response


class _FakeDriveFiles:
    def list(self, q, spaces, fields):
        return _FakeExecutable({"files": [{"id": "folder-1", "name": "job-searcher CVs"}]})

    def create(self, body, fields, media_body=None):
        return _FakeExecutable({"id": "drive-file-1", "webViewLink": "https://drive.google.com/file/d/drive-file-1/view"})


class _FakeDriveService:
    def files(self):
        return _FakeDriveFiles()


def _fake_render_pdf(html, output_path):
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("fake pdf content")


def test_tailor_cv_for_offer_creates_cv_version(conn, tmp_path):
    library = load_cv_library(FIXTURE_PATH)
    offer_id = insert_offer(conn, make_offer())
    offer = make_offer(id=offer_id)
    client = _FakeAnthropicClient(library)
    drive = _FakeDriveService()

    cv = tailor_cv_for_offer(client, drive, library, conn, offer, render_pdf_fn=_fake_render_pdf, output_dir=str(tmp_path))

    assert cv is not None
    assert cv.offer_id == offer_id
    assert cv.drive_file_id == "drive-file-1"
    assert cv.drive_web_view_link == "https://drive.google.com/file/d/drive-file-1/view"
    assert os.path.exists(cv.local_file_path)
    assert client.call_count == 1


def test_tailor_cv_for_offer_is_idempotent(conn, tmp_path):
    library = load_cv_library(FIXTURE_PATH)
    offer_id = insert_offer(conn, make_offer())
    offer = make_offer(id=offer_id)
    client = _FakeAnthropicClient(library)
    drive = _FakeDriveService()

    first = tailor_cv_for_offer(client, drive, library, conn, offer, render_pdf_fn=_fake_render_pdf, output_dir=str(tmp_path))
    second = tailor_cv_for_offer(client, drive, library, conn, offer, render_pdf_fn=_fake_render_pdf, output_dir=str(tmp_path))

    assert first.id == second.id
    assert client.call_count == 1  # never called the LLM twice for the same offer


def test_tailor_cv_for_offer_filename_uses_company_and_title_slugs(conn, tmp_path):
    library = load_cv_library(FIXTURE_PATH)
    offer_id = insert_offer(conn, make_offer(company="Acme Corp!", title="Senior Data / Engineer"))
    offer = make_offer(id=offer_id, company="Acme Corp!", title="Senior Data / Engineer")
    client = _FakeAnthropicClient(library)
    drive = _FakeDriveService()

    cv = tailor_cv_for_offer(client, drive, library, conn, offer, render_pdf_fn=_fake_render_pdf, output_dir=str(tmp_path))

    filename = os.path.basename(cv.local_file_path)
    assert "acme-corp" in filename
    assert "senior-data-engineer" in filename
    assert filename.endswith(".pdf")


def test_tailor_cv_for_offer_records_bullet_ids_used(conn, tmp_path):
    library = load_cv_library(FIXTURE_PATH)
    offer_id = insert_offer(conn, make_offer())
    offer = make_offer(id=offer_id)
    client = _FakeAnthropicClient(library)
    drive = _FakeDriveService()
    expected_bullet_id = library["experience"][0]["bullets"][0]["id"]

    cv = tailor_cv_for_offer(client, drive, library, conn, offer, render_pdf_fn=_fake_render_pdf, output_dir=str(tmp_path))

    assert cv.bullet_ids_used == [expected_bullet_id]
