"""Persist a terminal failure state so the UI can stop polling."""
from __future__ import annotations

import json
import os

import boto3


def lambda_handler(event: dict, context) -> dict:
    scan_id = event.get("scan_id")
    table_name = os.environ.get("SCANS_TABLE", "")
    if scan_id and table_name:
        error = event.get("failure", {})
        boto3.resource("dynamodb").Table(table_name).update_item(
            Key={"scan_id": scan_id},
            UpdateExpression="SET #s = :status, stage = :stage, progress = :progress, #e = :error",
            ExpressionAttributeNames={"#s": "status", "#e": "error"},
            ExpressionAttributeValues={":status": "FAILED", ":stage": "FAILED", ":progress": 100,
                                      ":error": json.dumps(error, default=str)[:1000]},
        )
    return {"scan_id": scan_id, "status": "FAILED"}
