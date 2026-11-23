"""Regression tests for defects that only appeared against real AWS.

Each case reproduces a failure seen on the first live deployment, where the mocked
tests had passed.
"""
import json
import sys
from decimal import Decimal
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "lambdas"))

import pytest  # noqa: E402

from api_router import handler as api_router  # noqa: E402
from analogy_engine import handler as analogy_engine  # noqa: E402
from orchestrator import handler as orchestrator  # noqa: E402


def test_api_response_serializes_dynamodb_decimals():
    body = {"progress": Decimal("100"), "score": Decimal("78.5")}
    parsed = json.loads(api_router._response(200, body)["body"])
    assert parsed == {"progress": 100, "score": 78.5}


def test_api_response_still_rejects_unknown_types():
    with pytest.raises(TypeError):
        api_router._response(200, {"bad": object()})


@pytest.mark.parametrize("raw", [
    '{"project_name": "Gateway"}',
    '```json\n{"project_name": "Gateway"}\n```',
    'Here is the JSON:\n{"project_name": "Gateway"}\nHope that helps.',
])
def test_orchestrator_parses_json_wrapped_in_fences_or_prose(raw):
    assert orchestrator._parse_json_object(raw) == {"project_name": "Gateway"}


@pytest.mark.parametrize("raw", ["", "no json here", "{broken", "[1, 2]", None])
def test_orchestrator_rejects_non_object_replies(raw):
    assert orchestrator._parse_json_object(raw) is None


def test_failure_handler_escapes_reserved_dynamodb_keywords(monkeypatch):
    from failure_handler import handler as failure

    table = MagicMock()
    monkeypatch.setenv("SCANS_TABLE", "scans")
    with patch.object(failure.boto3, "resource") as resource:
        resource.return_value.Table.return_value = table
        failure.lambda_handler({"scan_id": "s1", "failure": {"Error": "boom"}}, None)
    kwargs = table.update_item.call_args.kwargs
    names = kwargs["ExpressionAttributeNames"]
    expression = kwargs["UpdateExpression"]
    # `status` and `error` are DynamoDB reserved words and must be aliased.
    assert names["#s"] == "status" and names["#e"] == "error"
    assert " status " not in expression and ", error " not in expression


def test_analogy_threshold_defaults_and_override(monkeypatch):
    monkeypatch.delenv("ANALOGY_MIN_SIMILARITY", raising=False)
    assert analogy_engine._threshold(used_aoss=False) == analogy_engine.LOCAL_MIN_SIMILARITY
    assert analogy_engine._threshold(used_aoss=True) == analogy_engine.AOSS_MIN_SIMILARITY
    monkeypatch.setenv("ANALOGY_MIN_SIMILARITY", "0.4")
    assert analogy_engine._threshold(used_aoss=False) == 0.4
    monkeypatch.setenv("ANALOGY_MIN_SIMILARITY", "not-a-number")
    assert analogy_engine._threshold(used_aoss=False) == analogy_engine.LOCAL_MIN_SIMILARITY


def test_every_real_corpus_record_becomes_a_valid_analogy_match():
    from shared.schemas import AnalogyMatch

    corpus = json.loads((Path(__file__).parent.parent.parent / "data" / "patterns_20.json").read_text(encoding="utf-8"))
    assert len(corpus) == 20
    for record in corpus:
        match = AnalogyMatch.model_validate({**analogy_engine._flatten(record), "similarity_score": 0.3})
        assert match.mapping_table and match.mechanism and match.evidence.reference_url.startswith("https://")


def test_flatten_accepts_already_flat_records():
    flat = {"pattern_id": "PAT-X", "mechanism": "m", "mapping_table": [], "expected_lift": "l",
            "anti_pattern_warning": "w", "source_domain": "d", "canonical_mechanism": "c", "evidence": {}}
    assert analogy_engine._flatten(flat)["mechanism"] == "m"


def test_local_threshold_admits_real_world_titan_scores():
    # Observed best relevant cosine scores were 0.29-0.34; an off-topic best was 0.23.
    assert analogy_engine.LOCAL_MIN_SIMILARITY <= 0.27
    assert analogy_engine.LOCAL_MIN_SIMILARITY >= 0.15
