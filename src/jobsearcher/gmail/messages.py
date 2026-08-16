import base64


def get_header(headers: list[dict], name: str) -> str | None:
    for h in headers:
        if h["name"].lower() == name.lower():
            return h["value"]
    return None


def extract_bodies(payload: dict) -> tuple[str | None, str | None]:
    """Returns (text_plain, text_html) bodies, searching nested MIME parts."""
    text_plain = None
    text_html = None

    def walk(part):
        nonlocal text_plain, text_html
        mime_type = part.get("mimeType", "")
        body_data = part.get("body", {}).get("data")
        if body_data:
            decoded = base64.urlsafe_b64decode(body_data).decode("utf-8", errors="replace")
            if mime_type == "text/plain" and text_plain is None:
                text_plain = decoded
            elif mime_type == "text/html" and text_html is None:
                text_html = decoded
        for sub in part.get("parts", []):
            walk(sub)

    walk(payload)
    return text_plain, text_html
