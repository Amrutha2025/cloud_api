# Lambda handler for listing incidents

from botocore.exceptions import ClientError

from shared.utils import build_response, is_options_request
from shared.dynamodb import scan_incidents


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

    try:
        items = scan_incidents()
    except ClientError as exc:
        return build_response(
            500,
            {
                "error": "InternalServerError",
                "message": "Failed to list incidents",
                "detail": str(exc),
            },
        )

    return build_response(200, {"items": items})
