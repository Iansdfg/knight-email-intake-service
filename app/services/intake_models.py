from dataclasses import dataclass


@dataclass(frozen=True)
class IntakeAttachment:
    filename: str
    content: bytes
    mime_type: str


@dataclass(frozen=True)
class ParsedEmail:
    sender_email: str
    recipients: list[str]
    subject: str
    email_body: str
    attachments: list[IntakeAttachment]
    message_id: str | None = None
