# Lambda handler for updating incidents


from datetime import datetime, timezone

from botocore.exceptions import ClientError

from shared.utils import build_response, is_options_request, parse_json_body
from shared.dynamodb import update_incident_status


def _validate_payload(payload: dict):
    if "status" not in payload:
        return False, {"error": "ValidationError", "message": "status is required"}

    allowed_status = {"open", "in_progress", "resolved", "closed"}
    status = payload.get("status")
    if status not in allowed_status:
        return False, {
            "error": "ValidationError",
            "message": f"status must be one of: {', '.join(sorted(allowed_status))}",
        }

    return True, None


def lambda_handler(event, context):
    if is_options_request(event):
        return build_response(204)

    if (event or {}).get("httpMethod") not in {"PATCH", "PUT"}:
        return build_response(
            405,
            {
                "error": "MethodNotAllowed",
                "message": "Only PATCH or PUT is supported for this resource",
            },
        )

    path_params = (event or {}).get("pathParameters") or {}
    incident_id = path_params.get("id")
    if not incident_id:
        return build_response(
            400,
            {"error": "BadRequest", "message": "Path parameter 'id' is required"},
        )

    try:
        payload = parse_json_body(event)
    except ValueError as exc:
        return build_response(400, {"error": "BadRequest", "message": str(exc)})

    is_valid, error_body = _validate_payload(payload)
    if not is_valid:
        return build_response(400, error_body)

    new_status = payload["status"]
    updated_at = datetime.now(timezone.utc).isoformat()

    try:
        updated_item = update_incident_status(incident_id, new_status, updated_at)
    except ClientError as exc:
        if exc.response.get("Error", {}).get("Code") == "ConditionalCheckFailedException":
            return build_response(
                404,
                {
                    "error": "NotFound",
                    "message": f"Incident '{incident_id}' not found",
                },
            )

        return build_response(
            500,
            {
                "error": "InternalServerError",
                "message": "Failed to update incident status",
                "detail": str(exc),
            },
        )

    return build_response(200, updated_item)
