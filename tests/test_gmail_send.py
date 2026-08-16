import base64
import email

from jobsearcher.gmail.send import send_email


class _FakeExecutable:
    def __init__(self, response):
        self._response = response

    def execute(self):
        return self._response


class _FakeMessages:
    def __init__(self):
        self.sent = []

    def send(self, userId, body):
        self.sent.append(body)
        return _FakeExecutable({"id": "sent-msg-1"})


class _FakeUsers:
    def __init__(self, messages):
        self._messages = messages

    def messages(self):
        return self._messages


class _FakeGmailService:
    def __init__(self):
        self.messages = _FakeMessages()

    def users(self):
        return _FakeUsers(self.messages)


def test_send_email_returns_sent_message_id():
    service = _FakeGmailService()
    message_id = send_email(service, "me@example.com", "Subject", "Body text")
    assert message_id == "sent-msg-1"


def test_send_email_encodes_subject_and_body_correctly():
    service = _FakeGmailService()
    send_email(service, "me@example.com", "Test Subject", "Test body content")

    raw = service.messages.sent[0]["raw"]
    parsed = email.message_from_bytes(base64.urlsafe_b64decode(raw))
    payload = parsed.get_payload(decode=True).decode(parsed.get_content_charset() or "utf-8")

    assert parsed["subject"] == "Test Subject"
    assert parsed["to"] == "me@example.com"
    assert payload.strip() == "Test body content"


def test_send_email_handles_non_ascii_body():
    service = _FakeGmailService()
    send_email(service, "me@example.com", "Zaproszenie", "Cześć, oferta pracy: Gdańsk")

    raw = service.messages.sent[0]["raw"]
    mime_bytes = base64.urlsafe_b64decode(raw)
    parsed = email.message_from_bytes(mime_bytes)
    payload = parsed.get_payload(decode=True).decode(parsed.get_content_charset() or "utf-8")
    assert "Gdańsk" in payload
