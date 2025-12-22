# Shared utility functions

import json
from typing import Any, Dict, Optional


def build_response(status_code: int, body: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Build an API Gateway REST proxy integration response with CORS headers."""
    if body is None:
        body = {}

    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "OPTIONS,GET,POST,PATCH,PUT,DELETE",
            "Access-Control-Allow-Headers": "Content-Type,Authorization",
        },
        "body": json.dumps(body),
        "isBase64Encoded": False,
    }


def parse_json_body(event: Dict[str, Any]) -> Dict[str, Any]:
    """Parse the JSON body from an API Gateway REST proxy event.

    Raises:
        ValueError: If the body is missing or not valid JSON.
    """

    raw_body = event.get("body")
    if raw_body is None:
        raise ValueError("Request body is required")

    if event.get("isBase64Encoded"):
        import base64

        raw_body = base64.b64decode(raw_body).decode("utf-8")

    try:
        return json.loads(raw_body)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise ValueError("Request body must be valid JSON") from exc


def is_options_request(event: Dict[str, Any]) -> bool:
    """Return True if this is an HTTP OPTIONS request (for CORS preflight)."""

    return (event or {}).get("httpMethod") == "OPTIONS"
