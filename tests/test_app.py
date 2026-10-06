import json
from decimal import Decimal
from unittest.mock import Mock, patch

from src import app


def build_event(method="GET"):
    """
    Build a small API Gateway HTTP API
    payload version 2.0 event for testing.
    """
    return {
        "version": "2.0",
        "requestContext": {
            "http": {
                "method": method,
                "path": "/count",
            }
        },
        "headers": {
            "origin": "https://example.com",
        },
    }


@patch("src.app.boto3.resource")
def test_handler_returns_incremented_count(
    mock_boto3_resource,
):
    """
    Verify that the Lambda returns the count
    returned by DynamoDB.
    """

    mock_dynamodb = Mock()
    mock_table = Mock()

    mock_boto3_resource.return_value = mock_dynamodb
    mock_dynamodb.Table.return_value = mock_table

    mock_table.update_item.return_value = {
        "Attributes": {
            "count": Decimal("42"),
        }
    }

    app.ALLOWED_ORIGIN = "https://example.com"

    response = app.handler(
        build_event("GET"),
        None,
    )

    assert response["statusCode"] == 200

    body = json.loads(response["body"])

    assert body["count"] == 42

    assert response["headers"]["Content-Type"] == (
        "application/json"
    )

    assert response["headers"]["Access-Control-Allow-Origin"] == (
        "https://example.com"
    )


@patch("src.app.boto3.resource")
def test_handler_updates_dynamodb(
    mock_boto3_resource,
):
    """
    Verify that Lambda calls DynamoDB with the expected
    atomic increment operation.
    """

    mock_dynamodb = Mock()
    mock_table = Mock()

    mock_boto3_resource.return_value = mock_dynamodb
    mock_dynamodb.Table.return_value = mock_table

    mock_table.update_item.return_value = {
        "Attributes": {
            "count": Decimal("10"),
        }
    }

    app.ALLOWED_ORIGIN = "https://example.com"

    response = app.handler(
        build_event("GET"),
        None,
    )

    assert response["statusCode"] == 200

    mock_table.update_item.assert_called_once_with(
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


@patch("src.app.boto3.resource")
def test_handler_returns_500_when_dynamodb_fails(
    mock_boto3_resource,
):
    """
    Verify that the Lambda returns HTTP 500
    if DynamoDB fails.
    """

    mock_dynamodb = Mock()
    mock_table = Mock()

    mock_boto3_resource.return_value = mock_dynamodb
    mock_dynamodb.Table.return_value = mock_table

    mock_table.update_item.side_effect = Exception(
        "DynamoDB is unavailable"
    )

    app.ALLOWED_ORIGIN = "https://example.com"

    response = app.handler(
        build_event("GET"),
        None,
    )

    assert response["statusCode"] == 500

    body = json.loads(response["body"])

    assert body["message"] == (
        "Unable to retrieve visitor count."
    )


def test_options_request_returns_204():
    """
    Verify that the Lambda responds correctly
    to a browser CORS preflight request.
    """

    app.ALLOWED_ORIGIN = "https://example.com"

    response = app.handler(
        build_event("OPTIONS"),
        None,
    )

    assert response["statusCode"] == 204

    assert response["headers"]["Access-Control-Allow-Origin"] == (
        "https://example.com"
    )

    assert response["headers"]["Access-Control-Allow-Methods"] == (
        "GET,OPTIONS"
    )

    assert response["body"] == ""