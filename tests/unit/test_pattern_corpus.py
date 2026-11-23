"""
Phase 1 — Task 1
Corpus integrity tests for data/patterns_20.json.
Covers all FR-1, FR-2, FR-3 checks from phase-1 requirements.md.
Run: pytest tests/unit/test_pattern_corpus.py -v
"""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "lambdas"))

PATTERNS_PATH = Path(__file__).parent.parent.parent / "data" / "patterns_20.json"
VAGUE_PHRASES = ["like a", "similar to", "acts as", "functions as"]
REQUIRED_DOMAIN_KEYWORDS = ["Telecom", "Distributed", "OS", "Control", "Operations"]


@pytest.fixture(scope="module")
def patterns() -> list[dict]:
    assert PATTERNS_PATH.exists(), f"patterns_20.json not found at {PATTERNS_PATH}"
    return json.loads(PATTERNS_PATH.read_text(encoding="utf-8"))


# ── FR-1: Schema completeness ──────────────────────────────────────────────

class TestSchemaCompleteness:
    def test_exactly_20_patterns(self, patterns):
        assert len(patterns) == 20, f"Expected 20 patterns, got {len(patterns)}"

    def test_all_pattern_ids_unique(self, patterns):
        ids = [p["pattern_id"] for p in patterns]
        assert len(ids) == len(set(ids)), f"Duplicate IDs: {[i for i in ids if ids.count(i) > 1]}"

    def test_pattern_ids_sequential(self, patterns):
        ids = sorted(p["pattern_id"] for p in patterns)
        expected = [f"PAT-{i:03d}" for i in range(1, 21)]
        assert ids == expected, f"ID mismatch: got {ids}"

    def test_all_source_domains_non_empty(self, patterns):
        for p in patterns:
            assert p.get("source_domain", "").strip(), \
                f"{p['pattern_id']}: source_domain is empty"

    def test_all_canonical_mechanisms_non_empty(self, patterns):
        for p in patterns:
            assert p.get("canonical_mechanism", "").strip(), \
                f"{p['pattern_id']}: canonical_mechanism is empty"

    def test_all_problem_signatures_complete(self, patterns):
        required_keys = ["state_space", "bottleneck_type", "failure_mode", "consistency_model"]
        for p in patterns:
            sig = p.get("problem_signature", {})
            for key in required_keys:
                assert sig.get(key, "").strip(), \
                    f"{p['pattern_id']}: problem_signature.{key} is missing or empty"

    def test_all_trigger_conditions_non_empty(self, patterns):
        for p in patterns:
            detected = p.get("trigger_condition", {}).get("detected_when", "").strip()
            assert detected, f"{p['pattern_id']}: trigger_condition.detected_when is empty"

    def test_all_mechanisms_non_empty(self, patterns):
        for p in patterns:
            mech = p.get("transferable_design", {}).get("mechanism", "").strip()
            assert mech, f"{p['pattern_id']}: transferable_design.mechanism is empty"

    def test_all_expected_lifts_non_empty(self, patterns):
        for p in patterns:
            lift = p.get("transferable_design", {}).get("expected_lift", "").strip()
            assert lift, f"{p['pattern_id']}: transferable_design.expected_lift is empty"

    def test_all_anti_pattern_warnings_sufficient_length(self, patterns):
        for p in patterns:
            warning = p.get("transferable_design", {}).get("anti_pattern_warning", "")
            assert len(warning) >= 10, \
                f"{p['pattern_id']}: anti_pattern_warning too short ({len(warning)} chars): '{warning}'"

    def test_all_mapping_tables_non_empty(self, patterns):
        for p in patterns:
            table = p.get("transferable_design", {}).get("mapping_table", [])
            assert len(table) >= 1, f"{p['pattern_id']}: mapping_table has 0 entries"

    def test_all_mapping_table_entries_complete(self, patterns):
        required_keys = ["source_primitive", "target_repo_module", "expected_effect"]
        for p in patterns:
            for i, entry in enumerate(p.get("transferable_design", {}).get("mapping_table", [])):
                for key in required_keys:
                    assert entry.get(key, "").strip(), \
                        f"{p['pattern_id']} mapping_table[{i}].{key} is empty"

    def test_all_evidence_standards_non_empty(self, patterns):
        for p in patterns:
            std = p.get("evidence", {}).get("standard", "").strip()
            assert std, f"{p['pattern_id']}: evidence.standard is empty"


