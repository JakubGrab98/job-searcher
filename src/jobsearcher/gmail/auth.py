import os

import httplib2
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_httplib2 import AuthorizedHttp
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = [
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/gmail.send",
]


def get_credentials(client_secrets_path: str, token_path: str, ca_bundle_path: str | None = None) -> Credentials:
    # google-auth-oauthlib's token exchange goes through `requests`, which
    # honors REQUESTS_CA_BUNDLE. On machines with TLS-intercepting antivirus
    # (e.g. Avast), the default trust store rejects the interceptor's cert,
    # so a custom bundle path can be supplied via CA_BUNDLE_PATH in .env.
    if ca_bundle_path:
        os.environ.setdefault("REQUESTS_CA_BUNDLE", ca_bundle_path)

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


def get_gmail_service(client_secrets_path: str, token_path: str, ca_bundle_path: str | None = None):
    creds = get_credentials(client_secrets_path, token_path, ca_bundle_path)
    # The actual Gmail API calls go through httplib2, which does NOT read
    # REQUESTS_CA_BUNDLE — it needs its own ca_certs passed explicitly.
    http = httplib2.Http(ca_certs=ca_bundle_path) if ca_bundle_path else httplib2.Http()
    authorized_http = AuthorizedHttp(creds, http=http)
    return build("gmail", "v1", http=authorized_http)
