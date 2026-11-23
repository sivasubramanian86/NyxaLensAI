"""API cache, execution, delta, and SVG behavior."""
from __future__ import annotations

import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "lambdas"))

import api_router.handler as api


def event(method: str, path: str, body=None, params=None):
    return {"httpMethod": method, "path": path, "body": json.dumps(body) if body is not None else None,
            "pathParameters": params or {}}


def test_post_returns_completed_cache_hit():
    table = MagicMock()
    table.query.return_value = {"Items": [{"scan_id": "cached", "status": "COMPLETED"}]}
    with patch.object(api, "_ddb", table), patch.object(api, "_sfn") as sfn, \
         patch.object(api, "get_repo_head_sha", return_value="sha"), patch.object(api, "get_public_repo", return_value={"private": False}):
        response = api.lambda_handler(event("POST", "/scans", {"repo_url": "https://github.com/acme/demo"}), None)
    assert response["statusCode"] == 200
    assert json.loads(response["body"])["scan_id"] == "cached"
    sfn.start_execution.assert_not_called()


def test_post_cache_miss_persists_and_starts_execution():
    table = MagicMock()
    table.query.return_value = {"Items": []}
    with patch.object(api, "_ddb", table), patch.object(api, "_sfn") as sfn, \
         patch.object(api, "STATE_MACHINE_ARN", "arn:state-machine"):
        response = api.lambda_handler(event("POST", "/scans", {"rfc_text": "Design a resilient scanner", "parent_scan_id": "parent"}), None)
    payload = json.loads(response["body"])
    assert response["statusCode"] == 202
    table.put_item.assert_called_once()
    started = json.loads(sfn.start_execution.call_args.kwargs["input"])
    assert started["scan_id"] == payload["scan_id"]
    assert started["parent_scan_id"] == "parent"


def test_invalid_or_private_repository_does_not_start_execution():
    table = MagicMock()
    with patch.object(api, "_ddb", table), patch.object(api, "_sfn") as sfn:
        invalid = api.lambda_handler(event("POST", "/scans", {"repo_url": "https://example.com/private"}), None)
        with patch.object(api, "get_public_repo", return_value={"private": True}):
            private = api.lambda_handler(event("POST", "/scans", {"repo_url": "https://github.com/acme/private"}), None)
    assert invalid["statusCode"] == private["statusCode"] == 422
    sfn.start_execution.assert_not_called()


def test_get_scan_calculates_parent_score_delta():
    table = MagicMock()
    table.get_item.side_effect = [
        {"Item": {"scan_id": "child", "status": "COMPLETED", "progress": 100,
                   "parent_scan_id": "parent", "nyxa_score": {"composite": 79}, "dossier": "{}"}},
        {"Item": {"nyxa_score": {"composite": 64}}},
    ]
    with patch.object(api, "_ddb", table):
        response = api.lambda_handler(event("GET", "/scans/child", params={"scan_id": "child"}), None)
    body = json.loads(response["body"])
    assert response["statusCode"] == 200
    assert body["score_delta"] == 15


def test_badge_is_well_formed_svg_and_cacheable():
    table = MagicMock()
    table.get_item.return_value = {"Item": {"nyxa_score": {"composite": 79}, "name_collision": {"traffic_light": "GREEN"}}}
    with patch.object(api, "_ddb", table):
        response = api.lambda_handler(event("GET", "/badge/scan", params={"scan_id": "scan"}), None)
    assert response["headers"]["Content-Type"] == "image/svg+xml"
    assert response["headers"]["Cache-Control"] == "max-age=300"
    root = ET.fromstring(response["body"])
    assert root.tag.endswith("svg")
    assert "79/100" in "".join(root.itertext())
