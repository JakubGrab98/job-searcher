# Setup Guide

End-to-end instructions for getting job-searcher running from scratch, on a
new machine or after a reinstall. For Google-specific steps see
[`google-cloud-setup.md`](google-cloud-setup.md) (linked inline below); for
ongoing tuning after it's running see [`tuning-guide.md`](tuning-guide.md).

## Prerequisites

- Windows (this guide assumes PowerShell + Windows Task Scheduler — the
  Python code itself is cross-platform, but scheduling instructions here
  are Windows-specific)
- Python 3.11+
- A Google account to receive justjoin.it alerts and send notifications from
  (can be the same account as the notification recipient, or a dedicated
  one — see "Two-account setup" in the architecture plan for why this
  project uses two)
- An [Anthropic API key](https://console.anthropic.com/) for CV tailoring

## 1. Python environment

```bash
cd c:\Projects\job-searcher
python -m venv .venv
.venv\Scripts\pip install -e ".[dev]"
.venv\Scripts\python -m playwright install chromium
```

If `pip install` fails with an SSL certificate error (common behind
antivirus HTTPS interception, e.g. Avast), install with the interceptor's
root cert trusted:

```bash
.venv\Scripts\pip install --cert "<path-to-interceptor-root-cert>.pem" --trusted-host pypi.org --trusted-host files.pythonhosted.org -e ".[dev]"
```

## 2. Google Cloud / Gmail / Drive setup

Full walkthrough (project creation, API enablement, OAuth consent screen,
credentials, scopes, troubleshooting): **[`google-cloud-setup.md`](google-cloud-setup.md)**.

End state: `secrets/gmail_client_secret.json` exists (the OAuth client
credentials downloaded from Google Cloud Console). The refresh token
(`secrets/gmail_token.json`) gets created automatically the first time you
run anything that authenticates — see step 6.

## 3. Configure `.env`

```bash
cp .env.example .env
```

Fill in each value:

| Variable | What it is |
|---|---|
| `GOOGLE_OAUTH_CLIENT_SECRETS_PATH` | Path to the file from step 2 — default `./secrets/gmail_client_secret.json` is usually fine as-is |
| `GOOGLE_OAUTH_TOKEN_PATH` | Where the auto-generated refresh token gets cached — default `./secrets/gmail_token.json`, don't need to create this yourself |
| `ANTHROPIC_API_KEY` | From [console.anthropic.com](https://console.anthropic.com/) |
| `DATABASE_PATH` | SQLite file location — default `./data/jobsearcher.db` is fine |
| `NOTIFY_EMAIL` | Where match notification emails get sent — your real inbox |
| `CA_BUNDLE_PATH` | Only needed behind TLS-intercepting antivirus/proxy (e.g. Avast) — see the SSL troubleshooting section in `google-cloud-setup.md`. Leave blank otherwise. |

## 4. Configure your filter criteria

```bash
cp config/filters.example.yaml config/filters.yaml
```

Edit `config/filters.yaml` with your real role keywords, seniority, salary
floor, location/remote preference, tech stack requirements, and any
excluded companies. Field semantics (substring matching, case sensitivity,
etc.) are documented in [`tuning-guide.md`](tuning-guide.md).

## 5. Author your CV bullet library

```bash
cp config/cv_library.example.yaml config/cv_library.yaml
```

Fill in `config/cv_library.yaml` with your real, truthful experience —
this is the *only* source of content the LLM tailoring step can draw from,
it never invents anything. See the schema comments in the file itself and
[`tuning-guide.md`](tuning-guide.md) for authoring guidance (e.g. how
`variant_of` works, handling two roles at the same company).

The rendered CV's visual design (two-column layout, navy header, skill
bars) lives in `src/jobsearcher/tailor/templates/cv_template.html` — edit
that HTML/CSS directly if you want a different look; nothing else needs
touching to change it.

## 6. First run — verify everything end to end

```bash
.venv\Scripts\python.exe run.py
```

This is also what triggers the first Google OAuth consent: a browser
window opens listing the Gmail + Drive permissions — approve it once, and
`secrets/gmail_token.json` gets created so you're not asked again.

Check the output — `Run complete: {...}` with an `ingested`/`matched`/etc.
stats dict means it worked. Look at `logs/run.log` for the same info logged
with timestamps, and confirm `data/jobsearcher.db` was created:

```bash
.venv\Scripts\python.exe -c "
from jobsearcher.db.database import connect
from jobsearcher.db.repository import list_recent_runs
conn = connect('data/jobsearcher.db')
for r in list_recent_runs(conn, limit=5):
    print(r.started_at, r.status, r.stats or r.error_message)
"
```

If a match happens to be found on this first run, check your `NOTIFY_EMAIL`
inbox for the notification, and Google Drive for a new "job-searcher CVs"
folder with the generated PDF.

## 7. Schedule it (Windows Task Scheduler)

The tool is meant to run on a schedule, not continuously or purely on
demand. **Check how often justjoin.it actually sends your alert digest
before picking an interval** — this project observed it arrives once daily
after 10 AM, not continuously, so the schedule here is once-daily. Adjust
the trigger below to match what you actually observe.

Register the task via PowerShell (run as your normal user, no elevation
needed):

```powershell
$action = New-ScheduledTaskAction `
    -Execute "c:\Projects\job-searcher\.venv\Scripts\python.exe" `
    -Argument "run.py" `
    -WorkingDirectory "c:\Projects\job-searcher"

$trigger = New-ScheduledTaskTrigger -Daily -At "10:30AM"

$settings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -WakeToRun `
    -DontStopOnIdleEnd `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 10) `
    -MultipleInstances IgnoreNew

Register-ScheduledTask -TaskName "job-searcher-run" `
    -Action $action -Trigger $trigger -Settings $settings `
    -Description "Runs the job-searcher pipeline daily. See c:\Projects\job-searcher\README.md"
```