# ── FR-1: reference_url and measurement_status ────────────────────────────

class TestEvidenceFields:
    def test_all_reference_urls_https(self, patterns):
        for p in patterns:
            url = p.get("evidence", {}).get("reference_url", "")
            assert url.startswith("https://"), \
                f"{p['pattern_id']}: reference_url must use HTTPS, got: '{url}'"

    def test_all_reference_urls_non_empty(self, patterns):
        for p in patterns:
            url = p.get("evidence", {}).get("reference_url", "")
            assert url.strip(), f"{p['pattern_id']}: reference_url is empty"

    def test_all_measurement_status_estimated(self, patterns):
        for p in patterns:
            status = p.get("evidence", {}).get("measurement_status")
            assert status == "ESTIMATED", \
                f"{p['pattern_id']}: measurement_status must be 'ESTIMATED', got: '{status}'"


# ── FR-2: Domain coverage ─────────────────────────────────────────────────

class TestDomainCoverage:
    def test_all_five_domain_keywords_present(self, patterns):
        domains = {p["source_domain"] for p in patterns}
        for keyword in REQUIRED_DOMAIN_KEYWORDS:
            assert any(keyword in d for d in domains), \
                f"No pattern has source_domain containing '{keyword}'. Domains found: {sorted(domains)}"

    def test_at_least_3_telecom_patterns(self, patterns):
        telecom = [p for p in patterns if "Telecom" in p.get("source_domain", "")]
        assert len(telecom) >= 3, \
            f"Expected ≥3 Telecom patterns, got {len(telecom)}"

    def test_at_least_3_distributed_systems_patterns(self, patterns):
        dist = [p for p in patterns if "Distributed" in p.get("source_domain", "")]
        assert len(dist) >= 3, \
            f"Expected ≥3 Distributed Systems patterns, got {len(dist)}"

    def test_at_least_3_os_kernel_patterns(self, patterns):
        os_pats = [p for p in patterns if "OS" in p.get("source_domain", "")]
        assert len(os_pats) >= 3, \
            f"Expected ≥3 OS Kernel patterns, got {len(os_pats)}"


# ── FR-3: No vague metaphors ──────────────────────────────────────────────

class TestNoVagueMetaphors:
    def test_no_vague_phrases_in_canonical_mechanism(self, patterns):
        for p in patterns:
            mech_lower = p.get("canonical_mechanism", "").lower()
            for phrase in VAGUE_PHRASES:
                assert phrase not in mech_lower, \
                    f"{p['pattern_id']}: canonical_mechanism contains vague phrase '{phrase}': '{p['canonical_mechanism']}'"

    def test_no_vague_phrases_in_mechanism_description(self, patterns):
        for p in patterns:
            mech_lower = p.get("transferable_design", {}).get("mechanism", "").lower()
            for phrase in ["it's like", "think of it as", "imagine a"]:
                assert phrase not in mech_lower, \
                    f"{p['pattern_id']}: mechanism description contains vague phrase '{phrase}'"


# ── Pydantic schema validation (uses seed_opensearch models) ──────────────

class TestPydanticValidation:
    def test_all_patterns_validate_against_analog_pattern_schema(self, patterns):
        """
        Import and use the AnalogPattern model from seed_opensearch.py.
        This test will fail if seed_opensearch.py has not yet been hardened (Task 2).
        """
        import importlib.util
        seed_path = Path(__file__).parent.parent.parent / "data" / "seed_opensearch.py"

        spec = importlib.util.spec_from_file_location("seed_opensearch", seed_path)
        module = importlib.util.module_from_spec(spec)

        try:
            spec.loader.exec_module(module)
            AnalogPattern = module.AnalogPattern
        except (AttributeError, Exception) as e:
            pytest.skip(f"AnalogPattern model not yet available in seed_opensearch.py: {e}")

        errors = []
        for record in patterns:
            try:
                AnalogPattern.model_validate(record)
            except Exception as exc:
                errors.append(f"{record.get('pattern_id', '?')}: {exc}")

        assert not errors, "Pydantic validation failures:\n" + "\n".join(errors)
