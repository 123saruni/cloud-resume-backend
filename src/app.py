import json
import os
from typing import Any

import boto3


TABLE_NAME = os.environ.get(
    "TABLE_NAME",
    "visitor_count",
)

ALLOWED_ORIGIN = os.environ.get(
    "ALLOWED_ORIGIN",
    "*",
)


def get_table():
    """
    Create and return the DynamoDB table resource.
    """
    dynamodb = boto3.resource("dynamodb")

    return dynamodb.Table(TABLE_NAME)


def get_request_method(event: dict[str, Any]) -> str:
    """
    Get the HTTP method from an API Gateway HTTP API
    payload version 2.0 event.
    """
    return (
        event.get("requestContext", {})
        .get("http", {})
        .get("method", "GET")
        .upper()
    )


def build_response(
    status_code: int,
    body: dict[str, Any] | None = None,
    origin: str | None = None,
) -> dict[str, Any]:
    """
    Build a Lambda proxy response.
    """
    headers = {
        "Content-Type": "application/json",
        "Access-Control-Allow-Methods": "GET,OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type",
        "Access-Control-Allow-Origin": origin or ALLOWED_ORIGIN,
    }

    return {
        "statusCode": status_code,
        "headers": headers,
        "body": json.dumps(body) if body is not None else "",
    }


def handler(
    event: dict[str, Any],
    context: Any,
) -> dict[str, Any]:
    """
    Increment the visitor counter in DynamoDB
    and return the new count.
    """

    method = get_request_method(event)

    # Handle browser CORS preflight requests.
    if method == "OPTIONS":
        return build_response(
            status_code=204,
            origin=ALLOWED_ORIGIN,
        )

    try:
        table = get_table()

        response = table.update_item(
            Key={
                "id": "visitor_counter",
            },
            UpdateExpression="ADD #count :increment",
            ExpressionAttributeNames={
                "#count": "count",
            },
            ExpressionAttributeValues={
                ":increment": 1,
            },
            ReturnValues="UPDATED_NEW",
        )

        new_count = int(
            response["Attributes"]["count"]
        )

        return build_response(
            status_code=200,
            body={
                "count": new_count,
            },
            origin=ALLOWED_ORIGIN,
        )

    except Exception as exc:
        print(f"Visitor counter error: {exc}")

        return build_response(
            status_code=500,
            body={
                "message": "Unable to retrieve visitor count.",
            },
            origin=ALLOWED_ORIGIN,
        )