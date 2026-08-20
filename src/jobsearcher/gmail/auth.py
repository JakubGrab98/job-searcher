import os

import httplib2
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_httplib2 import AuthorizedHttp
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from jobsearcher.ssl_utils import build_combined_ca_bundle

SCOPES = [
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/drive.file",
]


def get_credentials(client_secrets_path: str, token_path: str, ca_bundle_path: str | None = None) -> Credentials:
    # google-auth-oauthlib's token exchange goes through `requests`, which
    # honors REQUESTS_CA_BUNDLE. On machines with TLS-intercepting antivirus
    # (e.g. Avast), the default trust store rejects the interceptor's cert.
    # Whether a given connection actually gets intercepted varies by
    # execution context (confirmed live: interactive sessions vs. Windows
    # Task Scheduler behave differently) — trusting ONLY the intercepting
    # cert breaks the not-intercepted case, so a combined bundle (standard
    # public roots + the intercepting cert) is used instead of the raw
    # CA_BUNDLE_PATH file.
    if ca_bundle_path:
        os.environ.setdefault("REQUESTS_CA_BUNDLE", build_combined_ca_bundle(ca_bundle_path))

    creds = None
    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(client_secrets_path, SCOPES)
            creds = flow.run_local_server(port=0)

        os.makedirs(os.path.dirname(token_path), exist_ok=True)
        with open(token_path, "w", encoding="utf-8") as f:
            f.write(creds.to_json())

    return creds


def _build_service(service_name: str, version: str, client_secrets_path: str, token_path: str, ca_bundle_path: str | None):
    creds = get_credentials(client_secrets_path, token_path, ca_bundle_path)
    # The actual API calls go through httplib2, which does NOT read
    # REQUESTS_CA_BUNDLE — it needs its own ca_certs passed explicitly.
    # Same combined-bundle reasoning as get_credentials() above.
    if ca_bundle_path:
        http = httplib2.Http(ca_certs=build_combined_ca_bundle(ca_bundle_path))
    else:
        http = httplib2.Http()
    authorized_http = AuthorizedHttp(creds, http=http)
    return build(service_name, version, http=authorized_http)


def get_gmail_service(client_secrets_path: str, token_path: str, ca_bundle_path: str | None = None):
    return _build_service("gmail", "v1", client_secrets_path, token_path, ca_bundle_path)


def get_drive_service(client_secrets_path: str, token_path: str, ca_bundle_path: str | None = None):
    return _build_service("drive", "v3", client_secrets_path, token_path, ca_bundle_path)
