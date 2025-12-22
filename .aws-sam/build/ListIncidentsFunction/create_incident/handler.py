# Lambda handler for creating incidents

import uuid
from datetime import datetime, timezone

from botocore.exceptions import ClientError

from shared.utils import build_response, is_options_request, parse_json_body
from shared.dynamodb import put_incident_item
from shared.sns import publish_incident_created_message


def _validate_payload(payload: dict):
    required_fields = ["title", "description", "severity", "reported_by"]
    missing = [f for f in required_fields if f not in payload]
    if missing:
        return False, {
            "error": "ValidationError",
            "message": f"Missing fields: {', '.join(missing)}",
        }

    if not isinstance(payload.get("title"), str) or not payload["title"].strip():
        return False, {
            "error": "ValidationError",
            "message": "title must be a non-empty string",
        }

    if not isinstance(payload.get("description"), str) or not payload["description"].strip():
        return False, {
            "error": "ValidationError",
            "message": "description must be a non-empty string",
        }

    if not isinstance(payload.get("reported_by"), str) or not payload["reported_by"].strip():
        return False, {
            "error": "ValidationError",
            "message": "reported_by must be a non-empty string",
        }

    allowed_severity = {"low", "medium", "high", "critical"}
    if payload.get("severity") not in allowed_severity:
        return False, {
            "error": "ValidationError",
            "message": f"severity must be one of: {', '.join(sorted(allowed_severity))}",
        }

    if "tags" in payload and not isinstance(payload["tags"], list):
        return False, {
            "error": "ValidationError",
            "message": "tags must be a list of strings",
        }

    return True, None


def lambda_handler(event, context):
    if is_options_request(event):
        return build_response(204)

    if (event or {}).get("httpMethod") != "POST":
        return build_response(
            405,
            {
                "error": "MethodNotAllowed",
                "message": "Only POST is supported for this resource",
            },
        )

    try:
        payload = parse_json_body(event)
    except ValueError as exc:
        return build_response(400, {"error": "BadRequest", "message": str(exc)})

    is_valid, error_body = _validate_payload(payload)
    if not is_valid:
        return build_response(400, error_body)

    incident_id = str(uuid.uuid4())
    created_at = datetime.now(timezone.utc).isoformat()

    item = {
        "incident_id": incident_id,
        "title": payload["title"].strip(),
        "description": payload["description"].strip(),
        "severity": payload["severity"],
        "reported_by": payload["reported_by"].strip(),
        "created_at": created_at,
        "status": "open",
    }

    if "tags" in payload:
        item["tags"] = payload["tags"]

    try:
        put_incident_item(item)
    except ClientError as exc:
        return build_response(
            500,
            {
                "error": "InternalServerError",
                "message": "Failed to create incident (DynamoDB)",
                "detail": str(exc),
            },
        )

    notification_payload = {
        "incident_id": incident_id,
        "severity": item["severity"],
        "title": item["title"],
        "created_at": created_at,
        "status": item["status"],
    }

    try:
        publish_incident_created_message(notification_payload)
    except Exception as exc:  # SNS failures should not roll back the incident
        return build_response(
            202,
            {
                "incident_id": incident_id,
                "status": "created",
                "created_at": created_at,
                "warning": "Incident stored but notification failed",
                "sns_error": str(exc),
            },
        )

    return build_response(
        201,
        {
            "incident_id": incident_id,
            "status": "created",
            "created_at": created_at,
        },
    )
