# Google Cloud Setup

This project uses two Google APIs under one OAuth client:

- **Gmail API** — reads justjoin.it job-alert emails, sends match notifications
- **Google Drive API** — stores generated CV PDFs (`drive.file` scope only —
  the app can see/manage only files it creates itself, not your whole Drive)

Everything below happens once, in your own Google account. This has already
been done for this project (project `job-searcher-505615`) — this doc exists
so it can be repeated (new machine, revoked access, new scope) without
re-deriving it from scratch.

## 1. Create or select a Google Cloud project

[console.cloud.google.com](https://console.cloud.google.com) → create a new
project (e.g. "job-searcher") or reuse an existing one.

## 2. Enable the APIs

APIs & Services → Library → enable, one at a time:
- **Gmail API**
- **Google Drive API**

Both are required — they're separate APIs even though this project uses one
OAuth client/consent screen for both.

## 3. Configure the OAuth consent screen

APIs & Services → OAuth consent screen. Google splits this into tabs:

**Branding**
- App name: anything (e.g. "job-searcher")
- User support email: your Gmail address
- Developer contact information: your Gmail address (required)

**Audience**
- User type: **External** (personal Gmail accounts can't use Internal)
- Publishing status: **Testing** — not Production. Testing mode works
  indefinitely for listed test users with no Google review needed, even for
  the sensitive scopes below. Production would show every sign-in an
  "unverified app" warning and eventually require completing Google's
  verification process, for zero benefit when you're the only user.
- Test users: add your own Gmail address here — required in Testing mode, or
  auth is refused.

**Data Access** — add these scopes:
```
https://www.googleapis.com/auth/gmail.modify
https://www.googleapis.com/auth/gmail.send
https://www.googleapis.com/auth/drive.file
```
`gmail.modify` (not just `.readonly`) is needed because the app marks
alert emails as read after processing them, not just reads them.

## 4. Create OAuth client credentials

APIs & Services → Credentials → Create Credentials → OAuth client ID.
- Application type: **Desktop app** — not Web app. This avoids needing a
  redirect URI/webserver; the client library opens a local browser window
  for you to approve once, using a loopback redirect.
- Download the resulting JSON.

## 5. Place the credentials file

Save the downloaded JSON at:
```
secrets/gmail_client_secret.json
```
`secrets/` is gitignored — this file (and the token generated in step 7)
must never be committed.

## 6. Configure `.env`

Copy `.env.example` to `.env` and fill in:
```
GOOGLE_OAUTH_CLIENT_SECRETS_PATH=./secrets/gmail_client_secret.json
GOOGLE_OAUTH_TOKEN_PATH=./secrets/gmail_token.json
NOTIFY_EMAIL=<your Gmail address>
```
If you're behind TLS-intercepting antivirus/proxy software (this project hit
it with Avast — see Troubleshooting below), also set `CA_BUNDLE_PATH`.

## 7. First run — authorize

Run anything that calls `get_gmail_service()` or `get_drive_service()` (e.g.
`run.py`, or `scripts/fetch_sample_alert.py`):
```
.venv/Scripts/python.exe run.py
```
A browser window opens listing the Gmail + Drive permissions above — approve
it once. This caches a refresh token at `secrets/gmail_token.json`; you won't
be asked again unless the token is deleted or new scopes are added.

## Troubleshooting

**Generic Google 500 error page during the consent flow**
Usually means the consent screen isn't fully configured — go back and check
the **Branding** tab specifically (App name, User support email, Developer
contact email are all required, even in Testing mode).

**"Google hasn't verified this app" warning**
Means the app is in **Production**, not Testing. Go to Audience → switch
back to Testing, and make sure your account is listed under Test users.

**`SSLCertVerificationError: unable to get local issuer certificate`**
TLS-intercepting antivirus/proxy (this project hit it with Avast). Two
libraries are involved and need to trust the interceptor's root cert
separately:
- `google-auth-oauthlib`'s token exchange goes through `requests`, which
  honors `REQUESTS_CA_BUNDLE`.
- The actual Gmail/Drive API calls go through `httplib2`, which does **not**
  read `REQUESTS_CA_BUNDLE` — it needs `ca_certs` passed explicitly.

Both are already wired up in `src/jobsearcher/gmail/auth.py` via the
`CA_BUNDLE_PATH` env var — just set it to your interceptor's root cert path
(e.g. `C:\ProgramData\Avast Software\Avast\wscert.pem` for Avast) and both
code paths pick it up.

**Adding a new scope later**
1. Add the scope string to `SCOPES` in `src/jobsearcher/gmail/auth.py`.
2. Add it under OAuth consent screen → Data Access, same as step 3 above.
3. Delete `secrets/gmail_token.json` — the cached token was authorized
   without the new scope and won't have it until you re-consent.
4. Run anything that builds a Google service again to trigger a fresh
   browser consent flow covering the new scope.

This is exactly how the Drive scope was added after Gmail was already
working.
