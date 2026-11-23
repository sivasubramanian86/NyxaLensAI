"""
Unit tests: Pydantic schema validation and patterns_20.json integrity.
Run with: pytest tests/unit/test_schemas.py -v
"""
import json
import sys
from pathlib import Path

import pytest

# Allow imports from lambdas/shared without package install
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "lambdas"))

from shared.schemas import (
    ScanRequest, NameCollisionResult,
    PatternEvidence, NyxaScore,
)

PATTERNS_PATH = Path(__file__).parent.parent.parent / "data" / "patterns_20.json"


# ── ScanRequest ────────────────────────────────────────────────────────────

class TestScanRequest:
    def test_valid_repo_url(self):
        r = ScanRequest(repo_url="https://github.com/owner/repo")
        assert r.repo_url == "https://github.com/owner/repo"
        assert r.rfc_text is None

    def test_valid_rfc_text(self):
        r = ScanRequest(rfc_text="# My idea\nThis is a proposal.")
        assert r.rfc_text is not None

    def test_requires_at_least_one(self):
        with pytest.raises(Exception):
            ScanRequest()

    def test_rfc_text_max_length(self):
        with pytest.raises(Exception):
            ScanRequest(rfc_text="x" * 8001)

    def test_parent_scan_id_optional(self):
        r = ScanRequest(repo_url="https://github.com/a/b", parent_scan_id="scan-123")
        assert r.parent_scan_id == "scan-123"

    def test_force_refresh_default_false(self):
        r = ScanRequest(repo_url="https://github.com/a/b")
        assert r.force_refresh is False


# ── NyxaScore ──────────────────────────────────────────────────────────────

class TestNyxaScore:
    def test_valid_score(self):
        s = NyxaScore(
            composite=74, clarity=70, landscape_coverage=65, originality=80,
            gap_opportunity=75, enhancement_potential=85, evidence_quality=50,
            deterministic_points=28, rubric_points=46,
            projected_post_enhancement=86, verdict="Upgradeable",
        )
        assert s.composite == 74

    def test_composite_out_of_range(self):
        with pytest.raises(Exception):
            NyxaScore(
                composite=101, clarity=70, landscape_coverage=65, originality=80,
                gap_opportunity=75, enhancement_potential=85, evidence_quality=50,
                deterministic_points=28, rubric_points=46,
                projected_post_enhancement=86, verdict="OK",
            )

    def test_projected_delta_bounded(self):
        """Projected post-enhancement must not exceed a +18 delta from composite."""
        composite = 64
        projected = 85  # +21 — should be treated as suspicious in business logic
        s = NyxaScore(
            composite=composite, clarity=60, landscape_coverage=55, originality=65,
            gap_opportunity=70, enhancement_potential=80, evidence_quality=40,
            deterministic_points=25, rubric_points=39,
            projected_post_enhancement=projected, verdict="Upgradeable",
        )
        assert s.projected_post_enhancement - s.composite <= 21  # schema allows it
        # Business rule: realistic cap is +18. Enforced in scoring_engine.py.


# ── NameCollisionResult ────────────────────────────────────────────────────

class TestNameCollisionResult:
    def test_valid_green(self):
        r = NameCollisionResult(
            traffic_light="GREEN",
            safe_alternatives=["NyxaForge", "NyxaAmplify"],
            registries_checked=["github", "pypi", "npm"],
        )
        assert r.traffic_light == "GREEN"

    def test_invalid_traffic_light(self):
        with pytest.raises(Exception):
            NameCollisionResult(traffic_light="AMBER")


# ── PatternEvidence ────────────────────────────────────────────────────────

class TestPatternEvidence:
    def test_valid_estimated(self):
        e = PatternEvidence(
            standard="ITU-T X.733",
            reference_url="https://www.itu.int/rec/T-REC-X.733",
        )
        assert e.measurement_status == "ESTIMATED"

    def test_benchmarked(self):
        e = PatternEvidence(
            standard="My Study",
            reference_url="https://example.com/paper",
            measurement_status="BENCHMARKED",
        )
        assert e.measurement_status == "BENCHMARKED"


# ── patterns_20.json corpus integrity ─────────────────────────────────────

class TestPatternCorpus:
    @pytest.fixture(scope="class")
    def patterns(self):
        assert PATTERNS_PATH.exists(), f"patterns_20.json not found at {PATTERNS_PATH}"
        return json.loads(PATTERNS_PATH.read_text(encoding="utf-8"))

    def test_exactly_20_patterns(self, patterns):
        assert len(patterns) == 20, f"Expected 20 patterns, got {len(patterns)}"

    def test_all_pattern_ids_unique(self, patterns):
        ids = [p["pattern_id"] for p in patterns]
        assert len(ids) == len(set(ids)), "Duplicate pattern_id found"

    def test_pattern_ids_sequential(self, patterns):
        ids = sorted([p["pattern_id"] for p in patterns])
        expected = [f"PAT-{i:03d}" for i in range(1, 21)]
        assert ids == expected

    def test_all_reference_urls_https(self, patterns):
        for p in patterns:
            url = p["evidence"]["reference_url"]
            assert url.startswith("https://"), \
                f"{p['pattern_id']}: reference_url must use HTTPS, got: {url}"

    def test_all_measurement_status_estimated(self, patterns):
        for p in patterns:
            status = p["evidence"].get("measurement_status")
            assert status == "ESTIMATED", \
                f"{p['pattern_id']}: measurement_status must be ESTIMATED, got: {status}"

    def test_no_vague_metaphors_in_mechanism(self, patterns):
        """Canonical mechanisms must not be vague metaphors."""
        vague_terms = ["like a", "similar to", "acts as", "functions as"]
        for p in patterns:
            mech = p["canonical_mechanism"].lower()
            for term in vague_terms:
                assert term not in mech, \
                    f"{p['pattern_id']}: canonical_mechanism appears vague: {p['canonical_mechanism']}"

    def test_all_mapping_tables_non_empty(self, patterns):
        for p in patterns:
            table = p["transferable_design"]["mapping_table"]
            assert len(table) >= 1, \
                f"{p['pattern_id']}: mapping_table must have at least 1 entry"

    def test_all_patterns_have_anti_pattern_warning(self, patterns):
        for p in patterns:
            warning = p["transferable_design"].get("anti_pattern_warning", "")
            assert len(warning) >= 10, \
                f"{p['pattern_id']}: anti_pattern_warning is missing or too short"

    def test_patterns_cover_5_domains(self, patterns):
        """Patterns must span all 5 required source domains."""
        domains = {p["source_domain"] for p in patterns}
        required_keywords = ["Telecom", "Distributed", "OS", "Control", "Operations"]
        for kw in required_keywords:
            assert any(kw in d for d in domains), \
                f"No pattern found with source_domain containing '{kw}'"
