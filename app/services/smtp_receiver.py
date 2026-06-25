import asyncio
import logging
from uuid import uuid4

from aiosmtpd.controller import Controller

from app.config import Settings, get_settings
from app.database import SessionLocal
from app.services.email_parser import EmailParser
from app.services.intake_service import IntakeService
from app.utils.logging import log_event

logger = logging.getLogger(__name__)


class SmtpIntakeHandler:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._parser = EmailParser()

    async def handle_DATA(self, server, session, envelope) -> str:  # noqa: ANN001
        request_id = str(uuid4())
        parsed_email = self._parser.parse_bytes(envelope.content)
        db = SessionLocal()
        try:
            service = IntakeService(db, self._settings)
            response = service.ingest(parsed_email, request_id=request_id)
            log_event(
                logger,
                event="smtp_email_received",
                case_id=str(response.case_id),
                request_id=request_id,
            )
        finally:
            db.close()
        return "250 Message accepted for delivery"


def run_smtp_receiver(settings: Settings | None = None) -> None:
    active_settings = settings or get_settings()
    controller = Controller(
        SmtpIntakeHandler(active_settings),
        hostname=active_settings.smtp_host,
        port=active_settings.smtp_port,
    )
    controller.start()
    try:
        asyncio.get_event_loop().run_forever()
    finally:
        controller.stop()
