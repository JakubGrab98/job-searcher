import os

import pytest

from jobsearcher.ingest.email_parser import parse_category, parse_offer_cards

FIXTURE_PATH = os.path.join(os.path.dirname(__file__), "fixtures", "sample_alert_email.html")


@pytest.fixture
def sample_html():
    with open(FIXTURE_PATH, encoding="utf-8") as f:
        return f.read()


def test_parse_category_reads_preferences_banner(sample_html):
    assert parse_category(sample_html) == "Analytics"


def test_parse_offer_cards_returns_all_offers_in_digest(sample_html):
    cards = parse_offer_cards(sample_html)
    assert len(cards) == 10


def test_parse_offer_cards_extracts_first_card_fields(sample_html):
    cards = parse_offer_cards(sample_html)
    first = cards[0]
    assert first.url == (
        "https://justjoin.it/job-offer/"
        "reply-polska-sp-z-o-o--senior-business-analyst-katowice-analytics-229f90b9"
    )
    assert first.company == "Reply Polska Sp. z o. o."
    assert first.city == "Katowice"
    assert first.title == "Senior Business Analyst"
    assert first.salary_text == "14000 - 20000 PLN"
    assert first.work_mode == "Hybrid"
    assert first.contract_type == "Permanent"
    assert first.seniority == "Senior"


def test_parse_offer_cards_urls_have_no_tracking_params(sample_html):
    cards = parse_offer_cards(sample_html)
    assert all("?" not in c.url and "utm_" not in c.url for c in cards)


def test_parse_offer_cards_urls_are_unique(sample_html):
    cards = parse_offer_cards(sample_html)
    urls = [c.url for c in cards]
    assert len(urls) == len(set(urls))


def test_parse_offer_cards_handles_gmail_forwarding_class_prefix():
    # Gmail forwarding prefixes every class with a message-scoped string
    # (e.g. "company-name" -> "m_-4816130689228390770company-name") to
    # avoid style collisions with the surrounding UI — confirmed against a
    # real forwarded alert email. Fields must still resolve correctly.
    html = """
    <html><body>
    Your preferences: <b>Data</b>
    <a href="https://justjoin.it/job-offer/acme-data-engineer">
      <p class="m_-123company-name">Acme</p>
      <p class="m_-123company-city">Warszawa</p>
      <p class="m_-123offer-title">Data Engineer</p>
      <p class="m_-123salary">Undisclosed salary</p>
      <td class="m_-123offer-details">Remote</td>
      <td class="m_-123offer-details">B2B</td>
      <td class="m_-123offer-details">Senior</td>
    </a>
    </body></html>
    """
    cards = parse_offer_cards(html)
    assert len(cards) == 1
    assert cards[0].company == "Acme"
    assert cards[0].city == "Warszawa"
    assert cards[0].title == "Data Engineer"
    assert cards[0].work_mode == "Remote"
    assert cards[0].contract_type == "B2B"
    assert cards[0].seniority == "Senior"
