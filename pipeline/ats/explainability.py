"""
Recruiter-grade explanations and contextual skill gap analysis.

Generates human-readable positive factors, negative factors,
and contextual skill gap explanations that reference ontology
relationships and actual resume evidence.
"""

from __future__ import annotations

from pipeline.ats.models import (
    AchievementResult,
    AtsScoreResponse,
    ConsistencyResult,
    DomainMatchResult,
    EducationResult,
    ExperienceResult,
    ParseabilityResult,
    SemanticChunkResult,
    SeniorityResult,
    SkillMatch,
    SkillsResult,
)
from pipeline.ats.taxonomy import get_children_of, get_parent_of


def generate_explanations(
    skills: SkillsResult | None,
    experience: ExperienceResult | None,
    education: EducationResult | None,
    seniority: SeniorityResult | None,
    domain: DomainMatchResult | None,
    semantic: SemanticChunkResult | None,
    achievements: AchievementResult | None,
    consistency: ConsistencyResult | None,
    parseability: ParseabilityResult | None,
) -> tuple[list[str], list[str]]:
    """
    Generate top_strengths and top_gaps from all scored signals.

    Returns (strengths, gaps) — each list max 5 items, sorted by impact.
    """
    strengths: list[tuple[float, str]] = []  # (priority, text)
    gaps: list[tuple[float, str]] = []

    # ── Skills ───────────────────────────────────────────────────
    if skills:
        matched_required = [
            s for s in (skills.matched or [])
            if s.jd_section == "requirement" and s.matched
        ]
        total_required = [
            s for s in (skills.all_skills or [])
            if s.jd_section == "requirement"
        ]
        missing_required = [
            s for s in (skills.missing or [])
            if s.jd_section == "requirement"
        ]

        if total_required:
            pct = len(matched_required) / len(total_required)
            if pct >= 0.8:
                strengths.append((
                    10,
                    f"Matched {len(matched_required)}/{len(total_required)} required skills ({pct:.0%}) — strong technical alignment"
                ))
            elif pct >= 0.5:
                gaps.append((
                    6,
                    f"Matched only {len(matched_required)}/{len(total_required)} required skills ({pct:.0%}) — several gaps to address"
                ))
            else:
                gaps.append((
                    10,
                    f"Matched only {len(matched_required)}/{len(total_required)} required skills ({pct:.0%}) — significant skill gaps"
                ))

        # Top missing required skills
        for skill in (missing_required or [])[:3]:
            if skill.importance >= 7:
                gaps.append((
                    skill.importance,
                    f"Missing '{skill.skill}' — listed as a requirement (importance: {skill.importance}/10)"
                ))

    # ── Experience ───────────────────────────────────────────────
    if experience:
        if experience.score >= 0.85 and experience.resume_years is not None:
            strengths.append((8, experience.detail))
        elif experience.score <= 0.5:
            gaps.append((8, experience.detail))

    # ── Education ────────────────────────────────────────────────
    if education:
        if education.score >= 0.9:
            strengths.append((5, education.detail))
        elif education.score <= 0.5:
            gaps.append((5, education.detail))

    # ── Seniority ────────────────────────────────────────────────
    if seniority and seniority.confidence >= 0.5:
        if seniority.trajectory == "positive":
            strengths.append((4, "Positive career trajectory — consistent upward progression"))
        elif seniority.trajectory == "concern":
            gaps.append((3, seniority.trajectory_detail or "Potential career trajectory concern"))

    # ── Domain ───────────────────────────────────────────────────
    if domain:
        if domain.overlap_score >= 0.9:
            strengths.append((
                5,
                f"Direct domain match: {', '.join(domain.jd_domains[:3])}"
            ))
        elif domain.overlap_score <= 0.4 and domain.jd_domains:
            gaps.append((
                4,
                f"No domain overlap — JD targets {', '.join(domain.jd_domains[:3])}"
            ))

    # ── Semantic ─────────────────────────────────────────────────
    if semantic and semantic.confidence > 0:
        if semantic.overall_semantic_fit >= 0.75:
            strengths.append((
                6,
                f"Strong semantic alignment ({semantic.overall_semantic_fit:.0%}) — resume language closely matches JD"
            ))

    # ── Achievements ─────────────────────────────────────────────
    if achievements:
        if achievements.impact_score >= 0.7 and len(achievements.achievements) >= 2:
            strengths.append((
                6,
                f"{len(achievements.achievements)} quantified achievements demonstrate measurable impact"
            ))
        elif achievements.impact_score < 0.3:
            gaps.append((
                5,
                "No quantified achievements detected — add metrics (%, $, users) to demonstrate impact"
            ))

        if achievements.leadership_score >= 0.6:
            strengths.append((4, "Strong leadership signals detected"))

    # ── Consistency ──────────────────────────────────────────────
    if consistency and consistency.flags:
        for flag in consistency.flags[:2]:
            gaps.append((3, flag))

    # ── Parseability ─────────────────────────────────────────────
    if parseability and parseability.score < 0.5:
        gaps.append((
            4,
            "Resume structure needs improvement for ATS parsing — missing key sections"
        ))

    # Sort by priority (descending) and take top 5
    strengths.sort(key=lambda x: x[0], reverse=True)
    gaps.sort(key=lambda x: x[0], reverse=True)

    return (
        [s[1] for s in strengths[:5]],
        [g[1] for g in gaps[:5]],
    )


