"""REST routes for starting scans, polling results, and score badges."""
from __future__ import annotations

import hashlib
import html
import json
import os
import re
import time
import uuid
from decimal import Decimal

import boto3
from boto3.dynamodb.conditions import Key
from pydantic import ValidationError

from shared.github_client import get_public_repo, get_repo_head_sha
from shared.schemas import ScanRequest

SCANS_TABLE = os.environ.get("SCANS_TABLE", "")
STATE_MACHINE_ARN = os.environ.get("STATE_MACHINE_ARN", "")
_ddb = boto3.resource("dynamodb").Table(SCANS_TABLE) if SCANS_TABLE else None
_sfn = boto3.client("stepfunctions") if STATE_MACHINE_ARN else None


def _cors_headers() -> dict:
    return {"Access-Control-Allow-Origin": "*", "Access-Control-Allow-Headers": "Content-Type,Authorization",
            "Access-Control-Allow-Methods": "GET,POST,OPTIONS"}


def _json_default(value: object) -> object:
    """DynamoDB returns numbers as Decimal, which json cannot serialize."""
    if isinstance(value, Decimal):
        return int(value) if value == value.to_integral_value() else float(value)
    raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")


def _response(status: int, body: dict) -> dict:
    return {"statusCode": status, "headers": {**_cors_headers(), "Content-Type": "application/json"},
            "body": json.dumps(body, default=_json_default)}


def _normalize(value: str) -> str:
    return " ".join(value.strip().split()).lower()


def _scan_key(normalized_input: str, commit_sha: str) -> str:
    return hashlib.sha256(f"{normalized_input}{commit_sha}".encode("utf-8")).hexdigest()


def _svg_badge(score: int, traffic_light: str) -> str:
    color = "#4c1" if score >= 70 else "#dfb317" if score >= 50 else "#e05d44"
    text = f"{max(0, min(100, score))}/100"
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="142" height="20" role="img" aria-label="Nyxa Score {text}; collision {html.escape(traffic_light)}">'
        '<linearGradient id="s" x2="0" y2="100%"><stop offset="0" stop-color="#fff" stop-opacity=".2"/>'
        '<stop offset="1" stop-opacity=".1"/></linearGradient>'
        '<rect width="142" height="20" rx="3" fill="#555"/><rect x="74" width="68" height="20" rx="3" fill="'
        + html.escape(color, quote=True) + '"/><rect x="74" width="3" height="20" fill="' + html.escape(color, quote=True) + '"/>'
        '<rect width="142" height="20" rx="3" fill="url(#s)"/>'
        '<g fill="#fff" text-anchor="middle" font-family="Verdana,sans-serif" font-size="11">'
        '<text x="37" y="14">Nyxa Score</text><text x="108" y="14">' + text + '</text></g></svg>'
    )


def _decode_dossier(value):
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return None
    return value


