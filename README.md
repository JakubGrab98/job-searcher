# job-searcher

Personal tool that ingests justjoin.it "data" category job-alert emails, filters
offers against `config/filters.yaml`, tailors a CV per matching offer, and applies
to offers with justjoin.it's native quick-apply.

## Status

Foundations only: SQLite persistence layer and the filter engine are implemented
and tested. Ingestion (Gmail), enrichment (Playwright), CV tailoring (LLM), and
sending are not yet built — see `docs/superpowers/plans/` for the architecture
plan and follow-on implementation plans.

## Setup

```bash
python -m venv .venv
.venv/Scripts/pip install -e ".[dev]"
cp config/filters.example.yaml config/filters.yaml   # then edit with your real criteria
cp config/cv_library.example.yaml config/cv_library.yaml   # then fill with your real CV content
cp .env.example .env   # then fill in secrets once later plans add Gmail/LLM integration
```

If `pip install` fails with an SSL certificate error (common behind antivirus
HTTPS interception, e.g. Avast), install with the interceptor's root cert trusted:

```bash
pip install --cert "<path-to-interceptor-root-cert>.pem" --trusted-host pypi.org --trusted-host files.pythonhosted.org -e ".[dev]"
```

## Tests

```bash
.venv/Scripts/pytest tests/ -v
```
