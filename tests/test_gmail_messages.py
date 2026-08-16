import base64

from jobsearcher.gmail.messages import extract_bodies, get_header


def _b64(text: str) -> str:
    return base64.urlsafe_b64encode(text.encode("utf-8")).decode("ascii")


def test_get_header_is_case_insensitive():
    headers = [{"name": "Subject", "value": "New jobs for you: Analytics"}]
    assert get_header(headers, "subject") == "New jobs for you: Analytics"


def test_get_header_returns_none_when_missing():
    assert get_header([{"name": "Subject", "value": "x"}], "From") is None


def test_extract_bodies_single_part_html():
    payload = {"mimeType": "text/html", "body": {"data": _b64("<p>hello</p>")}}
    text_plain, text_html = extract_bodies(payload)
    assert text_plain is None
    assert text_html == "<p>hello</p>"


def test_extract_bodies_multipart_alternative():
    payload = {
        "mimeType": "multipart/alternative",
        "body": {},
        "parts": [
            {"mimeType": "text/plain", "body": {"data": _b64("plain body")}},
            {"mimeType": "text/html", "body": {"data": _b64("<p>html body</p>")}},
        ],
    }
    text_plain, text_html = extract_bodies(payload)
    assert text_plain == "plain body"
    assert text_html == "<p>html body</p>"


def test_extract_bodies_returns_none_when_no_matching_parts():
    payload = {"mimeType": "image/png", "body": {"data": _b64("binary")}}
    text_plain, text_html = extract_bodies(payload)
    assert text_plain is None
    assert text_html is None
