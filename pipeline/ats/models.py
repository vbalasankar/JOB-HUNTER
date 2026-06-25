"""
Pydantic models for the ATS engine.

Every extracted signal carries a confidence value (0.0–1.0) so the
aggregator can weight trustworthy signals higher and propagate
uncertainty honestly.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Generic, Optional, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


# ── Core confidence wrapper ──────────────────────────────────────────


@dataclass
class ConfidentValue(Generic[T]):
    """A value paired with extraction confidence and evidence."""

    value: T
    confidence: float = 0.0  # 0.0–1.0
    evidence: list[str] = field(default_factory=list)
    method: str = "unknown"  # regex | semantic | ontology | heuristic | date_range_analysis


# ── Skill matching ───────────────────────────────────────────────────


class SkillMatch(BaseModel):
    """A single skill extracted from the JD, with match status against the resume."""

    skill: str
    category: str = "hard_skill"  # hard_skill | soft_skill | tool | certification | methodology | language
    matched: bool = False
    match_type: str = "none"  # exact | alias | child_to_parent | semantic | noun_phrase | none
    confidence: float = 0.0
    jd_section: str = "requirement"  # requirement | responsibility | nice_to_have | fluff
    jd_weight: float = 1.0  # 1.0 for required, 0.5 for nice-to-have, 0.0 for fluff
    importance: int = 5  # 1–10 dynamic weight
    credit: float = 0.0  # 0.0–1.0, partial credit for child_to_parent
    evidence_resume: Optional[str] = None
    evidence_jd: Optional[str] = None
    parent_skill: Optional[str] = None  # For child_to_parent matches
    children_matched: list[str] = Field(default_factory=list)  # Children that contributed


class SkillsResult(BaseModel):
    """Aggregated skill matching result."""

    hard_skills_score: float = 0.0
    soft_skills_score: float = 0.0
    tools_score: float = 0.0
    overall_skills_score: float = 0.0
    confidence: float = 0.0
    matched: list[SkillMatch] = Field(default_factory=list)
    missing: list[SkillMatch] = Field(default_factory=list)
    all_skills: list[SkillMatch] = Field(default_factory=list)


# ── Experience ───────────────────────────────────────────────────────


class ExperienceResult(BaseModel):
    """Experience extraction and comparison result."""

    jd_required_years: Optional[float] = None
    jd_years_confidence: float = 0.0
    jd_years_evidence: list[str] = Field(default_factory=list)
    resume_years: Optional[float] = None
    resume_years_confidence: float = 0.0
    resume_years_evidence: list[str] = Field(default_factory=list)
    score: float = 0.5
    confidence: float = 0.0
    detail: str = ""


# ── Education ────────────────────────────────────────────────────────


class EducationResult(BaseModel):
    """Education extraction and comparison result."""

    jd_required_level: Optional[str] = None  # phd | master | bachelor | associate | certificate
    jd_level_confidence: float = 0.0
    jd_level_evidence: list[str] = Field(default_factory=list)
    jd_is_preferred: bool = False  # "preferred" vs "required"
    resume_level: Optional[str] = None
    resume_level_confidence: float = 0.0
    resume_level_evidence: list[str] = Field(default_factory=list)
    resume_field: Optional[str] = None  # "Computer Science", "Mathematics", etc.
    score: float = 0.5
    confidence: float = 0.0
    detail: str = ""


# ── Seniority ────────────────────────────────────────────────────────


class SeniorityResult(BaseModel):
    """Candidate seniority inference result."""

    level: str = "mid"  # intern | junior | mid | senior | staff | principal
    confidence: float = 0.0
    signals: list[str] = Field(default_factory=list)
    trajectory: Optional[str] = None  # "positive" | "lateral" | "concern" | None
    trajectory_detail: Optional[str] = None
    stability_note: Optional[str] = None


# ── Domain ───────────────────────────────────────────────────────────


class DomainMatchResult(BaseModel):
    """Domain matching result between JD and resume."""

    jd_domains: list[str] = Field(default_factory=list)
    resume_domains: list[str] = Field(default_factory=list)
    overlap_score: float = 0.0
    confidence: float = 0.0
    detail: str = ""


# ── Semantic chunks ──────────────────────────────────────────────────


class SemanticChunkResult(BaseModel):
    """Chunk-level semantic similarity between resume and JD sections."""

    skills_vs_requirements: float = 0.0
    experience_vs_responsibilities: float = 0.0
    projects_vs_requirements: float = 0.0
    summary_vs_requirements: float = 0.0
    overall_semantic_fit: float = 0.0
    confidence: float = 0.0  # 0.95 if embeddings available, 0.0 if fallback


# ── Achievements ─────────────────────────────────────────────────────


class AchievementResult(BaseModel):
    """Achievement extraction result from resume."""

    impact_score: float = 0.0
    leadership_score: float = 0.0
    ownership_score: float = 0.0
    achievements: list[str] = Field(default_factory=list)
    metrics_found: list[str] = Field(default_factory=list)
    leadership_signals: list[str] = Field(default_factory=list)
    weak_verbs_found: list[str] = Field(default_factory=list)
    confidence: float = 0.0


# ── Consistency ──────────────────────────────────────────────────────


class ConsistencyResult(BaseModel):
    """Contradiction detection result."""

    consistency_score: float = 1.0  # 1.0 = no contradictions
    flags: list[str] = Field(default_factory=list)
    confidence: float = 0.0


# ── Parseability ─────────────────────────────────────────────────────


class ParseabilityResult(BaseModel):
    """Resume structure and ATS parseability scoring."""

    score: float = 0.0
    has_skills_section: bool = False
    has_experience_section: bool = False
    has_education_section: bool = False
    has_summary_section: bool = False
    has_contact_info: bool = False
    has_quantified_achievements: bool = False
    has_chronological_dates: bool = False
    word_count: int = 0
    density_rating: str = "unknown"  # sparse | good | dense
    recommendations: list[str] = Field(default_factory=list)


# ── Rewrite suggestions ─────────────────────────────────────────────


class RewriteSuggestion(BaseModel):
    """A single actionable ATS optimization recommendation."""

    category: str  # missing_parent_skill | missing_years | weak_verb | ...
    priority: str = "important"  # critical | important | nice_to_have
    current_text: Optional[str] = None
    suggestion: str = ""
    reasoning: str = ""


# ── Role detection ───────────────────────────────────────────────────


class RoleDetectionResult(BaseModel):
    """Detected role archetype from the JD."""

    role: str = "general"  # backend | frontend | data | devops | ml | product | general
    confidence: float = 0.0
    matched_patterns: list[str] = Field(default_factory=list)


# ── Aggregated signal ────────────────────────────────────────────────


class ScoredSignal(BaseModel):
    """A single scored signal for the aggregator."""

    name: str
    score: float = 0.0
    confidence: float = 0.0
    weight: float = 0.0


# ── Final response ───────────────────────────────────────────────────


class AtsScoreResponse(BaseModel):
    """Complete ATS analysis response."""

    # Primary outputs (what the UI emphasizes)
    overall_fit_score: float = 0.0  # 0–100
    confidence_score: float = 0.0  # 0.0–1.0
    top_strengths: list[str] = Field(default_factory=list)
    top_gaps: list[str] = Field(default_factory=list)

    # Category scores (secondary, expandable in UI)
    hard_skills_score: float = 0.0
    soft_skills_score: float = 0.0
    role_match_score: float = 0.0
    experience_score: float = 0.0
    education_score: float = 0.0
    semantic_fit_score: Optional[float] = None
    impact_score: float = 0.0
    leadership_score: float = 0.0
    seniority_match_score: float = 0.0
    domain_match_score: float = 0.0
    consistency_score: float = 1.0
    parseability_score: float = 0.0

    # Detailed breakdowns
    skills: Optional[SkillsResult] = None
    experience: Optional[ExperienceResult] = None
    education: Optional[EducationResult] = None
    seniority: Optional[SeniorityResult] = None
    domain: Optional[DomainMatchResult] = None
    semantic: Optional[SemanticChunkResult] = None
    achievements: Optional[AchievementResult] = None
    consistency: Optional[ConsistencyResult] = None
    parseability: Optional[ParseabilityResult] = None
    role_detection: Optional[RoleDetectionResult] = None

    # Actionable output
    rewrite_suggestions: list[RewriteSuggestion] = Field(default_factory=list)
    suggestions: list[str] = Field(default_factory=list)  # Legacy compat

    # Keyword lists (backward compat)
    matched_keywords: list[str] = Field(default_factory=list)
    missing_keywords: list[str] = Field(default_factory=list)
