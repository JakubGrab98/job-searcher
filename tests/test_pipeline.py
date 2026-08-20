import base64

import pytest

from jobsearcher.db.repository import get_offer
from jobsearcher.filter.config import FilterConfig
from jobsearcher.pipeline import run_once


def _b64(text: str) -> str:
    return base64.urlsafe_b64encode(text.encode("utf-8")).decode("ascii")


class _FakeExecutable:
    def __init__(self, response):
        self._response = response

    def execute(self):
        return self._response


class _FakeMessages:
    def __init__(self, list_response, get_responses):
        self._list_response = list_response
        self._get_responses = get_responses
        self.modified_ids = []

    def list(self, userId, q):
        return _FakeExecutable(self._list_response)

    def get(self, userId, id, format):
        return _FakeExecutable(self._get_responses[id])

    def modify(self, userId, id, body):
        self.modified_ids.append(id)
        return _FakeExecutable({})


class _FakeUsers:
    def __init__(self, messages):
        self._messages = messages

    def messages(self):
        return self._messages


class _FakeGmailService:
    def __init__(self, messages):
        self._users = _FakeUsers(messages)

    def users(self):
        return self._users


DIGEST_HTML = """
<html><body>
Your preferences: <b>Data</b>
<a href="https://justjoin.it/job-offer/acme-data-engineer?utm_source=mail">
  <p class="company-name">Acme</p>
  <p class="company-city">Warszawa</p>
  <p class="offer-title">Data Engineer</p>
  <p class="salary">Undisclosed salary</p>
  <td class="offer-details">Remote</td>
  <td class="offer-details">B2B</td>
  <td class="offer-details">Senior</td>
</a>
</body></html>
"""


def _make_gmail_service():
    list_response = {"messages": [{"id": "msg-1"}]}
    get_responses = {
        "msg-1": {
            "payload": {
                "headers": [{"name": "Subject", "value": "New jobs for you: Data"}],
                "mimeType": "text/html",
                "body": {"data": _b64(DIGEST_HTML)},
            }
        }
    }
    messages = _FakeMessages(list_response, get_responses)
    return _FakeGmailService(messages)


def _enrich_matching(conn, offer_id, url):
    from jobsearcher.db.repository import update_offer_enrichment

    update_offer_enrichment(
        conn, offer_id, seniority="Senior", employment_type="B2B", salary_min=180, salary_max=220,
        currency="PLN", remote_type="Remote", tech_stack=["python"], apply_type="native",
    )


def _enrich_non_matching(conn, offer_id, url):
    from jobsearcher.db.repository import update_offer_enrichment

    update_offer_enrichment(
        conn, offer_id, seniority="Junior", employment_type="UoP", salary_min=50, salary_max=60,
        currency="PLN", remote_type="Office", tech_stack=["java"], apply_type="native",
    )


def _filter_config():
    return FilterConfig(role_keywords=["data engineer"], contract_types=["b2b"])


def _fake_tailor(conn, offer):
    return "fake-cv-version"


def _failing_tailor(conn, offer):
    raise RuntimeError("LLM call failed")


@pytest.fixture
def sent_emails():
    return []


def test_run_once_notifies_for_matching_offer(conn, sent_emails):
    service = _make_gmail_service()

    def fake_send(offer, match_result, cv_version):
        sent_emails.append((offer.title, match_result.matched_criteria, cv_version))

    stats = run_once(conn, service, _enrich_matching, _filter_config(), _fake_tailor, fake_send)

    assert stats == {
        "ingested": 1, "enriched": 1, "matched": 1, "filtered_out": 0,
        "tailored": 1, "tailoring_failed": 0, "notified": 1, "enrichment_failed": 0,
    }
    assert len(sent_emails) == 1
    assert sent_emails[0][2] == "fake-cv-version"
    offer = get_offer(conn, 1)
    assert offer.status == "notified"


def test_run_once_does_not_notify_for_non_matching_offer(conn, sent_emails):
    service = _make_gmail_service()

    def fake_send(offer, match_result, cv_version):
        sent_emails.append(offer.title)

    stats = run_once(conn, service, _enrich_non_matching, _filter_config(), _fake_tailor, fake_send)

    assert stats["matched"] == 0
    assert stats["filtered_out"] == 1
    assert stats["notified"] == 0
    assert sent_emails == []
    offer = get_offer(conn, 1)
    assert offer.status == "filtered_out"
    assert offer.filter_reasons != []


def test_run_once_marks_offer_failed_when_enrichment_raises(conn):
    service = _make_gmail_service()

    def failing_enrich(conn, offer_id, url):
        raise RuntimeError("Playwright navigation timeout")

    stats = run_once(conn, service, failing_enrich, _filter_config(), _fake_tailor, lambda o, r, c: None)

    assert stats["enrichment_failed"] == 1
    assert stats["enriched"] == 0
    offer = get_offer(conn, 1)
    assert offer.status == "failed"


def test_run_once_still_notifies_when_tailoring_fails(conn, sent_emails):
    service = _make_gmail_service()

    def fake_send(offer, match_result, cv_version):
        sent_emails.append(cv_version)

    stats = run_once(conn, service, _enrich_matching, _filter_config(), _failing_tailor, fake_send)

    assert stats["tailoring_failed"] == 1
    assert stats["tailored"] == 0
    assert stats["notified"] == 1  # still notified about the match despite the tailoring failure
    assert sent_emails == [None]
    offer = get_offer(conn, 1)
    assert offer.status == "notified"


def test_run_once_is_a_noop_when_no_new_offers(conn):
    service = _FakeGmailService(_FakeMessages({"messages": []}, {}))
    stats = run_once(conn, service, _enrich_matching, _filter_config(), _fake_tailor, lambda o, r, c: None)
    assert stats == {
        "ingested": 0, "enriched": 0, "matched": 0, "filtered_out": 0,
        "tailored": 0, "tailoring_failed": 0, "notified": 0, "enrichment_failed": 0,
    }
