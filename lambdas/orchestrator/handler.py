"""Classify a scan request and prepare the parallel discovery lanes."""
from __future__ import annotations

import json
import os
import re
import uuid

import boto3

from shared.bedrock_client import LITE_MODEL_ID, invoke_lite
from shared.telemetry import start_span
from shared.schemas import ProblemSignature, ScanRequest, UniversalProjectProfile

_table_name = os.environ.get("SCANS_TABLE", "")
_ddb = boto3.resource("dynamodb").Table(_table_name) if _table_name else None


def _extract(text: str, fallback_name: str) -> dict:
    prompt = (
        "Extract this software proposal as JSON with project_name, domain_keywords, "
        "and problem_signature (state_space, bottleneck_type, failure_mode, "
        "consistency_model). Use short technical phrases.\n\n" + text[:8000]
    )
    raw = invoke_lite(prompt, system="Return one JSON object only.", max_tokens=600)
    parsed = _parse_json_object(raw)
    if parsed is None:
        return {"project_name": fallback_name, "domain_keywords": [], "problem_signature": {}}
    return parsed


def _parse_json_object(raw: object) -> dict | None:
    """Parse a model reply that may wrap its JSON in markdown fences or prose."""
    if not isinstance(raw, str):
        return None
    text = raw.strip()
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end <= start:
        return None
    try:
        value = json.loads(text[start:end + 1])
    except json.JSONDecodeError:
        return None
    return value if isinstance(value, dict) else None


def lambda_handler(event: dict, context) -> dict:
    request = ScanRequest.model_validate(event)
    scan_id = event.get("scan_id") or str(uuid.uuid4())
    input_type = "GITHUB_URL" if request.repo_url else "RFC_TEXT"
    if request.repo_url:
        match = re.fullmatch(r"https://github\.com/([^/]+)/([^/#?]+)(?:\.git)?/?", request.repo_url.strip(), re.I)
        fallback_name = match.group(2) if match else "Unknown project"
        source = f"Repository {request.repo_url}. Describe its likely purpose and architecture."
    else:
        fallback_name = "Untitled RFC"
        source = request.rfc_text or ""

    trace = start_span("orchestrator", LITE_MODEL_ID, source)
    extracted = _extract(source, fallback_name)
    profile = UniversalProjectProfile(
        scan_id=scan_id,
        input_type=input_type,
        project_name=str(extracted.get("project_name") or fallback_name),
        domain_keywords=extracted.get("domain_keywords", []),
        problem_signature=ProblemSignature.model_validate(
            extracted.get("problem_signature") or {
                "state_space": "unknown", "bottleneck_type": "unknown",
                "failure_mode": "unknown", "consistency_model": "unknown",
            }
        ),
    )
    if _ddb:
        _ddb.update_item(
            Key={"scan_id": scan_id},
            UpdateExpression="SET #s = :s, stage = :stage, progress = :p, completed_subagents = if_not_exists(completed_subagents, :flags)",
            ExpressionAttributeNames={"#s": "status"},
            ExpressionAttributeValues={":s": "DISCOVERING", ":stage": "PARALLEL_DISCOVERY", ":p": 20,
                                       ":flags": {"repo_scan": False, "name_collision": False, "landscape": False,
                                                   "analogy": False, "enhancement": False}},
        )
    result = {**event, "scan_id": scan_id, "project_profile": profile.model_dump()}
    result["pipeline_trace"] = [trace.finish(profile.model_dump())]
    return result
