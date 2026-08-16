from jobsearcher.tailor.drive_upload import upload_cv


class _FakeExecutable:
    def __init__(self, response):
        self._response = response

    def execute(self):
        return self._response


class _FakeFiles:
    def __init__(self, existing_folders=None):
        self.existing_folders = existing_folders or []
        self.created = []

    def list(self, q, spaces, fields):
        matches = [f for f in self.existing_folders if f["name"] in q]
        return _FakeExecutable({"files": matches})

    def create(self, body, fields, media_body=None):
        record = {"body": body, "media_body": media_body}
        self.created.append(record)
        file_id = f"file-{len(self.created)}"
        response = {"id": file_id}
        if "webViewLink" in fields:
            response["webViewLink"] = f"https://drive.google.com/file/d/{file_id}/view"
        return _FakeExecutable(response)


class _FakeDriveService:
    def __init__(self, existing_folders=None):
        self._files = _FakeFiles(existing_folders)

    def files(self):
        return self._files


def test_upload_cv_creates_folder_when_missing(tmp_path):
    pdf_path = tmp_path / "cv.pdf"
    pdf_path.write_bytes(b"%PDF-1.4 fake content")

    service = _FakeDriveService(existing_folders=[])
    upload_cv(service, str(pdf_path), "2026-08-16_acme_data-engineer_v1.pdf", "https://justjoin.it/job-offer/acme")

    folder_creates = [c for c in service._files.created if c["body"].get("mimeType") == "application/vnd.google-apps.folder"]
    assert len(folder_creates) == 1
    assert folder_creates[0]["body"]["name"] == "job-searcher CVs"


def test_upload_cv_reuses_existing_folder(tmp_path):
    pdf_path = tmp_path / "cv.pdf"
    pdf_path.write_bytes(b"%PDF-1.4 fake content")

    service = _FakeDriveService(existing_folders=[{"id": "existing-folder-id", "name": "job-searcher CVs"}])
    upload_cv(service, str(pdf_path), "cv.pdf", "https://justjoin.it/job-offer/acme")

    folder_creates = [c for c in service._files.created if c["body"].get("mimeType") == "application/vnd.google-apps.folder"]
    assert len(folder_creates) == 0

    file_creates = [c for c in service._files.created if c["body"].get("mimeType") != "application/vnd.google-apps.folder"]
    assert file_creates[0]["body"]["parents"] == ["existing-folder-id"]


def test_upload_cv_sets_offer_url_as_description(tmp_path):
    pdf_path = tmp_path / "cv.pdf"
    pdf_path.write_bytes(b"%PDF-1.4 fake content")

    service = _FakeDriveService(existing_folders=[{"id": "folder-1", "name": "job-searcher CVs"}])
    upload_cv(service, str(pdf_path), "cv.pdf", "https://justjoin.it/job-offer/acme")

    file_create = [c for c in service._files.created if c["body"].get("mimeType") != "application/vnd.google-apps.folder"][0]
    assert file_create["body"]["description"] == "https://justjoin.it/job-offer/acme"
    assert file_create["body"]["name"] == "cv.pdf"


def test_upload_cv_returns_file_id_and_web_view_link(tmp_path):
    pdf_path = tmp_path / "cv.pdf"
    pdf_path.write_bytes(b"%PDF-1.4 fake content")

    service = _FakeDriveService(existing_folders=[{"id": "folder-1", "name": "job-searcher CVs"}])
    file_id, web_view_link = upload_cv(service, str(pdf_path), "cv.pdf", "https://justjoin.it/job-offer/acme")

    assert file_id.startswith("file-")
    assert web_view_link.startswith("https://drive.google.com/file/d/")
