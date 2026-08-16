"""
One-off validation: authenticate with the new Drive scope and upload a
throwaway PDF to confirm the whole flow works end-to-end.
Not part of the app's runtime pipeline.
"""

import os
import sys

from dotenv import load_dotenv

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from jobsearcher.gmail.auth import get_drive_service  # noqa: E402
from jobsearcher.tailor.drive_upload import upload_cv  # noqa: E402

load_dotenv()


def main():
    client_secrets_path = os.environ["GOOGLE_OAUTH_CLIENT_SECRETS_PATH"]
    token_path = os.environ["GOOGLE_OAUTH_TOKEN_PATH"]
    ca_bundle_path = os.environ.get("CA_BUNDLE_PATH") or None

    service = get_drive_service(client_secrets_path, token_path, ca_bundle_path)

    test_pdf_path = "scripts/_test_upload.pdf"
    with open(test_pdf_path, "wb") as f:
        f.write(b"%PDF-1.4\n%test file from job-searcher validation script\n")

    file_id, web_view_link = upload_cv(
        service, test_pdf_path, "job-searcher-drive-test.pdf",
        "https://justjoin.it/job-offer/test-offer",
    )

    print(f"Uploaded. file_id={file_id}")
    print(f"web_view_link={web_view_link}")

    os.remove(test_pdf_path)


if __name__ == "__main__":
    main()
