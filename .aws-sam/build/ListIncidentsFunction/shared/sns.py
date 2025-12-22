# Shared SNS helper functions

import json
import os
from typing import Any, Dict

import boto3

_sns_client = boto3.client("sns")


def _get_env_var(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def publish_incident_created_message(payload: Dict[str, Any]) -> None:
    """Publish an incident-created notification to the configured SNS topic.

    The payload should be JSON-serializable and typically contains keys such
    as incident_id, severity, title, created_at, and status.
    """

    topic_arn = _get_env_var("INCIDENTS_TOPIC_ARN")

    _sns_client.publish(
        TopicArn=topic_arn,
        Message=json.dumps(payload),
        Subject=f"New incident: {payload.get('incident_id', 'unknown')} ({payload.get('severity', 'n/a')})",
        MessageAttributes={
            "severity": {
                "DataType": "String",
                "StringValue": str(payload.get("severity", "unknown")),
            }
        },
    )
