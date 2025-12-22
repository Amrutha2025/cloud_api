# Shared DynamoDB helper functions

import os
from typing import Any, Dict, List, Optional

import boto3
from botocore.exceptions import ClientError


_dynamodb_resource = boto3.resource("dynamodb")


def _get_env_var(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def get_incidents_table():
    """Return a DynamoDB Table instance for the incidents table."""

    table_name = _get_env_var("INCIDENTS_TABLE_NAME")
    return _dynamodb_resource.Table(table_name)


def put_incident_item(item: Dict[str, Any]) -> None:
    """Create a new incident item.

    Uses a conditional put to avoid overwriting an existing incident_id.
    Raises ClientError on failure.
    """

    table = get_incidents_table()
    table.put_item(Item=item, ConditionExpression="attribute_not_exists(incident_id)")


def get_incident_item(incident_id: str) -> Optional[Dict[str, Any]]:
    """Fetch a single incident by ID. Returns None if not found."""

    table = get_incidents_table()
    response = table.get_item(Key={"incident_id": incident_id})
    return response.get("Item")


def scan_incidents() -> List[Dict[str, Any]]:
    """Return all incidents using a DynamoDB scan.

    This is intended for small datasets or admin/debug tooling.
    """

    table = get_incidents_table()
    items: List[Dict[str, Any]] = []
    scan_kwargs: Dict[str, Any] = {}

    while True:
        response = table.scan(**scan_kwargs)
        items.extend(response.get("Items", []))
        last_key = response.get("LastEvaluatedKey")
        if not last_key:
            break
        scan_kwargs["ExclusiveStartKey"] = last_key

    return items


def update_incident_status(incident_id: str, status: str, updated_at: str) -> Dict[str, Any]:
    """Update an incident's status, returning the updated item.

    Raises ClientError. Caller should handle ConditionalCheckFailedException
    when the incident does not exist.
    """

    table = get_incidents_table()
    response = table.update_item(
        Key={"incident_id": incident_id},
        UpdateExpression="SET #s = :s, updated_at = :u",
        ExpressionAttributeNames={"#s": "status"},
        ExpressionAttributeValues={":s": status, ":u": updated_at},
        ConditionExpression="attribute_exists(incident_id)",
        ReturnValues="ALL_NEW",
    )
    return response.get("Attributes", {})
