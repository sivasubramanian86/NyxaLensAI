"""Session scan memory with AgentCore and DynamoDB/local fallbacks."""
from __future__ import annotations

import os
import time
from datetime import datetime, timezone
from typing import Any

import boto3
from boto3.dynamodb.conditions import Key
from botocore.exceptions import UnknownServiceError


class SessionMemoryProvider:
    def __init__(self, client=None, table=None, memory_id: str | None = None) -> None:
        self.memory_id = memory_id or os.environ.get("AGENTCORE_MEMORY_ID", "")
        self.table_name = os.environ.get("SESSION_MEMORY_TABLE", "")
        self.table = table
        self._client = client
        self._local: dict[str, list[dict]] = {}
        if self.table is None and self.table_name:
            self.table = boto3.resource("dynamodb").Table(self.table_name)
        if self._client is None and self.memory_id:
            try:
                self._client = boto3.client("bedrock-agentcore")
            except (UnknownServiceError, Exception):
                self._client = None
        operations = set(getattr(getattr(getattr(self._client, "meta", None), "service_model", None), "operation_names", []))
        self.native_enabled = bool(self.memory_id and {"CreateEvent", "ListEvents"} <= operations)

    @staticmethod
    def _actor_id(session_id: str) -> str:
        return "builder-" + session_id[:56]

    def remember(self, session_id: str, summary: dict[str, Any]) -> None:
        if self.native_enabled:
            try:
                self._client.create_event(
                    memoryId=self.memory_id,
                    actorId=self._actor_id(session_id),
                    sessionId=session_id,
                    eventTimestamp=datetime.now(timezone.utc),
                    payload=[{"json": {"content": summary}}],
                    extractionMode="SKIP",
                )
                return
            except Exception:
                pass
        item = {"session_id": session_id, "timestamp": int(time.time()), "summary": summary,
                "ttl": int(time.time()) + 90 * 86400}
        if self.table is not None:
            self.table.put_item(Item=item)
        else:
            self._local.setdefault(session_id, []).append(item)

    def retrieve(self, session_id: str, current: dict[str, Any] | None = None) -> list[dict]:
        records: list[dict] = []
        if self.native_enabled:
            try:
                response = self._client.list_events(
                    memoryId=self.memory_id,
                    actorId=self._actor_id(session_id),
                    sessionId=session_id,
                    includePayloads=True,
                    maxResults=20,
                )
                for event in response.get("events", []):
                    for payload in event.get("payload", []):
                        summary = payload.get("json", {}).get("content")
                        if isinstance(summary, dict):
                            records.append({"summary": summary, "timestamp": event.get("eventTimestamp")})
            except Exception:
                records = []
        if not records:
            if self.table is not None:
                response = self.table.query(
                    KeyConditionExpression=Key("session_id").eq(session_id),
                    ScanIndexForward=False,
                    Limit=20,
                )
                records = response.get("Items", [])
            else:
                records = list(reversed(self._local.get(session_id, [])))[0:20]
        return [record["summary"] for record in sorted(records, key=lambda r: str(r.get("timestamp", "")), reverse=True)
                if isinstance(record.get("summary"), dict)][:3] if current is None else self._relevant(records, current)

    @staticmethod
    def _relevant(records: list[dict], current: dict[str, Any]) -> list[dict]:
        patterns = set(current.get("matched_pattern_ids", []))
        tech = {str(value).lower() for value in current.get("tech_stack", [])}
        ranked = []
        for record in records:
            summary = record.get("summary", {})
            prior_patterns = set(summary.get("matched_pattern_ids", []))
            prior_tech = {str(value).lower() for value in summary.get("tech_stack", [])}
            score = 3 * len(patterns & prior_patterns) + len(tech & prior_tech)
            if current.get("project_name") and current.get("project_name") == summary.get("project_name"):
                score += 2
            if score:
                ranked.append((score, str(record.get("timestamp", "")), summary))
        ranked.sort(key=lambda row: (row[0], row[1]), reverse=True)
        return [summary for _, _, summary in ranked[:3]]
