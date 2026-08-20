# Google Cloud Setup

This project uses two Google APIs under one OAuth client:

- **Gmail API** — reads justjoin.it job-alert emails, sends match notifications
- **Google Drive API** — stores generated CV PDFs (`drive.file` scope only —
  the app can see/manage only files it creates itself, not your whole Drive)

Everything below happens once, in a Google account. This doc exists so it can
be repeated (new machine, revoked access, new scope) without re-deriving it
from scratch. Part of the broader [`setup-guide.md`](setup-guide.md) — start
there for the full picture, come here for the Google-specific portion and
troubleshooting.

## Two-account setup

The OAuth credential authenticates as **one** Google account, and Gmail API
calls always operate on that account's own mailbox ("me") — so whichever
account grants consent is both where alert emails are read from *and* where
notification emails are sent *from*. This project deliberately uses two
different addresses for two different roles:

- **Ingestion account** (a dedicated mailbox) — this is the account the
  OAuth credential authenticates as, and the one that needs justjoin.it's
  alert emails pointed at it (change this in your justjoin.it account's
  notification settings — that's on their side, not something this
  project's code does).
- **Notification recipient** (your personal address) — set via
  `NOTIFY_EMAIL` in `.env`. Match emails are sent *from* the ingestion account
  *to* whatever `NOTIFY_EMAIL` is, so this can be any address — no extra
  Google setup needed for it, it's just the `to:` header on outgoing mail.

If you ever want ingestion and notifications on the same address again, just
point both at it — nothing in the code assumes they differ.

This project currently runs on GCP project `job-searcher-dev`, authenticated
as the dedicated ingestion account (superseded an earlier `job-searcher-505615`
project that was authenticated as the personal account directly).

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
TLS-intercepting antivirus/proxy (this project hit it with Avast). Three
libraries are involved and each needs its own cert configuration:
`requests` (OAuth token exchange, `REQUESTS_CA_BUNDLE`), `httplib2` (actual
Gmail/Drive API calls, `ca_certs` param), and `httpx` (Anthropic SDK,
`verify=` param) — none of them share config with each other.

All three are wired up in `src/jobsearcher/gmail/auth.py` /
`src/jobsearcher/ssl_utils.py` via the `CA_BUNDLE_PATH` env var — set it to
your interceptor's root cert path (e.g.
`C:\ProgramData\Avast Software\Avast\wscert.pem` for Avast).

**Important**: don't trust the interceptor's cert *alone* — whether a given
connection actually gets intercepted varies by execution context (confirmed
live: works interactively, fails identically under Windows Task Scheduler,
because that context's connections apparently aren't intercepted and hit
the real Google certificate chain, which only the interceptor's root can't
validate). `ssl_utils.build_combined_ca_bundle()` merges the standard
public trust roots (via `certifi`) with the interceptor's cert into one
bundle, which is what actually gets passed to all three libraries — covers
both the intercepted and non-intercepted case regardless of context. If you
see this error only in one context (e.g. only when scheduled, not
interactively, or vice versa), that mismatch is exactly why — don't
special-case it further, the combined bundle is the fix.

**Adding a new scope later**
1. Add the scope string to `SCOPES` in `src/jobsearcher/gmail/auth.py`.
2. Add it under OAuth consent screen → Data Access, same as step 3 above.
3. Delete `secrets/gmail_token.json` — the cached token was authorized
   without the new scope and won't have it until you re-consent.
4. Run anything that builds a Google service again to trigger a fresh
   browser consent flow covering the new scope.

This is exactly how the Drive scope was added after Gmail was already
working.
