"""Small DynamoDB updates shared by pipeline stages."""
from __future__ import annotations

import os
import time

import boto3


def record_lane(scan_id: str | None, lane: str) -> None:
    table_name = os.environ.get("SCANS_TABLE", "")
    if not scan_id or not table_name:
        return
    table = boto3.resource("dynamodb").Table(table_name)
    table.update_item(
        Key={"scan_id": scan_id},
        UpdateExpression="SET completed_subagents.#lane = :done, stage = :stage ADD progress :increment",
        ExpressionAttributeNames={"#lane": lane},
        ExpressionAttributeValues={":done": True, ":stage": "DISCOVERING", ":increment": 12},
    )


def record_complete(scan_id: str, cache_key: str | None = None) -> None:
    table_name = os.environ.get("SCANS_TABLE", "")
    if not table_name:
        return
    table = boto3.resource("dynamodb").Table(table_name)
    values = {":done": True, ":status": "COMPLETED", ":stage": "COMPLETED", ":progress": 100, ":now": int(time.time())}
    expression = "SET completed_subagents.enhancement = :done, #status = :status, stage = :stage, progress = :progress, completed_at = :now"
    if cache_key:
        values[":cache"] = cache_key
        expression += ", cache_key = :cache"
    table.update_item(Key={"scan_id": scan_id}, UpdateExpression=expression,
                      ExpressionAttributeNames={"#status": "status"}, ExpressionAttributeValues=values)
