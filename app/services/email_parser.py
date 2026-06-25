from email import policy
from email.message import EmailMessage
from email.parser import BytesParser
from email.utils import getaddresses, parseaddr

from app.services.intake_models import IntakeAttachment, ParsedEmail
from app.utils.filenames import safe_attachment_filename


class EmailParser:
    def parse_bytes(self, raw_message: bytes) -> ParsedEmail:
        message = BytesParser(policy=policy.default).parsebytes(raw_message)
        return self.parse_message(message)

    def parse_message(self, message: EmailMessage) -> ParsedEmail:
        sender = parseaddr(message.get("From", ""))[1]
        recipients = [
            address
            for _, address in getaddresses(message.get_all("To", []) + message.get_all("Cc", []))
            if address
        ]
        subject = message.get("Subject", "")
        message_id = message.get("Message-ID")
        body = self._body_from_message(message)
        attachments = self._attachments_from_message(message)
        return ParsedEmail(
            sender_email=sender,
            recipients=recipients,
            subject=subject,
            email_body=body,
            attachments=attachments,
            message_id=message_id,
        )

    def _body_from_message(self, message: EmailMessage) -> str:
        if message.is_multipart():
            plain_body = message.get_body(preferencelist=("plain",))
            html_body = message.get_body(preferencelist=("html",))
            selected = plain_body or html_body
            if selected is not None:
                return selected.get_content()
            return ""
        content = message.get_content()
        return content if isinstance(content, str) else ""

    def _attachments_from_message(self, message: EmailMessage) -> list[IntakeAttachment]:
        attachments: list[IntakeAttachment] = []
        for part in message.iter_attachments():
            filename = safe_attachment_filename(part.get_filename())
            content = part.get_payload(decode=True) or b""
            attachments.append(
                IntakeAttachment(
                    filename=filename,
                    content=content,
                    mime_type=part.get_content_type() or "application/octet-stream",
                )
            )
        return attachments
