import base64
import os

import pytest

from jobsearcher.db.repository import get_offer_by_url, list_offers_by_status
from jobsearcher.ingest.gmail_ingest import fetch_and_store_new_offers

FIXTURE_PATH = os.path.join(os.path.dirname(__file__), "fixtures", "sample_alert_email.html")


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
        self.modified_ids.append((id, body))
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


@pytest.fixture
def sample_html():
    with open(FIXTURE_PATH, encoding="utf-8") as f:
        return f.read()


def _make_service(html: str, has_messages: bool = True):
    list_response = {"messages": [{"id": "msg-1"}]} if has_messages else {"messages": []}
    get_responses = {
        "msg-1": {
            "payload": {
                "headers": [{"name": "Subject", "value": "New jobs for you: Analytics"}],
                "mimeType": "text/html",
                "body": {"data": _b64(html)},
            }
        }
    }
    messages = _FakeMessages(list_response, get_responses)
    return _FakeGmailService(messages), messages


def test_fetch_and_store_stores_every_offer_in_the_digest(conn, sample_html):
    service, _ = _make_service(sample_html)
    offer_ids = fetch_and_store_new_offers(service, conn)
    assert len(offer_ids) == 10
    assert len(list_offers_by_status(conn, "new")) == 10


def test_fetch_and_store_marks_email_read_after_storing(conn, sample_html):
    service, messages = _make_service(sample_html)
    fetch_and_store_new_offers(service, conn)
    assert messages.modified_ids == [("msg-1", {"removeLabelIds": ["UNREAD"]})]


def test_fetch_and_store_populates_offer_fields_from_email(conn, sample_html):
    service, _ = _make_service(sample_html)
    fetch_and_store_new_offers(service, conn)
    offer = get_offer_by_url(
        conn,
        "https://justjoin.it/job-offer/"
        "reply-polska-sp-z-o-o--senior-business-analyst-katowice-analytics-229f90b9",
    )
    assert offer is not None
    assert offer.title == "Senior Business Analyst"
    assert offer.company == "Reply Polska Sp. z o. o."
    assert offer.category == "Analytics"
    assert offer.location == "Katowice"
    assert offer.gmail_message_id == "msg-1"
    assert offer.status == "new"


def test_fetch_and_store_is_idempotent_across_repeated_runs(conn, sample_html):
    service, _ = _make_service(sample_html)
    fetch_and_store_new_offers(service, conn)
    # Second run: same unread message returned again (e.g. modify call failed
    # upstream last time) — must not create duplicate offers.
    fetch_and_store_new_offers(service, conn)
    assert len(list_offers_by_status(conn, "new")) == 10


def test_fetch_and_store_returns_empty_list_when_no_unread_messages(conn):
    service, _ = _make_service("", has_messages=False)
    offer_ids = fetch_and_store_new_offers(service, conn)
    assert offer_ids == []
