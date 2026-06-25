import json
from datetime import datetime
from uuid import UUID

import boto3

from app.config import Settings


class SqsService:
    def __init__(self, settings: Settings) -> None:
        self._queue_url = settings.sqs_queue_url
        self._client = boto3.client("sqs", region_name=settings.aws_region)

    def publish_case_created(
        self,
        *,
        case_id: UUID,
        received_at: datetime,
        attachment_count: int,
    ) -> None:
        if not self._queue_url:
            return
        message = {
            "event_type": "CASE_CREATED",
            "case_id": str(case_id),
            "received_at": received_at.isoformat(),
            "attachment_count": attachment_count,
        }
        self._client.send_message(
            QueueUrl=self._queue_url,
            MessageBody=json.dumps(message),
        )

    def check_connectivity(self) -> bool:
        if not self._queue_url:
            return True
        self._client.get_queue_attributes(
            QueueUrl=self._queue_url,
            AttributeNames=["QueueArn"],
        )
        return True
