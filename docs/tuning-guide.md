# Tuning Guide

How to adjust what the tool matches on, what your CV emphasizes, and how to
tell whether it's actually working.

## Tuning `config/filters.yaml`

Every enriched offer runs through `jobsearcher.filter.engine.evaluate()`
against this file. Fields:

- `role_keywords` — offer title or tech stack must contain **at least one**
  (case-insensitive substring match). This is the primary relevance gate; an
  empty list means no title/tech filtering at all.
- `contract_types` — matched by **substring**, not exact equality (e.g.
  `"b2b"` matches an extracted value of `"B2B, Permanent"`). Real extracted
  values are free text from the offer page, not a clean enum.
- `seniority` — matched **case-insensitively** against the extracted value
  (e.g. `"senior"` matches `"Senior"`).
- `salary_floor` / `salary_period` / `currency` — only enforced when the
  offer's currency matches `currency` exactly; a currency mismatch skips the
  salary check rather than rejecting the offer (can't compare PLN to EUR).
- `locations` / `remote_ok` — an offer passes if its location matches one of
  `locations`, OR if `remote_ok` is true and the offer is remote.
- `tech_must_have` — **all** must appear in the offer's extracted tech stack.
- `tech_nice_to_have` — informational only, shown in `matched_criteria`, never
  filters anything out.
- `excluded_companies` — exact company name match, always rejects.

Any list left empty means "no restriction" for that criterion — an empty
`filters.yaml` (except `role_keywords`) matches everything.

**Why an offer got filtered out**: every rejected offer's `filter_reasons`
column explains exactly which check(s) failed. Query it directly:

```bash
.venv/Scripts/python.exe -c "
from jobsearcher.db.database import connect
conn = connect('data/jobsearcher.db')
rows = conn.execute(\"SELECT title, company, filter_reasons FROM offers WHERE status='filtered_out' ORDER BY id DESC LIMIT 20\").fetchall()
for r in rows:
    print(r['title'], '|', r['company'], '|', r['filter_reasons'])
"
```

If you're seeing good offers filtered out for reasons that don't actually
matter to you, loosen the relevant `filters.yaml` field. If you're seeing
irrelevant offers matching, tighten `role_keywords` or add `tech_must_have`.

## Tuning `config/cv_library.yaml`

This is the only source of truth for what the LLM tailoring step can put on
a generated CV — it never invents content, only selects/lightly rephrases
from what's here. To improve tailoring:

- **Add bullets, don't just edit existing ones**, when you want new angles
  covered — more truthful bullets tagged for a theme gives the model more to
  choose from for offers on that theme.
- **Tags matter for the deterministic prefilter** (`tailor/bullet_prefilter.py`,
  not used by default — see below) but not for the LLM path currently wired
  in, which sees the full library every time (that's what's cached). Still
  worth keeping tags accurate/descriptive for your own reference and for if
  you switch strategies later.
- **`variant_of`**: mark an alternate phrasing of the *same underlying fact*
  as a variant of the bullet immediately before it in that role's list (must
  be adjacent — `variant_of` isn't a real cross-reference id, it's positional
  in how this file is authored). The tailoring step picks whichever phrasing
  fits the offer better; it does not add both.
- **Two roles at the same company** (a promotion, a return stint) are fully
  supported — each role gets its own stable id independent of company name
  (`cv_library.get_role_by_id()`), so they render as distinct entries.
- Real cost per tailoring call is small (Haiku + prompt caching — see
  `docs/google-cloud-setup.md`'s sibling architecture notes in the plan doc
  for the caching design), but it's still a real API call per match — an
  offer only gets tailored once (`get_cv_version_by_offer()` skips repeats),
  so editing the library doesn't retroactively re-tailor past matches.

**Reviewing what actually got tailored**: `cv_versions.bullet_ids_used` records
exactly which bullets were selected for a given offer — cross-reference
against the library to see if the selection made sense.

## Reviewing run history

Every `run.py` execution is logged twice — a plain-text log
(`logs/run.log`, rotates at 2MB × 5 files) and a queryable `runs` table
(`started_at`, `finished_at`, `status`, `stats` JSON, `error_message`):

```bash
.venv/Scripts/python.exe -c "
from jobsearcher.db.database import connect
from jobsearcher.db.repository import list_recent_runs
conn = connect('data/jobsearcher.db')
for r in list_recent_runs(conn, limit=10):
    print(r.started_at, r.status, r.stats or r.error_message)
"
```

A failed run also sends you an email (`build_failure_alert()` in
`notify/notification.py`) — best-effort; if Gmail auth itself is what broke,
that alert can't be sent, and only the log/DB will show it. If runs start
failing or silently returning `ingested: 0` when you know new alerts exist,
the two most likely causes are:

- **justjoin.it changed page markup** — breaks `enrich/offer_details.py`'s
  section-header text parsing or `enrich/apply_type.py`'s button/dialog
  detection. Re-run `scripts/explore_offer_fields.py` against a real live
  offer to see what changed.
- **justjoin.it changed the alert email template** — breaks
  `ingest/email_parser.py`'s class-based field extraction. Re-run
  `scripts/fetch_sample_alert.py --query "from:justjoin.it"` to pull a fresh
  sample and compare against `tests/fixtures/sample_alert_email.html`.