def generate_skill_gap_explanations(
    missing_skills: list[SkillMatch],
    matched_skills: list[SkillMatch],
) -> list[str]:
    """
    Generate contextual skill gap explanations.

    Instead of generic "Missing X", explain:
    - Why the skill matters
    - Evidence already present (child skills found)
    - How to improve ATS visibility
    """
    explanations: list[str] = []
    processed: set[str] = set()

    for skill in missing_skills:
        if skill.skill in processed:
            continue
        processed.add(skill.skill)

        # Check if children of this skill are matched
        children = get_children_of(skill.skill)
        matched_children = [
            m.skill for m in matched_skills
            if m.skill in children
        ]

        if matched_children:
            # Partial match through children
            child_list = ", ".join(matched_children[:4])
            explanations.append(
                f"You mention {child_list}, which "
                f"{'are' if len(matched_children) > 1 else 'is'} "
                f"{'technologies in' if len(matched_children) > 1 else 'a technology in'} "
                f"the {skill.skill.title()} ecosystem. "
                f"Consider explicitly listing '{skill.skill.title()}' because "
                f"ATS systems often search for the parent technology."
            )
        elif skill.importance >= 8:
            # High-importance required skill — critical gap
            explanations.append(
                f"'{skill.skill.title()}' is a high-priority requirement "
                f"(importance: {skill.importance}/10) in this JD. "
                f"If you have experience with it, make sure it's explicitly mentioned "
                f"in your Skills section."
            )
        elif skill.jd_section == "requirement":
            # Required skill — standard gap
            explanations.append(
                f"'{skill.skill.title()}' is listed as a requirement. "
                f"Add it to your resume if you have experience, even if indirect."
            )

        if len(explanations) >= 5:
            break

    # Check for reverse: matched children but parent not explicitly listed
    matched_set = {m.skill for m in matched_skills}
    for m in matched_skills:
        parent = get_parent_of(m.skill)
        if parent and parent not in matched_set and parent not in processed:
            processed.add(parent)
            siblings = [
                s.skill for s in matched_skills
                if get_parent_of(s.skill) == parent
            ]
            if len(siblings) >= 2:
                sibling_list = ", ".join(siblings[:4])
                explanations.append(
                    f"You mention {sibling_list} but not '{parent.title()}'. "
                    f"Since these are all {parent.title()} ecosystem tools, "
                    f"listing '{parent.title()}' explicitly would improve ATS matching."
                )

        if len(explanations) >= 7:
            break

    return explanations
