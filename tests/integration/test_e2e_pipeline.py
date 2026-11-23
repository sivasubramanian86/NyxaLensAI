"""Local end-to-end Step Functions payload simulation with service calls mocked."""
from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "lambdas"))

import orchestrator.handler as orchestrator
import repo_scanner.handler as repo_scanner
import name_collision.handler as name_collision
import landscape_scout.handler as landscape_scout
import analogy_engine.handler as analogy_engine
import enhancement_citation.handler as enhancement
from shared.schemas import EnhancementDossier


def test_full_pipeline_payload_returns_valid_dossier():
    extraction = {"project_name": "Sample", "domain_keywords": ["repo analysis"], "problem_signature": {
        "state_space": "repository modules", "bottleneck_type": "duplicate effort",
        "failure_mode": "parallel reinvention", "consistency_model": "eventual"}}
    raw_files = {"README.md": "# Sample\n- Python architecture", "pyproject.toml": "[project]\ndependencies=['httpx']",
                 "src/main.py": "import ast\ndef scan(): return ast.parse('')"}
    tree = {"tree": [{"path": path, "type": "blob"} for path in raw_files]}
    repo = {"full_name": "acme/sample", "name": "sample", "owner": {"login": "acme"},
            "html_url": "https://github.com/acme/sample", "stargazers_count": 8, "description": "Sample"}
    draft = {"kill_keep_inject": [{"action": "KEEP", "target_component": "scanner", "rationale": "Has AST parsing"}],
             "ranked_backlog": [{"rank": 1, "title": "Add tests", "description": "Exercise parser", "effort": "LOW", "impact": "HIGH"}],
             "mermaid_before_after": "graph TD; A[repo] --> B[scanner]",
             "rubric": {key: 70 for key in ("clarity", "landscape_coverage", "originality", "gap_opportunity", "enhancement_potential", "evidence_quality")}}

    with patch.object(orchestrator, "invoke_lite", return_value=json.dumps(extraction)), \
         patch.object(orchestrator, "_ddb", None):
        initial = orchestrator.lambda_handler({"repo_url": "https://github.com/acme/sample", "scan_id": "e2e-1"}, None)
    with patch.object(repo_scanner, "get_repo_tree", return_value=tree), \
         patch.object(repo_scanner, "get_file_content", side_effect=lambda owner, name, path: raw_files[path]):
        repo_result = repo_scanner.lambda_handler(initial, None)
    async def empty_collision_lookup(name):
        return [], False
    with patch.object(name_collision, "_lookup", side_effect=empty_collision_lookup), \
         patch.object(name_collision, "_double_metaphone", return_value=set()):
        collision_result = name_collision.lambda_handler(initial, None)
    with patch.object(landscape_scout, "_queries", return_value=["repo architecture" ]), \
         patch.object(landscape_scout, "search_repos", return_value=[repo]), \
         patch.object(landscape_scout, "get_file_content", return_value="## Limitations\n- No hosted mode"), \
         patch.object(landscape_scout, "_arxiv", return_value=[]):
        landscape_result = landscape_scout.lambda_handler(initial, None)
    with patch.object(analogy_engine, "_query_text", return_value="bounded repository architecture"), \
         patch.object(analogy_engine, "embed", return_value=[1.0, 0.0]), \
         patch.object(analogy_engine, "LOCAL_EMBEDDED", Path("missing-patterns.json")), \
         patch.object(analogy_engine, "AOSS_ENDPOINT", ""):
        analogy_result = analogy_engine.lambda_handler(initial, None)
    final_input = {**initial, "discovery": [repo_result, collision_result, landscape_result, analogy_result]}
    with patch.object(enhancement, "invoke_sonnet_json", return_value=draft), \
         patch.object(enhancement, "_ddb", None), patch.object(enhancement, "_s3", None):
        final = enhancement.lambda_handler(final_input, None)

    dossier = EnhancementDossier.model_validate(final["dossier"])
    assert final["status"] == "COMPLETED"
    assert dossier.project_profile.code_files_scanned == 1
    assert 0 <= dossier.nyxa_score.composite <= 100