def _post_scan(body: dict) -> dict:
    try:
        request = ScanRequest.model_validate(body)
    except ValidationError as exc:
        return _response(422, {"error": "Invalid scan request", "details": exc.errors(include_input=False)})
    if bool(request.repo_url) == bool(request.rfc_text):
        return _response(422, {"error": "Provide exactly one of repo_url or rfc_text."})
    normalized_input = _normalize(request.rfc_text) if request.rfc_text else ""
    commit_sha = ""
    if request.repo_url:
        match = re.fullmatch(r"https://github\.com/([A-Za-z0-9-]+)/([A-Za-z0-9_.-]+)(?:\.git)?/?", request.repo_url.strip(), re.I)
        if not match:
            return _response(422, {"error": "repo_url must be a public GitHub repository URL."})
        owner, repo = match.groups()
        try:
            metadata = get_public_repo(owner, repo.removesuffix(".git"))
            if not metadata or metadata.get("private"):
                return _response(422, {"error": "Repository must be public and accessible."})
            commit_sha = body.get("commit_sha") or get_repo_head_sha(owner, repo.removesuffix(".git"))
        except Exception:
            return _response(503, {"error": "Could not verify public repository or read current commit."})
        normalized_input = f"https://github.com/{owner.lower()}/{repo.lower().removesuffix('.git')}"

    cache_key = _scan_key(normalized_input, commit_sha)
    if not request.force_refresh and _ddb:
        cutoff = int(time.time()) - 86400
        cached = _ddb.query(
            IndexName="CacheIndex",
            KeyConditionExpression=Key("cache_key").eq(cache_key) & Key("completed_at").gte(cutoff),
            ScanIndexForward=False,
            Limit=1,
        ).get("Items", [])
        if cached:
            return _response(200, {"scan_id": cached[0]["scan_id"], "status": "COMPLETED"})

    scan_id = str(uuid.uuid4())
    if not _ddb or not _sfn or not STATE_MACHINE_ARN:
        return _response(503, {"error": "Scan service is not configured."})
    flags = {"repo_scan": False, "name_collision": False, "landscape": False, "analogy": False, "enhancement": False}
    _ddb.put_item(Item={"scan_id": scan_id, "status": "INITIALIZED", "stage": "QUEUED", "progress": 5,
                        "cache_key": cache_key, "parent_scan_id": request.parent_scan_id,
                        "session_id": body.get("session_id") or scan_id,
                        "completed_subagents": flags,
                        "created_at": int(time.time()), "ttl": int(time.time()) + 604800})
    try:
        _sfn.start_execution(stateMachineArn=STATE_MACHINE_ARN, name=scan_id,
                             input=json.dumps({**body, "scan_id": scan_id, "cache_key": cache_key}))
    except Exception:
        _ddb.update_item(Key={"scan_id": scan_id}, UpdateExpression="SET #s = :s",
                         ExpressionAttributeNames={"#s": "status"}, ExpressionAttributeValues={":s": "FAILED"})
        return _response(503, {"error": "Could not start scan."})
    return _response(202, {"scan_id": scan_id, "status": "INITIALIZED"})


def _get_scan(scan_id: str) -> dict:
    item = _ddb.get_item(Key={"scan_id": scan_id}).get("Item") if _ddb else None
    if not item:
        return _response(404, {"error": "Scan not found"})
    dossier = _decode_dossier(item.get("dossier"))
    response = {"scan_id": scan_id, "status": item.get("status"), "stage": item.get("stage"),
                "progress": item.get("progress", 0), "completed_subagents": item.get("completed_subagents", {}),
                "dossier": dossier}
    parent_id = item.get("parent_scan_id")
    if parent_id:
        parent = _ddb.get_item(Key={"scan_id": parent_id}).get("Item", {})
        parent_score = (parent.get("nyxa_score") or {}).get("composite")
        current_score = (item.get("nyxa_score") or {}).get("composite")
        if parent_score is not None and current_score is not None:
            response["score_delta"] = int(current_score) - int(parent_score)
    return _response(200, response)


def _get_badge(scan_id: str) -> dict:
    item = _ddb.get_item(Key={"scan_id": scan_id}).get("Item") if _ddb else None
    if not item:
        return _response(404, {"error": "Scan not found"})
    score = int((item.get("nyxa_score") or {}).get("composite", 0))
    traffic_light = (item.get("name_collision") or {}).get("traffic_light", "YELLOW")
    return {"statusCode": 200, "headers": {**_cors_headers(), "Content-Type": "image/svg+xml",
            "Cache-Control": "max-age=300"}, "body": _svg_badge(score, traffic_light)}


def lambda_handler(event: dict, context) -> dict:
    method = event.get("httpMethod", "")
    path = event.get("path", "")
    path_params = event.get("pathParameters") or {}
    if method == "OPTIONS":
        return {"statusCode": 200, "headers": _cors_headers(), "body": ""}
    if method == "POST" and path.rstrip("/") == "/scans":
        try:
            body = json.loads(event.get("body") or "{}")
        except json.JSONDecodeError:
            return _response(400, {"error": "Request body must be valid JSON."})
        return _post_scan(body)
    if method == "GET" and "scan_id" in path_params:
        scan_id = path_params["scan_id"]
        if path.startswith("/badge/"):
            return _get_badge(scan_id)
        return _get_scan(scan_id)
    return _response(404, {"error": "Unknown route"})
