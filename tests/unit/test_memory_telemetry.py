"""Phase 5 memory and telemetry checks."""
from __future__ import annotations

import logging
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "lambdas"))

from shared.memory_client import SessionMemoryProvider
from shared.telemetry import start_span


def test_agentcore_memory_read_write_when_service_operations_exist():
    client = Mock()
    client.meta = SimpleNamespace(service_model=SimpleNamespace(operation_names=["CreateEvent", "ListEvents"]))
    client.list_events.return_value = {"events": [{"eventTimestamp": "2026-01-01", "payload": [{"json": {"content": {"scan_id": "old"}}}]}]}
    provider = SessionMemoryProvider(client=client, memory_id="memory-1")

    provider.remember("session-1", {"scan_id": "new"})
    assert provider.retrieve("session-1") == [{"scan_id": "old"}]
    client.create_event.assert_called_once()


def test_memory_uses_dynamodb_fallback():
    table = Mock()
    table.query.return_value = {"Items": [{"timestamp": 2, "summary": {"scan_id": "old", "matched_pattern_ids": ["PAT-001"]}}]}
    provider = SessionMemoryProvider(table=table, memory_id="")

    provider.remember("session-1", {"scan_id": "new"})
    assert provider.retrieve("session-1")[0]["scan_id"] == "old"
    table.put_item.assert_called_once()
    table.query.assert_called_once()


def test_telemetry_emits_emf_and_token_counts(caplog):
    with caplog.at_level(logging.INFO):
        result = start_span("scanner", "amazon.nova-lite-v1:0", "input text").finish("output", 2, 1)

    assert result["input_tokens"] == 3
    assert result["output_tokens"] == 2
    assert result["citations_verified"] == 2
    assert '"CloudWatchMetrics"' in caplog.text
