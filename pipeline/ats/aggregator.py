"""
Unified signal aggregation for ATS engine.

Takes all individual scored signals (with their confidences) and computes
a final weighted overall fit score and confidence score.
"""

from __future__ import annotations

from pipeline.ats.explainability import generate_explanations
from pipeline.ats.models import (
    AchievementResult,
    AtsScoreResponse,
    ConsistencyResult,
    DomainMatchResult,
    EducationResult,
    ExperienceResult,
    ParseabilityResult,
    RoleDetectionResult,
    ScoredSignal,
    SemanticChunkResult,
    SeniorityResult,
    SkillsResult,
)
from pipeline.ats.role_scorers import get_role_profile


def aggregate_signals(
    skills: SkillsResult,
    experience: ExperienceResult,
    education: EducationResult,
    achievements: AchievementResult,
    seniority: SeniorityResult,
    domain: DomainMatchResult,
    semantic: SemanticChunkResult | None,
    parseability: ParseabilityResult,
    consistency: ConsistencyResult,
    role_detection: RoleDetectionResult,
) -> AtsScoreResponse:
    """
    Aggregate all signals into a final score, weighted by confidence
    and role-specific importance.
    """
    profile = get_role_profile(role_detection.role)

    # 1. Define base signals and their configured importance from the role profile
    # If a signal is None (e.g. semantic), its weight is 0.
    signals: dict[str, ScoredSignal] = {
        "hard_skills": ScoredSignal(
            name="hard_skills",
            score=skills.hard_skills_score,
            confidence=skills.confidence,
            weight=profile.skills_importance,
        ),
        "experience": ScoredSignal(
            name="experience",
            score=experience.score,
            confidence=experience.confidence,
            weight=profile.experience_importance,
        ),
        "education": ScoredSignal(
            name="education",
            score=education.score,
            confidence=education.confidence,
            weight=profile.education_importance,
        ),
        "impact": ScoredSignal(
            name="impact",
            score=achievements.impact_score,
            confidence=achievements.confidence,
            weight=profile.impact_importance,
        ),
        "leadership": ScoredSignal(
            name="leadership",
            score=achievements.leadership_score,
            confidence=achievements.confidence,
            weight=profile.leadership_importance,
        ),
        "seniority": ScoredSignal(
            name="seniority",
            score=0.8 if seniority.level in ["senior", "staff", "principal"] else 0.5, # Simplified for aggregation
            confidence=seniority.confidence,
            weight=profile.seniority_importance,
        ),
        "domain": ScoredSignal(
            name="domain",
            score=domain.overlap_score,
            confidence=domain.confidence,
            weight=profile.domain_importance,
        ),
        "soft_skills": ScoredSignal(
            name="soft_skills",
            score=skills.soft_skills_score,
            confidence=skills.confidence,
            weight=profile.soft_skills_importance,
        ),
    }

    if semantic is not None:
        signals["semantic"] = ScoredSignal(
            name="semantic",
            score=semantic.overall_semantic_fit,
            confidence=semantic.confidence,
            weight=profile.semantic_importance,
        )

    # 2. Compute confidence-weighted sum
    total_weight = 0.0
    weighted_score_sum = 0.0
    confidence_sum = 0.0
    raw_weight_sum = 0.0

    for name, signal in signals.items():
        # Effective weight = base_weight * confidence
        # Low confidence signals naturally contribute less
        effective_weight = signal.weight * signal.confidence

        weighted_score_sum += signal.score * effective_weight
        total_weight += effective_weight
        
        confidence_sum += signal.confidence * signal.weight
        raw_weight_sum += signal.weight

    # Handle edge case where total_weight is 0 (all confidences 0)
    if total_weight > 0:
        overall_fit = weighted_score_sum / total_weight
    else:
        # Fallback to unweighted average of whatever scores we have
        scores = [s.score for s in signals.values()]
        overall_fit = sum(scores) / len(scores) if scores else 0.0

    # Overall raw confidence (weighted average of confidences)
    raw_confidence = confidence_sum / max(raw_weight_sum, 0.01)

    # Penalize confidence by consistency issues
    final_confidence = raw_confidence * consistency.consistency_score

    # Convert overall fit to 0-100 scale
    final_fit_score = min(100.0, max(0.0, overall_fit * 100.0))

    # Generate strengths and gaps
    strengths, gaps = generate_explanations(
        skills=skills,
        experience=experience,
        education=education,
        seniority=seniority,
        domain=domain,
        semantic=semantic,
        achievements=achievements,
        consistency=consistency,
        parseability=parseability,
    )

    # Convert keywords for backward compatibility
    matched_kws = [s.skill for s in skills.matched] if skills.matched else []
    missing_kws = [s.skill for s in skills.missing] if skills.missing else []

    return AtsScoreResponse(
        overall_fit_score=round(final_fit_score, 1),
        confidence_score=round(final_confidence, 3),
        top_strengths=strengths,
        top_gaps=gaps,
        
        # Categories
        hard_skills_score=round(skills.hard_skills_score, 3),
        soft_skills_score=round(skills.soft_skills_score, 3),
        role_match_score=0.8, # Hardcoded for now
        experience_score=round(experience.score, 3),
        education_score=round(education.score, 3),
        semantic_fit_score=round(semantic.overall_semantic_fit, 3) if semantic else None,
        impact_score=round(achievements.impact_score, 3),
        leadership_score=round(achievements.leadership_score, 3),
        seniority_match_score=0.8, # Simplified
        domain_match_score=round(domain.overlap_score, 3),
        consistency_score=round(consistency.consistency_score, 3),
        parseability_score=round(parseability.score, 3),

        # Details
        skills=skills,
        experience=experience,
        education=education,
        seniority=seniority,
        domain=domain,
        semantic=semantic,
        achievements=achievements,
        consistency=consistency,
        parseability=parseability,
        role_detection=role_detection,

        # Compat
        matched_keywords=matched_kws,
        missing_keywords=missing_kws,
        suggestions=gaps, # Map gaps to suggestions for old UI
        rewrite_suggestions=[], # Filled in by __init__.py
    )
