"""Synthesize a grounded dossier, verify citations, score, and persist."""
from __future__ import annotations

import json
import os
import re
import time

import boto3

from shared.bedrock_client import SONNET_MODEL_ID, invoke_sonnet_json
from shared.memory_client import SessionMemoryProvider
from shared.schemas import EnhancementDossier, NyxaScore
from shared.telemetry import start_span

_table_name = os.environ.get("SCANS_TABLE", "")
_bucket_name = os.environ.get("EVIDENCE_BUCKET", "")
_ddb = boto3.resource("dynamodb").Table(_table_name) if _table_name else None
_s3 = boto3.client("s3") if _bucket_name else None
_url_re = re.compile(r"https?://[^\s\]\[()<>\"']+", re.I)

_TOOL = {
    "name": "enhancement_dossier",
    "description": "Return evidence-grounded repo enhancement and rubric scores.",
    "inputSchema": {"json": {"type": "object", "required": ["kill_keep_inject", "ranked_backlog", "mermaid_before_after", "rubric"], "properties": {
        "kill_keep_inject": {"type": "array", "items": {"type": "object", "required": ["action", "target_component", "rationale"], "properties": {
            "action": {"type": "string", "enum": ["KILL", "KEEP", "INJECT"]}, "target_component": {"type": "string"}, "rationale": {"type": "string"}, "citation_url": {"type": ["string", "null"]}}}},
        "ranked_backlog": {"type": "array", "maxItems": 5, "items": {"type": "object", "required": ["rank", "title", "description", "effort", "impact"], "properties": {
            "rank": {"type": "integer"}, "title": {"type": "string"}, "description": {"type": "string"}, "effort": {"type": "string", "enum": ["LOW", "MEDIUM", "HIGH"]}, "impact": {"type": "string", "enum": ["LOW", "MEDIUM", "HIGH", "VERY HIGH"]}, "citation_url": {"type": ["string", "null"]}}}},
        "mermaid_before_after": {"type": "string"},
        "rubric": {"type": "object", "required": ["clarity", "landscape_coverage", "originality", "gap_opportunity", "enhancement_potential", "evidence_quality"], "properties": {
            key: {"type": "integer", "minimum": 0, "maximum": 100} for key in ("clarity", "landscape_coverage", "originality", "gap_opportunity", "enhancement_potential", "evidence_quality")}},
    }}}
}


def _sanitize_mermaid(source: str) -> str:
    def clean(match: re.Match) -> str:
        return "[" + re.sub(r"[()\"']", "", match.group(1)) + "]"
    return re.sub(r"\[([^\]]*)\]", clean, source)


def _urls(value) -> set[str]:
    found: set[str] = set()
    if isinstance(value, dict):
        for child in value.values():
            found.update(_urls(child))
    elif isinstance(value, list):
        for child in value:
            found.update(_urls(child))
    elif isinstance(value, str):
        found.update(m.rstrip(".,;:") for m in _url_re.findall(value))
    return found


def _ground(value, allowed: set[str], removed: set[str]):
    if isinstance(value, dict):
        return {k: _ground(v, allowed, removed) for k, v in value.items()}
    if isinstance(value, list):
        return [_ground(v, allowed, removed) for v in value]
    if isinstance(value, str):
        def keep(match: re.Match) -> str:
            url = match.group(0).rstrip(".,;:")
            if url in allowed:
                return match.group(0)
            removed.add(url)
            return ""
        return _url_re.sub(keep, value)
    return value


def _score(profile: dict, collision: dict, citation_count: int, mermaid: str, rubric: dict) -> NyxaScore:
    deterministic = (
        (8 if profile.get("has_tests") else 0)
        + (6 if profile.get("dependency_count", 0) and len(profile.get("dependencies", [])) == len(set(profile.get("dependencies", []))) else 0)
        + (8 if citation_count >= 3 else round(8 * citation_count / 3))
        + (8 if any(module in " ".join(profile.get("readme_claims", [])) for module in profile.get("core_modules", [])) else 0)
        + (4 if "graph" in mermaid.lower() and "--" in mermaid else 0)
        + (6 if collision.get("traffic_light") == "GREEN" else 0)
    )
    weights = {"clarity": 15, "landscape_coverage": 15, "originality": 25, "gap_opportunity": 15, "enhancement_potential": 20, "evidence_quality": 10}
    weighted_rubric = round(sum(int(rubric.get(k, 0)) * weight for k, weight in weights.items()) / 100)
    rubric_points = round(weighted_rubric * 0.6)
    composite = min(100, deterministic + rubric_points)
    delta = min(18, max(12, round(int(rubric.get("enhancement_potential", 0)) * 0.18)))
    return NyxaScore(
        composite=composite,
        **{key: int(rubric.get(key, 0)) for key in weights},
        deterministic_points=deterministic,
        rubric_points=rubric_points,
        projected_post_enhancement=min(100, composite + delta),
        verdict="Strong differentiation" if composite >= 70 else "Opportunity to differentiate" if composite >= 45 else "Needs clearer differentiation",
    )


