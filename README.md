# job-searcher

Personal tool that watches justjoin.it for relevant contracts, tailors a CV
per matching offer via LLM, and emails you the offer link + tailored CV —
no auto-apply, you submit every application yourself.

Pipeline: ingest justjoin.it job-alert emails (Gmail API) → enrich each
offer via a headless browser → filter against `config/filters.yaml` →
tailor a CV from `config/cv_library.yaml` (Claude Haiku, never invents
content) → render to PDF → upload to Google Drive → email you the match.

## Status

Feature-complete for its intended scope and running on a schedule. There's
no sending/auto-apply component by design (see the architecture plan's
"Why no auto-send" section) — `apply_type` (native/external) is detected
and shown in the notification for your own reference, nothing acts on it.

## Docs

| Doc | For |
|---|---|
| [`docs/setup-guide.md`](docs/setup-guide.md) | Setting this up from scratch — environment, Google/Anthropic credentials, config, and scheduling |
| [`docs/google-cloud-setup.md`](docs/google-cloud-setup.md) | The Google Cloud / Gmail / Drive OAuth portion specifically, plus troubleshooting (consent screen errors, SSL certificate issues) |
| [`docs/tuning-guide.md`](docs/tuning-guide.md) | Adjusting `filters.yaml`/`cv_library.yaml` once it's running, reviewing why an offer was filtered, reviewing run history |
| `docs/superpowers/plans/` | Architecture plan and implementation history — the "why" behind the decisions above |

## Running it

```bash
.venv/Scripts/python.exe run.py
```

One full pass: ingest new alert emails, enrich each new offer, filter,
tailor a CV for matches, email you. Meant to run on a schedule (see
`docs/setup-guide.md` for Windows Task Scheduler setup) rather than
continuously or purely on demand — check how often your justjoin.it alert
digest actually arrives before picking an interval. Every run is logged to
`logs/run.log` and the `runs` table; a failed run sends a best-effort
failure alert email.

## Tests

```bash
.venv/Scripts/pytest tests/ -v
```
