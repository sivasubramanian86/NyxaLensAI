"""Ensure curated offline demo dossiers remain valid and score-bounded."""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "lambdas"))

from shared.schemas import EnhancementDossier


def test_all_three_offline_demo_dossiers_validate():
    fixtures = sorted((Path(__file__).parent.parent / "fixtures").glob("fixture-*/dossier.json"))
    assert {path.parent.name for path in fixtures} == {
        "fixture-a-python-agent", "fixture-b-typescript-app", "fixture-c-markdown-rfc"
    }
    for path in fixtures:
        dossier = EnhancementDossier.model_validate(json.loads(path.read_text(encoding="utf-8")))
        assert 0 <= dossier.nyxa_score.composite <= 100
        assert dossier.pipeline_trace
        score = dossier.nyxa_score
        rubric = round((score.clarity * 15 + score.landscape_coverage * 15 + score.originality * 25
                        + score.gap_opportunity * 15 + score.enhancement_potential * 20
                        + score.evidence_quality * 10) / 100)
        assert score.rubric_points == round(rubric * 0.6)
        assert score.composite == score.deterministic_points + score.rubric_points
