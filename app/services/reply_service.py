import smtplib
from email.message import EmailMessage
from uuid import UUID

from app.config import Settings


class ReplyService:
    def __init__(self, settings: Settings) -> None:
        self._host = settings.smtp_host
        self._port = settings.smtp_port
        self._reply_from = settings.smtp_reply_from
        self._enabled = settings.smtp_reply_enabled

    def send_acknowledgement(self, *, recipient: str, case_id: UUID) -> None:
        if not self._enabled or not recipient:
            return

        message = EmailMessage()
        message["From"] = self._reply_from
        message["To"] = recipient
        message["Subject"] = "Knight Submission Received"
        message.set_content(
            "\n".join(
                [
                    "Thank you for your submission.",
                    "",
                    "Your Case ID is:",
                    "",
                    str(case_id),
                    "",
                    "Our underwriting team has received your submission and processing has begun.",
                    "",
                    "Please reference this Case ID in future communications.",
                ]
            )
        )

        with smtplib.SMTP(self._host, self._port, timeout=10) as smtp:
            smtp.send_message(message)
