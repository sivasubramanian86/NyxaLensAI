"""Retrieve structurally similar cross-domain engineering patterns."""
from __future__ import annotations

import json
import os
from pathlib import Path

import numpy as np

from shared.bedrock_client import EMBED_MODEL_ID, LITE_MODEL_ID, embed, invoke_lite
from shared.progress import record_lane
from shared.schemas import AnalogyMatch
from shared.telemetry import start_span

AOSS_ENDPOINT = os.environ.get("AOSS_ENDPOINT", "")
_data_root = Path(__file__).resolve().parents[2] / "data"
if not _data_root.exists():
    _data_root = Path(__file__).resolve().parents[1] / "data"
LOCAL_EMBEDDED = _data_root / "patterns_20_embedded.json"
AOSS_INDEX = os.environ.get("AOSS_INDEX", "systems-patterns-v1")


# Raw Titan V2 cosine scores between a short query and these long pattern texts are low.
# In four probe queries the best relevant match scored 0.29-0.34 and an off-topic query's
# best match scored 0.23, so a 0.72 cutoff suppressed every analogy. This default is a
# preliminary calibration, not a validated one. The AOSS score is a different, uncalibrated
# scale and keeps its original cutoff.
LOCAL_MIN_SIMILARITY = 0.22
AOSS_MIN_SIMILARITY = 0.72


def _threshold(used_aoss: bool) -> float:
    override = os.environ.get("ANALOGY_MIN_SIMILARITY", "")
    try:
        if override:
            return float(override)
    except ValueError:
        pass
    return AOSS_MIN_SIMILARITY if used_aoss else LOCAL_MIN_SIMILARITY


def _flatten(record: dict) -> dict:
    """Map a corpus record (design nested under transferable_design) to AnalogyMatch fields.

    Records that are already flat are passed through, so both shapes are accepted.
    """
    design = record.get("transferable_design") or {}
    return {
        "pattern_id": record.get("pattern_id"),
        "source_domain": record.get("source_domain"),
        "canonical_mechanism": record.get("canonical_mechanism"),
        "mechanism": record.get("mechanism", design.get("mechanism")),
        "mapping_table": record.get("mapping_table", design.get("mapping_table")),
        "expected_lift": record.get("expected_lift", design.get("expected_lift")),
        "anti_pattern_warning": record.get("anti_pattern_warning", design.get("anti_pattern_warning")),
        "evidence": record.get("evidence"),
    }


def _query_text(signature: dict) -> str:
    source = json.dumps(signature, sort_keys=True)
    try:
        return invoke_lite(
            "Remove domain-specific nouns. Return only the underlying system behavior, "
            "bottleneck and failure dynamics as one concise sentence.\n" + source,
            max_tokens=180,
        ).strip()
    except Exception:
        return " ".join(str(v).replace("_", " ") for v in signature.values())


def _local(vector: list[float]) -> list[tuple[dict, float]]:
    if not LOCAL_EMBEDDED.exists():
        return []
    records = json.loads(LOCAL_EMBEDDED.read_text(encoding="utf-8"))
    query = np.asarray(vector, dtype=np.float32)
    query_norm = np.linalg.norm(query)
    if query_norm == 0:
        return []
    matches = []
    for item in records:
        candidate = np.asarray(item.get("embedding", []), dtype=np.float32)
        if candidate.shape != query.shape:
            continue
        norm = np.linalg.norm(candidate)
        score = float(np.dot(query, candidate) / (query_norm * norm)) if norm else 0.0
        matches.append((item["record"], score))
    return sorted(matches, key=lambda pair: pair[1], reverse=True)


def _aoss(vector: list[float], query_text: str) -> list[tuple[dict, float]]:
    from opensearchpy import OpenSearch, RequestsHttpConnection
    from requests_aws4auth import AWS4Auth
    import boto3

    session = boto3.Session()
    credentials = session.get_credentials().get_frozen_credentials()
    region = os.environ.get("AWS_REGION", "us-east-1")
    auth = AWS4Auth(credentials.access_key, credentials.secret_key, region, "aoss", session_token=credentials.token)
    client = OpenSearch(
        hosts=[{"host": AOSS_ENDPOINT.removeprefix("https://"), "port": 443}],
        http_auth=auth, use_ssl=True, verify_certs=True, connection_class=RequestsHttpConnection,
    )
    response = client.search(index=AOSS_INDEX, body={"size": 10, "query": {"bool": {"should": [
        {"knn": {"embedding": {"vector": vector, "k": 10}}},
        {"multi_match": {"query": query_text, "fields": ["text", "canonical_mechanism", "source_domain"]}},
    ], "minimum_should_match": 1}}})
    hits = response.get("hits", {}).get("hits", [])
    return [(hit.get("_source", {}).get("record", {}), min(1.0, max(0.0, float(hit.get("_score", 0))))
             ) for hit in hits]


def lambda_handler(event: dict, context) -> dict:
    profile = event["project_profile"]
    trace = start_span("analogy_engine", LITE_MODEL_ID + "+" + EMBED_MODEL_ID, profile["problem_signature"])
    query_text = _query_text(profile["problem_signature"])
    vector = embed(query_text)
    used_aoss = bool(AOSS_ENDPOINT)
    try:
        pairs = _aoss(vector, query_text) if used_aoss else _local(vector)
    except Exception:
        used_aoss = False
        pairs = _local(vector)
    threshold = _threshold(used_aoss)
    matches = []
    for record, score in pairs:
        if score < threshold:
            continue
        record = {**_flatten(record), "similarity_score": min(1.0, max(0.0, score))}
        matches.append(AnalogyMatch.model_validate(record).model_dump())
        if len(matches) == 3:
            break
    record_lane(profile.get("scan_id"), "analogy")
    payload = {"analogies": matches, "analogy_query": query_text}
    payload["pipeline_trace"] = [trace.finish(payload)]
    return payload
