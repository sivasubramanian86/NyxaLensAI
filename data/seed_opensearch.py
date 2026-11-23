"""
NyxaLensAI — Pattern Corpus Seeder

Modes:
  --mode aoss   Index all 20 patterns into Amazon OpenSearch Serverless
                (requires a deployed AOSS collection)
  --mode local  Write pre-computed embeddings to data/patterns_20_embedded.json
                (zero-cost numpy fallback; works after `cdk destroy`)

Flags:
  --dry-run       Validate JSON + schema; do not call Bedrock or OpenSearch
  --force-refresh Delete the existing index and re-create from scratch

Usage:
  python data/seed_opensearch.py --mode local
  python data/seed_opensearch.py --mode aoss --force-refresh
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

# Allow running from repo root without installing the package
sys.path.insert(0, str(Path(__file__).parent.parent / "lambdas"))

from pydantic import BaseModel, field_validator
from typing import Literal


# ── Minimal schema for validation (mirrors schemas.py PatternEvidence) ─────

class PatternEvidence(BaseModel):
    standard: str
    reference_url: str
    measurement_status: Literal["ESTIMATED", "BENCHMARKED"] = "ESTIMATED"

    @field_validator("reference_url")
    @classmethod
    def must_be_https(cls, v: str) -> str:
        if not v.startswith("https://"):
            raise ValueError(f"reference_url must use HTTPS: {v}")
        return v


class MappingEntry(BaseModel):
    source_primitive: str
    target_repo_module: str
    expected_effect: str


class TransferableDesign(BaseModel):
    mechanism: str
    mapping_table: list[MappingEntry]
    expected_lift: str
    anti_pattern_warning: str


TransferableDesign.model_rebuild()


class ProblemSignature(BaseModel):
    state_space: str
    bottleneck_type: str
    failure_mode: str
    consistency_model: str


class AnalogPattern(BaseModel):
    pattern_id: str
    source_domain: str
    canonical_mechanism: str
    problem_signature: ProblemSignature
    trigger_condition: dict
    transferable_design: TransferableDesign
    evidence: PatternEvidence


# Explicit rebuild needed when from __future__ import annotations is active
AnalogPattern.model_rebuild()


# ── Paths ──────────────────────────────────────────────────────────────────

REPO_ROOT   = Path(__file__).parent.parent
PATTERNS    = REPO_ROOT / "data" / "patterns_20.json"
EMBEDDED    = REPO_ROOT / "data" / "patterns_20_embedded.json"
AOSS_INDEX  = os.environ.get("AOSS_INDEX", "systems-patterns-v1")
AOSS_EP     = os.environ.get("AOSS_ENDPOINT", "")
EMBED_MODEL = os.environ.get("EMBED_MODEL_ID", "amazon.titan-embed-text-v2:0")


def load_and_validate() -> list[AnalogPattern]:
    """Load patterns_20.json and validate every record against AnalogPattern schema."""
    raw = json.loads(PATTERNS.read_text(encoding="utf-8"))
    validated = []
    errors = []
    for i, record in enumerate(raw):
        try:
            validated.append(AnalogPattern.model_validate(record))
        except Exception as e:
            errors.append(f"Pattern {i} ({record.get('pattern_id', '?')}): {e}")
    if errors:
        print("VALIDATION ERRORS:")
        for err in errors:
            print(f"  {err}")
        sys.exit(1)
    print(f"[OK] All {len(validated)} patterns validated against AnalogPattern schema.")
    return validated


def _embed_text(text: str) -> list[float]:
    """Generate 1024-dim Titan Embeddings v2 vector."""
    import json as _json

    import boto3
    client = boto3.client("bedrock-runtime",
                           region_name=os.environ.get("AWS_REGION", "us-east-1"))
    response = client.invoke_model(
        modelId=EMBED_MODEL,
        body=_json.dumps({"inputText": text, "dimensions": 1024, "normalize": True}),
        contentType="application/json",
        accept="application/json",
    )
    return _json.loads(response["body"].read())["embedding"]


def _pattern_text(p: AnalogPattern) -> str:
    """Build the text string to embed for a pattern."""
    return (
        f"{p.source_domain}. {p.canonical_mechanism}. "
        f"State space: {p.problem_signature.state_space}. "
        f"Bottleneck: {p.problem_signature.bottleneck_type}. "
        f"Failure mode: {p.problem_signature.failure_mode}. "
        f"Mechanism: {p.transferable_design.mechanism}"
    )


def seed_local(patterns: list[AnalogPattern], dry_run: bool) -> None:
    """Write pre-computed embeddings to data/patterns_20_embedded.json."""
    if dry_run:
        print("DRY RUN - skipping Bedrock embedding calls and local file write.")
        return
    print("Generating local embeddings via Bedrock Titan Embeddings v2 …")
    embedded = []
    for p in patterns:
        text = _pattern_text(p)
        vec  = _embed_text(text)
        embedded.append({"pattern_id": p.pattern_id, "embedding": vec,
                          "text": text, "record": p.model_dump()})
        print(f"  [OK] {p.pattern_id}: {p.canonical_mechanism}")
    EMBEDDED.write_text(json.dumps(embedded, indent=2), encoding="utf-8")
    print(f"\n[OK] Local embeddings written to {EMBEDDED}")
    print("  The analogy_engine Lambda will use this file when AOSS is unavailable.")


def seed_aoss(patterns: list[AnalogPattern], dry_run: bool, force_refresh: bool) -> None:
    """Index patterns into Amazon OpenSearch Serverless."""
    if not AOSS_EP:
        print("ERROR: AOSS_ENDPOINT environment variable not set.")
        print("       Run `cdk deploy` first, then set AOSS_ENDPOINT from stack outputs.")
        sys.exit(1)

    if dry_run:
        print(f"DRY RUN — would index {len(patterns)} patterns into {AOSS_INDEX} at {AOSS_EP}.")
        return

    try:
        from opensearchpy import OpenSearch, RequestsHttpConnection
        from requests_aws4auth import AWS4Auth
        import boto3 as _boto3
    except ImportError:
        print("Install opensearch-py and requests-aws4auth: pip install opensearch-py requests-aws4auth")
        sys.exit(1)

    session    = _boto3.Session()
    creds      = session.get_credentials()
    region     = os.environ.get("AWS_REGION", "us-east-1")
    awsauth    = AWS4Auth(creds.access_key, creds.secret_key, region, "aoss",
                          session_token=creds.token)
    host       = AOSS_EP.replace("https://", "")
    client     = OpenSearch(hosts=[{"host": host, "port": 443}],
                             http_auth=awsauth,
                             use_ssl=True,
                             verify_certs=True,
                             connection_class=RequestsHttpConnection)

    if force_refresh and client.indices.exists(index=AOSS_INDEX):
        client.indices.delete(index=AOSS_INDEX)
        print(f"[OK] Deleted existing index: {AOSS_INDEX}")

    if not client.indices.exists(index=AOSS_INDEX):
        mapping = {
            "settings": {"index": {"knn": True}},
            "mappings": {
                "properties": {
                    "embedding": {"type": "knn_vector", "dimension": 1024,
                                   "method": {"name": "hnsw", "space_type": "cosinesimil",
                                               "engine": "nmslib"}},
                    "pattern_id": {"type": "keyword"},
                    "source_domain": {"type": "text"},
                    "canonical_mechanism": {"type": "text"},
                    "text": {"type": "text"},
                    "record": {"type": "object", "enabled": False},
                }
            }
        }
        client.indices.create(index=AOSS_INDEX, body=mapping)
        print(f"[OK] Created index: {AOSS_INDEX}")

    for p in patterns:
        text = _pattern_text(p)
        vec  = _embed_text(text)
        doc  = {"pattern_id": p.pattern_id, "source_domain": p.source_domain,
                 "canonical_mechanism": p.canonical_mechanism, "text": text,
                 "embedding": vec, "record": p.model_dump()}
        client.index(index=AOSS_INDEX, id=p.pattern_id, body=doc)
        print(f"  [OK] Indexed {p.pattern_id}: {p.canonical_mechanism}")

    print(f"\n[OK] All {len(patterns)} patterns indexed into {AOSS_INDEX}")


def main():
    parser = argparse.ArgumentParser(description="NyxaLensAI Pattern Corpus Seeder")
    parser.add_argument("--mode", choices=["aoss", "local"], default="local",
                        help="aoss: index into OpenSearch Serverless; local: write numpy fallback")
    parser.add_argument("--dry-run", action="store_true",
                        help="Validate only; do not call Bedrock or OpenSearch")
    parser.add_argument("--force-refresh", action="store_true",
                        help="Delete existing index and re-create from scratch (aoss only)")
    args = parser.parse_args()

    if args.force_refresh and args.mode != "aoss":
        print("WARNING: --force-refresh is only valid with --mode aoss; ignoring flag.")
        args.force_refresh = False

    patterns = load_and_validate()

    if args.mode == "local":
        seed_local(patterns, dry_run=args.dry_run)
    else:
        seed_aoss(patterns, dry_run=args.dry_run, force_refresh=args.force_refresh)


if __name__ == "__main__":
    main()
