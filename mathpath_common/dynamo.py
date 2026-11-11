"""DynamoDB access shared by both services. Each service owns exactly one table;
nothing reads another service's table (cross-service data goes over HTTP)."""

import os
from decimal import Decimal

import boto3

CONTENT_TABLE = os.getenv("CONTENT_TABLE", "mathpath-content")
PRACTICE_TABLE = os.getenv("PRACTICE_TABLE", "mathpath-practice")


def resource():
    kwargs = {"region_name": os.getenv("AWS_REGION", "ap-south-1")}
    if endpoint := os.getenv("DYNAMODB_ENDPOINT"):  # DynamoDB Local in docker-compose
        kwargs["endpoint_url"] = endpoint
    return boto3.resource("dynamodb", **kwargs)


def to_plain(value):
    """boto3 returns numbers as Decimal; convert them for JSON responses."""
    if isinstance(value, list):
        return [to_plain(v) for v in value]
    if isinstance(value, dict):
        return {k: to_plain(v) for k, v in value.items()}
    if isinstance(value, Decimal):
        return int(value) if value == value.to_integral_value() else float(value)
    return value


def to_ddb(value):
    """Floats are not accepted by boto3; store them as Decimal."""
    if isinstance(value, list):
        return [to_ddb(v) for v in value]
    if isinstance(value, dict):
        return {k: to_ddb(v) for k, v in value.items()}
    if isinstance(value, float):
        return Decimal(str(round(value, 4)))
    return value


def create_tables(ddb):
    """Single-table layouts, see README "DynamoDB design"."""
    existing = {t.name for t in ddb.tables.all()}
    if CONTENT_TABLE not in existing:
        ddb.create_table(
            TableName=CONTENT_TABLE,
            BillingMode="PAY_PER_REQUEST",
            KeySchema=[{"AttributeName": "PK", "KeyType": "HASH"}, {"AttributeName": "SK", "KeyType": "RANGE"}],
            AttributeDefinitions=[
                {"AttributeName": n, "AttributeType": "S"} for n in ("PK", "SK", "GSI1PK", "GSI1SK")
            ],
            GlobalSecondaryIndexes=[{
                "IndexName": "GSI1",
                "KeySchema": [{"AttributeName": "GSI1PK", "KeyType": "HASH"},
                              {"AttributeName": "GSI1SK", "KeyType": "RANGE"}],
                "Projection": {"ProjectionType": "ALL"},
            }],
        ).wait_until_exists()
    if PRACTICE_TABLE not in existing:
        ddb.create_table(
            TableName=PRACTICE_TABLE,
            BillingMode="PAY_PER_REQUEST",
            KeySchema=[{"AttributeName": "PK", "KeyType": "HASH"}, {"AttributeName": "SK", "KeyType": "RANGE"}],
            AttributeDefinitions=[{"AttributeName": n, "AttributeType": "S"} for n in ("PK", "SK")],
        ).wait_until_exists()
