from dataclasses import dataclass

from bs4 import BeautifulSoup


@dataclass
class ParsedOfferCard:
    url: str
    company: str
    city: str
    title: str
    salary_text: str
    work_mode: str
    contract_type: str
    seniority: str


def _clean_offer_url(href: str) -> str:
    # justjoin.it's utm-tagged hrefs sometimes contain a second, malformed
    # "?" inside the query string itself (e.g. "...?utm_campaign=x?utm_source=y").
    # Splitting on the first "?" strips all of it, malformed or not.
    return href.split("?", 1)[0]


def parse_category(html: str) -> str | None:
    soup = BeautifulSoup(html, "html.parser")
    for b_tag in soup.find_all("b"):
        parent_text = b_tag.parent.get_text(" ", strip=True) if b_tag.parent else ""
        if "Your preferences" in parent_text:
            return b_tag.get_text(strip=True)
    return None


def parse_offer_cards(html: str) -> list[ParsedOfferCard]:
    soup = BeautifulSoup(html, "html.parser")
    cards: list[ParsedOfferCard] = []
    seen_urls: set[str] = set()

    for link in soup.find_all("a", href=True):
        href = link["href"]
        if "justjoin.it/job-offer/" not in href:
            continue

        url = _clean_offer_url(href)
        if url in seen_urls:
            continue
        seen_urls.add(url)

        company_tag = link.find("p", class_="company-name")
        city_tag = link.find("p", class_="company-city")
        title_tag = link.find("p", class_="offer-title")
        salary_tag = link.find("p", class_="salary")
        detail_tags = link.find_all("td", class_="offer-details")

        salary_text = " ".join(salary_tag.get_text(" ", strip=True).split()) if salary_tag else ""

        cards.append(
            ParsedOfferCard(
                url=url,
                company=company_tag.get_text(strip=True) if company_tag else "",
                city=city_tag.get_text(strip=True) if city_tag else "",
                title=title_tag.get_text(strip=True) if title_tag else "",
                salary_text=salary_text,
                work_mode=detail_tags[0].get_text(strip=True) if len(detail_tags) > 0 else "",
                contract_type=detail_tags[1].get_text(strip=True) if len(detail_tags) > 1 else "",
                seniority=detail_tags[2].get_text(strip=True) if len(detail_tags) > 2 else "",
            )
        )

    return cards
