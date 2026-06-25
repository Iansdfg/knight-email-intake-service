import json
import logging
import time
from collections.abc import Mapping
from typing import Any


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "level": record.levelname,
            "message": record.getMessage(),
            "event": getattr(record, "event", None),
            "case_id": getattr(record, "case_id", None),
            "request_id": getattr(record, "request_id", None),
            "duration": getattr(record, "duration", None),
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


def configure_logging(level: str) -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    logging.basicConfig(level=level.upper(), handlers=[handler], force=True)


def log_event(
    logger: logging.Logger,
    *,
    event: str,
    case_id: str | None = None,
    request_id: str | None = None,
    duration: float | None = None,
    level: int = logging.INFO,
    message: str | None = None,
    extra: Mapping[str, Any] | None = None,
) -> None:
    log_extra = {
        "event": event,
        "case_id": case_id,
        "request_id": request_id,
        "duration": duration,
    }
    if extra:
        log_extra.update(extra)
    logger.log(level, message or event, extra=log_extra)


def monotonic_duration(started_at: float) -> float:
    return round(time.monotonic() - started_at, 6)
