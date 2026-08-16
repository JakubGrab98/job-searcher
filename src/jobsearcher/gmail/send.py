import base64
from email.mime.text import MIMEText


def send_email(service, to: str, subject: str, body: str) -> str:
    message = MIMEText(body, "plain", "utf-8")
    message["to"] = to
    message["subject"] = subject
    raw = base64.urlsafe_b64encode(message.as_bytes()).decode("ascii")

    sent = service.users().messages().send(userId="me", body={"raw": raw}).execute()
    return sent["id"]