def test_rfc_scan_preserves_grounded_analogy():
    extraction = {"project_name": "Fieldnote", "domain_keywords": ["architecture review"], "problem_signature": {
        "state_space": "ideas and evidence", "bottleneck_type": "late overlap discovery",
        "failure_mode": "duplicate implementation", "consistency_model": "evidence snapshot"}}
    with patch.object(orchestrator, "invoke_lite", return_value=json.dumps(extraction)), patch.object(orchestrator, "_ddb", None):
        initial = orchestrator.lambda_handler({"rfc_text": "Compare a proposal against public prior art", "scan_id": "rfc-1"}, None)
    pattern = {"pattern_id": "PAT-019", "source_domain": "Operations Research", "canonical_mechanism": "Bradley-Terry ranking",
               "mechanism": "Compare options pairwise.", "mapping_table": [{"source_primitive": "pairwise preference", "target_repo_module": "RFC", "expected_effect": "stable ranking"}],
               "expected_lift": "Estimated", "anti_pattern_warning": "Ranking depends on evidence quality.",
               "evidence": {"standard": "Bradley-Terry model", "reference_url": "https://example.org/bradley-terry", "measurement_status": "ESTIMATED"}, "similarity_score": 0.81}
    collision = {"traffic_light": "GREEN", "exact_matches": [], "fuzzy_matches": [], "phonetic_matches": [], "safe_alternatives": ["Fieldnote Atlas"]}
    landscape = {"direct_competitors": [], "academic_papers": [], "ecosystem_gaps": []}
    draft = {"kill_keep_inject": [], "ranked_backlog": [], "mermaid_before_after": "graph TD; A[RFC] --> B[Evidence]",
             "rubric": {key: 70 for key in ("clarity", "landscape_coverage", "originality", "gap_opportunity", "enhancement_potential", "evidence_quality")}}
    memory = MagicMock()
    memory.retrieve.return_value = []
    with patch.object(enhancement, "invoke_sonnet_json", return_value=draft), patch.object(enhancement, "_ddb", None), \
         patch.object(enhancement, "_s3", None), patch.object(enhancement, "SessionMemoryProvider", return_value=memory):
        final = enhancement.lambda_handler({**initial, "session_id": "session-rfc", "discovery": [
            {"repo_scan": initial["project_profile"]}, {"name_collision": collision}, {"landscape": landscape}, {"analogies": [pattern]}]}, None)
    dossier = EnhancementDossier.model_validate(final["dossier"])
    assert dossier.project_profile.input_type == "RFC_TEXT"
    assert dossier.project_profile.code_files_scanned == 0
    assert dossier.analogies[0].pattern_id == "PAT-019"


def test_rescan_computes_positive_parent_delta():
    profile = {"scan_id": "child", "input_type": "RFC_TEXT", "project_name": "Fieldnote", "domain_keywords": ["review"],
               "problem_signature": {"state_space": "ideas", "bottleneck_type": "overlap", "failure_mode": "duplication", "consistency_model": "snapshot"},
               "tech_stack": [], "dependencies": [], "core_modules": [], "has_tests": False, "readme_claims": [], "dependency_count": 0, "code_files_scanned": 0}
    collision = {"traffic_light": "GREEN", "exact_matches": [], "fuzzy_matches": [], "phonetic_matches": [], "safe_alternatives": []}
    draft = {"kill_keep_inject": [], "ranked_backlog": [], "mermaid_before_after": "graph TD; A[RFC] --> B[Evidence]",
             "rubric": {key: 100 for key in ("clarity", "landscape_coverage", "originality", "gap_opportunity", "enhancement_potential", "evidence_quality")}}
    table = MagicMock()
    table.get_item.return_value = {"Item": {"nyxa_score": {"composite": 64}}}
    memory = MagicMock()
    memory.retrieve.return_value = []
    with patch.object(enhancement, "invoke_sonnet_json", return_value=draft), patch.object(enhancement, "_ddb", table), \
         patch.object(enhancement, "_s3", None), patch.object(enhancement, "SessionMemoryProvider", return_value=memory):
        final = enhancement.lambda_handler({"scan_id": "child", "parent_scan_id": "parent", "project_profile": profile,
            "discovery": [{"repo_scan": profile}, {"name_collision": collision}, {"landscape": {"direct_competitors": [], "academic_papers": [], "ecosystem_gaps": []}}, {"analogies": []}]}, None)
    dossier = EnhancementDossier.model_validate(final["dossier"])
    assert dossier.score_delta is not None and dossier.score_delta > 0
