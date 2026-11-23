"""
NyxaLensAI — Shared Pydantic v2 Schemas
All inter-subagent data contracts. Validated at every Lambda boundary.
"""
from __future__ import annotations

from typing import Literal, Optional
from pydantic import BaseModel, Field, field_validator


# ── Input ──────────────────────────────────────────────────────────────────

class ScanRequest(BaseModel):
    repo_url: Optional[str] = Field(None, description="Public GitHub repository URL")
    rfc_text: Optional[str] = Field(None, max_length=8000, description="Markdown RFC or idea text")
    parent_scan_id: Optional[str] = Field(None, description="ID of prior scan for delta comparison")
    force_refresh: bool = Field(False, description="Bypass 24-hour DynamoDB cache")

    @field_validator("repo_url", "rfc_text", mode="before")
    @classmethod
    def at_least_one(cls, v, info):
        return v

    def model_post_init(self, __context) -> None:
        if not self.repo_url and not self.rfc_text:
            raise ValueError("Provide either repo_url or rfc_text.")


# ── Stage 1: Orchestrator output ───────────────────────────────────────────

class ProblemSignature(BaseModel):
    state_space: str
    bottleneck_type: str
    failure_mode: str
    consistency_model: str


class UniversalProjectProfile(BaseModel):
    scan_id: str
    input_type: Literal["GITHUB_URL", "RFC_TEXT"]
    project_name: str
    domain_keywords: list[str]
    problem_signature: ProblemSignature
    tech_stack: list[str] = Field(default_factory=list)
    dependencies: list[str] = Field(default_factory=list)
    core_modules: list[str] = Field(default_factory=list)
    has_tests: bool = False
    readme_claims: list[str] = Field(default_factory=list)
    dependency_count: int = 0
    code_files_scanned: int = 0


# ── Stage 2: Discovery lane outputs ───────────────────────────────────────

class NameCollisionResult(BaseModel):
    traffic_light: Literal["RED", "YELLOW", "GREEN"]
    exact_matches: list[str] = Field(default_factory=list)
    fuzzy_matches: list[str] = Field(default_factory=list)
    phonetic_matches: list[str] = Field(default_factory=list)
    safe_alternatives: list[str] = Field(default_factory=list)
    status: str = "OK"
    registries_checked: list[str] = Field(default_factory=list)


class CompetitorEntry(BaseModel):
    name: str
    url: str
    stars: Optional[int] = None
    description: Optional[str] = None
    limitations: Optional[str] = None


class AcademicPaper(BaseModel):
    title: str
    url: str
    abstract_snippet: Optional[str] = None


class LandscapeResult(BaseModel):
    direct_competitors: list[CompetitorEntry] = Field(default_factory=list)
    academic_papers: list[AcademicPaper] = Field(default_factory=list)
    ecosystem_gaps: list[str] = Field(default_factory=list)
    notable_discussions: list[str] = Field(default_factory=list)


# ── Pattern evidence (shared by pattern corpus and analogy output) ─────────

class PatternEvidence(BaseModel):
    standard: str
    reference_url: str
    measurement_status: Literal["ESTIMATED", "BENCHMARKED"] = "ESTIMATED"


class MappingTableEntry(BaseModel):
    source_primitive: str
    target_repo_module: str
    expected_effect: str


class AnalogyMatch(BaseModel):
    pattern_id: str
    source_domain: str
    canonical_mechanism: str
    mechanism: str
    mapping_table: list[MappingTableEntry]
    expected_lift: str
    anti_pattern_warning: str
    evidence: PatternEvidence
    similarity_score: float = Field(ge=0.0, le=1.0)


# ── Stage 3: Enhancement + Citation output ─────────────────────────────────

class KillKeepInjectItem(BaseModel):
    action: Literal["KILL", "KEEP", "INJECT"]
    target_component: str
    rationale: str
    citation_url: Optional[str] = None


class BacklogItem(BaseModel):
    rank: int
    title: str
    description: str
    effort: Literal["LOW", "MEDIUM", "HIGH"]
    impact: Literal["LOW", "MEDIUM", "HIGH", "VERY HIGH"]
    citation_url: Optional[str] = None


class NyxaScore(BaseModel):
    composite: int = Field(ge=0, le=100)
    clarity: int = Field(ge=0, le=100)
    landscape_coverage: int = Field(ge=0, le=100)
    originality: int = Field(ge=0, le=100)
    gap_opportunity: int = Field(ge=0, le=100)
    enhancement_potential: int = Field(ge=0, le=100)
    evidence_quality: int = Field(ge=0, le=100)
    deterministic_points: int = Field(ge=0, le=40)
    rubric_points: int = Field(ge=0, le=60)
    projected_post_enhancement: int = Field(ge=0, le=100)
    verdict: str


class PipelineTrace(BaseModel):
    subagent: str
    duration_ms: int
    model_id: str
    input_tokens: int
    output_tokens: int
    estimated_usd: float
    citations_verified: int = 0
    citations_stripped: int = 0


class EnhancementDossier(BaseModel):
    scan_id: str
    parent_scan_id: Optional[str] = None
    score_delta: Optional[int] = None
    project_profile: UniversalProjectProfile
    name_collision: NameCollisionResult
    landscape: LandscapeResult
    analogies: list[AnalogyMatch]
    kill_keep_inject: list[KillKeepInjectItem]
    ranked_backlog: list[BacklogItem]
    mermaid_before_after: str
    nyxa_score: NyxaScore
    verified_citations_count: int = 0
    stripped_hallucinations_count: int = 0
    pipeline_trace: list[PipelineTrace] = Field(default_factory=list)
    disclaimer: str = (
        "Architectural lift projections are domain-derived estimates, "
        "not empirical repo benchmarks."
    )
