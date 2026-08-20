# job-searcher

Personal tool that ingests justjoin.it "data" category job-alert emails,
filters offers against `config/filters.yaml`, tailors a CV per matching
offer via LLM, and emails you the offer link + tailored CV — no auto-apply,
you submit every application yourself.

## Status

Feature-complete for its intended scope: ingestion, enrichment, filtering,
LLM CV tailoring, Drive upload, notifications, run logging/failure alerting
are all implemented, tested, and validated against live data. There's no
sending/auto-apply component by design (see the architecture plan's "Why no
auto-send" section) — `apply_type` (native/external) is still detected and
shown in the notification for your own reference, nothing acts on it.
See `docs/superpowers/plans/` for the architecture plan and implementation
plans, and `docs/tuning-guide.md` for how to adjust filters and the CV
bullet library.

## Running it

```bash
.venv/Scripts/python.exe run.py
```

One full pass: ingest new alert emails, enrich each new offer, filter,
tailor a CV for matches, email you. Meant to run on a schedule (e.g. Windows
Task Scheduler, every ~30 min) rather than continuously. Every run is
logged to `logs/run.log` and the `runs` table; a failed run sends a
best-effort failure alert email.

## Setup

```bash
python -m venv .venv
.venv/Scripts/pip install -e ".[dev]"
.venv/Scripts/python -m playwright install chromium
cp config/filters.example.yaml config/filters.yaml   # then edit with your real criteria
cp config/cv_library.example.yaml config/cv_library.yaml   # then fill with your real CV content
cp .env.example .env   # then fill in secrets
```

Google (Gmail + Drive) setup is its own guide: see
[`docs/google-cloud-setup.md`](docs/google-cloud-setup.md). For tuning
filters/CV content and reviewing run history, see
[`docs/tuning-guide.md`](docs/tuning-guide.md).

If `pip install` fails with an SSL certificate error (common behind antivirus
HTTPS interception, e.g. Avast), install with the interceptor's root cert trusted:

```bash
pip install --cert "<path-to-interceptor-root-cert>.pem" --trusted-host pypi.org --trusted-host files.pythonhosted.org -e ".[dev]"
```

## Tests

```bash
.venv/Scripts/pytest tests/ -v
```