What each setting does:
- **`-StartWhenAvailable`**: if the scheduled time is missed (laptop was
  off/asleep), runs as soon as it's next available instead of skipping
  that day entirely.
- **`-WakeToRun`**: wakes the laptop from **sleep** to run — does **not**
  work from a full shutdown. The laptop needs to stay powered on (sleep is
  fine, shutdown isn't) for this to actually fire on schedule.
- **`-MultipleInstances IgnoreNew`**: if a run is still going when the next
  trigger fires (shouldn't normally happen at a once-daily cadence, but
  matters if you switch to a tighter interval), skip the new trigger
  rather than running two at once.

For a tighter interval instead of once-daily (e.g. every 30 min), replace
the trigger:

```powershell
$trigger = New-ScheduledTaskTrigger -Once -At (Get-Date) `
    -RepetitionInterval (New-TimeSpan -Minutes 30) `
    -RepetitionDuration (New-TimeSpan -Days 3650)
```

(`RepetitionDuration` needs an explicit large-but-bounded value like 10
years — `[TimeSpan]::MaxValue` overflows the Task Scheduler XML schema and
fails to register.)

**Verify it's registered correctly:**

```powershell
Get-ScheduledTask -TaskName "job-searcher-run" | Select-Object TaskName, State
Get-ScheduledTaskInfo -TaskName "job-searcher-run" | Select-Object NextRunTime
```

**Trigger it once manually to confirm it actually works** (don't just trust
that it's registered — the exact same command can behave differently under
Task Scheduler's execution context than run interactively; this project hit
an SSL certificate issue that only manifested when scheduled, see
`google-cloud-setup.md`'s troubleshooting section):

```powershell
Start-ScheduledTask -TaskName "job-searcher-run"
Start-Sleep -Seconds 15
Get-ScheduledTaskInfo -TaskName "job-searcher-run" | Select-Object LastRunTime, LastTaskResult
```

`LastTaskResult: 0` means success. Anything else — check `logs/run.log` for
the actual error.

**Changing the schedule later:**

```powershell
$trigger = New-ScheduledTaskTrigger -Daily -At "11:00AM"   # whatever new time
Set-ScheduledTask -TaskName "job-searcher-run" -Trigger $trigger
```

**Removing it:**

```powershell
Unregister-ScheduledTask -TaskName "job-searcher-run" -Confirm:$false
```

## You're done

From here, [`tuning-guide.md`](tuning-guide.md) covers adjusting
`filters.yaml`/`cv_library.yaml` and reviewing run history, and
`google-cloud-setup.md`'s troubleshooting section covers the specific
errors this project actually hit during setup (consent screen 500s,
unverified-app warnings, SSL certificate errors both generally and the
Task-Scheduler-specific variant).
