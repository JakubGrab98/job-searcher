from googleapiclient.http import MediaFileUpload

FOLDER_NAME = "job-searcher CVs"


def _find_or_create_folder(service, name: str = FOLDER_NAME) -> str:
    query = f"name = '{name}' and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
    results = service.files().list(q=query, spaces="drive", fields="files(id, name)").execute()
    matches = results.get("files", [])
    if matches:
        return matches[0]["id"]

    folder = (
        service.files()
        .create(body={"name": name, "mimeType": "application/vnd.google-apps.folder"}, fields="id")
        .execute()
    )
    return folder["id"]


def upload_cv(service, local_path: str, filename: str, offer_url: str) -> tuple[str, str]:
    """Uploads a CV PDF to the (auto-created if missing) job-searcher CVs
    folder, with the offer URL stored in the file's description field.
    Returns (file_id, web_view_link). Files stay private (owner-only)."""
    folder_id = _find_or_create_folder(service)

    file_metadata = {
        "name": filename,
        "parents": [folder_id],
        "description": offer_url,
    }
    media = MediaFileUpload(local_path, mimetype="application/pdf")
    uploaded = (
        service.files()
        .create(body=file_metadata, media_body=media, fields="id, webViewLink")
        .execute()
    )
    return uploaded["id"], uploaded["webViewLink"]
