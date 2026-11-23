"""Mocked unit coverage for each Phase 2 pipeline handler."""
from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "lambdas"))

import orchestrator.handler as orchestrator
import repo_scanner.handler as repo_scanner
import name_collision.handler as name_collision
import landscape_scout.handler as landscape_scout
import analogy_engine.handler as analogy_engine
import enhancement_citation.handler as enhancement


def profile(**changes):
    value = {
        "scan_id": "scan-1", "input_type": "GITHUB_URL", "project_name": "NyxaLens",
        "domain_keywords": ["repo architecture"],
        "problem_signature": {"state_space": "repo modules", "bottleneck_type": "duplicate work",
                              "failure_mode": "parallel reinvention", "consistency_model": "eventual"},
    }
    value.update(changes)
    return value


def test_orchestrator_extracts_profile_and_updates_status():
    response = {"project_name": "NyxaLens", "domain_keywords": ["architecture"],
                "problem_signature": {"state_space": "repositories", "bottleneck_type": "duplication",
                                      "failure_mode": "duplicate builds", "consistency_model": "eventual"}}
    with patch.object(orchestrator, "invoke_lite", return_value=json.dumps(response)), \
         patch.object(orchestrator, "_ddb") as table:
        result = orchestrator.lambda_handler({"rfc_text": "An architectural review tool", "scan_id": "s1"}, None)
    assert result["project_profile"]["project_name"] == "NyxaLens"
    assert result["project_profile"]["input_type"] == "RFC_TEXT"
    table.update_item.assert_called_once()


def test_repo_scanner_parses_python_and_manifest():
    tree = {"tree": [{"path": p, "type": "blob"} for p in ("README.md", "pyproject.toml", "src/app.py", "tests/test_app.py")]}
    contents = {"README.md": "# Repo\n- architecture analysis", "pyproject.toml": "[project]\ndependencies=['httpx>=0.2']",
                "src/app.py": "import ast\nclass Scanner:\n def scan(self): pass", "tests/test_app.py": "def test_ok(): pass"}
    with patch.object(repo_scanner, "get_repo_tree", return_value=tree), \
         patch.object(repo_scanner, "get_file_content", side_effect=lambda owner, repo, path: contents[path]):
        result = repo_scanner.lambda_handler({"repo_url": "https://github.com/acme/sample", "project_profile": profile()}, None)
    scanned = result["repo_scan"]
    assert scanned["tech_stack"] == ["Python"]
    assert scanned["has_tests"] is True
    assert scanned["dependencies"] == ["httpx"]
    assert any(module.endswith(":Scanner") for module in scanned["core_modules"])


def test_repo_scanner_caps_large_monorepo_at_40_code_files():
    paths = ["README.md"] + [f"packages/pkg{i}/src/module.py" for i in range(600)]
    calls = []
    def read_file(owner, repo, path):
        calls.append(path)
        return "def module(): pass" if path != "README.md" else "# Large repo"
    with patch.object(repo_scanner, "get_repo_tree", return_value={"tree": [{"path": p, "type": "blob"} for p in paths]}), \
         patch.object(repo_scanner, "get_file_content", side_effect=read_file):
        result = repo_scanner.lambda_handler({"repo_url": "https://github.com/acme/mono", "project_profile": profile()}, None)
    assert result["repo_scan"]["code_files_scanned"] == 40
    assert sum(path.endswith(".py") for path in calls) == 40


def test_name_collision_uses_red_threshold_and_alternatives():
    async def lookup(_):
        return ([{"name": "NyxaLens", "url": "https://github.com/acme/nyxalens", "source": "github"}], False)
    with patch.object(name_collision, "_lookup", side_effect=lookup), \
         patch.object(name_collision, "_double_metaphone", return_value={"NKS"}):
        result = name_collision.lambda_handler({"project_profile": profile()}, None)["name_collision"]
    assert result["traffic_light"] == "RED"
    assert len(result["safe_alternatives"]) == 3


def test_landscape_scout_collects_competitors_and_papers():
    repo = {"full_name": "acme/tool", "name": "tool", "owner": {"login": "acme"},
            "html_url": "https://github.com/acme/tool", "stargazers_count": 20, "description": "Tool"}
    with patch.object(landscape_scout, "_queries", return_value=["architecture reuse"]), \
         patch.object(landscape_scout, "search_repos", return_value=[repo]), \
         patch.object(landscape_scout, "get_file_content", return_value="## Limitations\n- Public repos only"), \
         patch.object(landscape_scout, "_arxiv", return_value=[{"title": "Paper", "url": "https://arxiv.org/abs/1", "abstract_snippet": "Abstract"}]):
        result = landscape_scout.lambda_handler({"project_profile": profile()}, None)["landscape"]
    assert result["direct_competitors"][0]["limitations"] == "- Public repos only"
    assert result["academic_papers"][0]["title"] == "Paper"


def test_analogy_engine_uses_local_cosine_fallback(tmp_path):
    record = {"pattern_id": "PAT-001", "source_domain": "Telecom", "canonical_mechanism": "Circuit breaker",
              "mechanism": "Open circuit after repeated failures", "mapping_table": [{"source_primitive": "alarm", "target_repo_module": "worker", "expected_effect": "stops retries"}],
              "expected_lift": "estimated", "anti_pattern_warning": "Avoid on normal retries.",
              "evidence": {"standard": "RFC", "reference_url": "https://example.com/rfc", "measurement_status": "ESTIMATED"}}
    embedded = tmp_path / "patterns.json"
    embedded.write_text(json.dumps([{"pattern_id": "PAT-001", "embedding": [1.0, 0.0], "record": record}]))
    with patch.object(analogy_engine, "LOCAL_EMBEDDED", embedded), \
         patch.object(analogy_engine, "_query_text", return_value="repeated failures"), \
         patch.object(analogy_engine, "embed", return_value=[1.0, 0.0]), \
         patch.object(analogy_engine, "AOSS_ENDPOINT", ""):
        result = analogy_engine.lambda_handler({"project_profile": profile()}, None)["analogies"]
    assert result[0]["pattern_id"] == "PAT-001"
    assert result[0]["similarity_score"] == 1.0


def test_enhancement_strips_unverified_citations_and_sanitizes_mermaid():
    draft = {"kill_keep_inject": [{"action": "KEEP", "target_component": "scanner", "rationale": "Useful", "citation_url": "https://evil.example/fake"}],
             "ranked_backlog": [], "mermaid_before_after": 'graph TD; A[before (old)] --> B["after"]',
             "rubric": {key: 70 for key in ("clarity", "landscape_coverage", "originality", "gap_opportunity", "enhancement_potential", "evidence_quality")}}
    lanes = [{"repo_scan": profile()}, {"name_collision": {"traffic_light": "GREEN"}},
             {"landscape": {"direct_competitors": [{"name": "Tool", "url": "https://github.com/acme/tool"}], "academic_papers": [], "ecosystem_gaps": []}},
             {"analogies": []}]
    with patch.object(enhancement, "invoke_sonnet_json", return_value=draft), patch.object(enhancement, "_ddb", None), patch.object(enhancement, "_s3", None):
        result = enhancement.lambda_handler({"scan_id": "s1", "project_profile": profile(), "discovery": lanes}, None)
    dossier = result["dossier"]
    assert dossier["stripped_hallucinations_count"] == 1
    assert "(" not in dossier["mermaid_before_after"] and '"' not in dossier["mermaid_before_after"]
    assert 0 <= dossier["nyxa_score"]["composite"] <= 100
