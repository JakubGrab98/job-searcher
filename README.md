# job-searcher

Personal tool that ingests justjoin.it "data" category job-alert emails, filters
offers against `config/filters.yaml`, tailors a CV per matching offer, and applies
to offers with justjoin.it's native quick-apply.

## Status

Ingestion (Gmail), enrichment (Playwright), filtering, notifications, and CV
rendering/Drive upload are implemented, tested, and validated against live
data. Still needed: the actual LLM bullet-selection call (needs
`ANTHROPIC_API_KEY`) and the sending/auto-apply component. See
`docs/superpowers/plans/` for the architecture plan and implementation plans.

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
[`docs/google-cloud-setup.md`](docs/google-cloud-setup.md).

If `pip install` fails with an SSL certificate error (common behind antivirus
HTTPS interception, e.g. Avast), install with the interceptor's root cert trusted:

```bash
pip install --cert "<path-to-interceptor-root-cert>.pem" --trusted-host pypi.org --trusted-host files.pythonhosted.org -e ".[dev]"
```

## Tests

```bash
.venv/Scripts/pytest tests/ -v
```