def lambda_handler(event: dict, context) -> dict:
    trace = start_span("enhancement_citation", SONNET_MODEL_ID, event)
    discovery = event.get("discovery", [])
    lanes = {}
    trace_entries = list(event.get("pipeline_trace", []))
    for result in discovery:
        if isinstance(result, dict):
            trace_entries.extend(result.get("pipeline_trace", []))
            lanes.update(result)
    profile = lanes.get("repo_scan") or event.get("project_profile", {})
    collision = lanes.get("name_collision", {"traffic_light": "YELLOW", "status": "MISSING"})
    landscape = lanes.get("landscape", {"direct_competitors": [], "academic_papers": [], "ecosystem_gaps": []})
    analogies = lanes.get("analogies", [])
    evidence = {"repo_scan": lanes.get("repo_scan", {}), "name_collision": collision,
                "landscape": landscape, "analogies": analogies}
    session_id = event.get("session_id") or event.get("parent_scan_id") or event.get("scan_id", "unknown")
    memory = SessionMemoryProvider()
    current_memory = {"project_name": profile.get("project_name"), "tech_stack": profile.get("tech_stack", []),
                      "matched_pattern_ids": [item.get("pattern_id") for item in analogies]}
    try:
        prior_scans = memory.retrieve(session_id, current_memory)
    except Exception:
        prior_scans = []
    evidence["prior_scans"] = prior_scans
    if _ddb:
        _ddb.update_item(Key={"scan_id": event.get("scan_id", "unknown")},
                         UpdateExpression="SET #s = :status, stage = :stage, progress = :progress",
                         ExpressionAttributeNames={"#s": "status"},
                         ExpressionAttributeValues={":status": "DISCOVERING", ":stage": "SYNTHESIZING", ":progress": 80})
    draft = invoke_sonnet_json(
        "Create a concise repo differentiation dossier. Cite only URLs present in the supplied evidence. "
        "Keep backlog to five items. Rubric dimensions are 0-100. Evidence:\n" + json.dumps(evidence, ensure_ascii=False),
        _TOOL,
        system="Use only supplied evidence. Do not invent URLs, competitors, papers, or measured lift.",
    )
    allowed = _urls(evidence)
    removed: set[str] = set()
    draft = _ground(draft, allowed, removed)
    for item in draft.get("kill_keep_inject", []) + draft.get("ranked_backlog", []):
        if item.get("citation_url") == "":
            item["citation_url"] = None
    draft["mermaid_before_after"] = _sanitize_mermaid(draft.get("mermaid_before_after", ""))
    draft["kill_keep_inject"] = draft.get("kill_keep_inject", [])[:10]
    draft["ranked_backlog"] = draft.get("ranked_backlog", [])[:5]
    verified = len(_urls(draft) & allowed)
    score = _score(profile, collision, verified, draft["mermaid_before_after"], draft.get("rubric", {}))
    trace_entries.append(trace.finish(draft, verified, len(removed)))
    parent_id = event.get("parent_scan_id")
    score_delta = None
    if parent_id and _ddb:
        parent = _ddb.get_item(Key={"scan_id": parent_id}).get("Item", {})
        prior = parent.get("nyxa_score", {}).get("composite")
        if prior is not None:
            score_delta = score.composite - int(prior)
    dossier_data = {
        "scan_id": event.get("scan_id", "unknown"), "parent_scan_id": parent_id,
        "score_delta": score_delta, "project_profile": profile,
        "name_collision": collision, "landscape": landscape, "analogies": analogies,
        "kill_keep_inject": draft["kill_keep_inject"], "ranked_backlog": draft["ranked_backlog"],
        "mermaid_before_after": draft["mermaid_before_after"], "nyxa_score": score.model_dump(),
        "verified_citations_count": verified, "stripped_hallucinations_count": len(removed),
        "pipeline_trace": trace_entries,
    }
    dossier = EnhancementDossier.model_validate(dossier_data)
    serialized = dossier.model_dump(mode="json")
    if _s3:
        _s3.put_object(Bucket=_bucket_name, Key=f"{dossier.scan_id}.json",
                       Body=json.dumps(event, ensure_ascii=False).encode(), ContentType="application/json")
    if _ddb:
        _ddb.update_item(
            Key={"scan_id": dossier.scan_id},
            UpdateExpression="SET #s = :s, stage = :stage, progress = :p, dossier = :d, nyxa_score = :n, name_collision = :c, completed_subagents.enhancement = :done, completed_at = :now",
            ExpressionAttributeNames={"#s": "status"},
            ExpressionAttributeValues={":s": "COMPLETED", ":stage": "COMPLETED", ":p": 100,
                                      ":d": json.dumps(serialized), ":n": score.model_dump(), ":c": collision,
                                      ":done": True, ":now": int(time.time())},
        )
    try:
        memory.remember(session_id, {
            "scan_id": dossier.scan_id,
            "project_name": dossier.project_profile.project_name,
            "tech_stack": dossier.project_profile.tech_stack,
            "matched_pattern_ids": [item.pattern_id for item in dossier.analogies],
            "nyxa_score": dossier.nyxa_score.composite,
            "timestamp": int(time.time()),
        })
    except Exception:
        pass
    return {"scan_id": dossier.scan_id, "status": "COMPLETED", "dossier": serialized}
