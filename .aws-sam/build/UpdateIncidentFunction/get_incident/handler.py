# Lambda handler for retrieving a single incident

from botocore.exceptions import ClientError

from shared.utils import build_response, is_options_request
from shared.dynamodb import get_incident_item


def lambda_handler(event, context):
    if is_options_request(event):
        return build_response(204)

    if (event or {}).get("httpMethod") != "GET":
        return build_response(
            405,
            {
                "error": "MethodNotAllowed",
                "message": "Only GET is supported for this resource",
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
        item = get_incident_item(incident_id)
    except ClientError as exc:
        return build_response(
            500,
            {
                "error": "InternalServerError",
                "message": "Failed to fetch incident",
                "detail": str(exc),
            },
        )

    if not item:
        return build_response(
            404,
            {
                "error": "NotFound",
                "message": f"Incident '{incident_id}' not found",
            },
        )

    return build_response(200, item)
