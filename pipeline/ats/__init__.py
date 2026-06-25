"""
Enterprise ATS Engine Public API.

Orchestrates the entire scoring pipeline.
"""

from __future__ import annotations

from pipeline.ats.achievements import extract_achievements
from pipeline.ats.aggregator import aggregate_signals
from pipeline.ats.consistency import check_consistency
from pipeline.ats.domain import match_domains
from pipeline.ats.extractors import extract_education, extract_experience
from pipeline.ats.models import AtsScoreResponse, SkillMatch, SkillsResult
from pipeline.ats.parseability import score_parseability
from pipeline.ats.rewrite_suggestions import generate_rewrite_suggestions
from pipeline.ats.role_scorers import detect_role, get_role_profile
from pipeline.ats.section_parser import parse_jd_sections, parse_resume_sections
from pipeline.ats.semantic import compute_semantic_chunks
from pipeline.ats.seniority import detect_seniority
from pipeline.ats.skill_weights import compute_weights_for_skills
from pipeline.ats.taxonomy import extract_noun_phrases, find_skills_in_text, get_children_of, resolve_skill


def extract_and_match_skills(
    resume_text: str, jd_text: str, role: str
) -> SkillsResult:
    """Extract and match skills between resume and JD."""
    # 1. Find all skills in JD and resume
    jd_found = find_skills_in_text(jd_text)
    resume_found = find_skills_in_text(resume_text)

    # 2. Extract noun phrases
    jd_nouns = extract_noun_phrases(jd_text)
    resume_nouns = extract_noun_phrases(resume_text)

    for noun in jd_nouns:
        if noun not in jd_found:
            jd_found[noun] = noun
    for noun in resume_nouns:
        if noun not in resume_found:
            resume_found[noun] = noun

    # 3. Get role weights
    profile = get_role_profile(role)
    weights = compute_weights_for_skills(
        list(jd_found.values()), jd_text, profile.weight_overrides
    )

    matched: list[SkillMatch] = []
    missing: list[SkillMatch] = []
    all_skills: list[SkillMatch] = []

    resume_canonicals = set(resume_found.values())

    for term, canonical in jd_found.items():
        info = resolve_skill(canonical)
        category = info.category if info else "hard_skill"
        
        # Check noun phrases
        is_noun = False
        if not info and canonical in jd_nouns:
            is_noun = True

        weight = weights.get(canonical, 5)

        is_matched = False
        match_type = "none"
        credit = 0.0
        children_matched = []

        if canonical in resume_canonicals:
            is_matched = True
            match_type = "noun_phrase" if is_noun else "exact"
            credit = 1.0
        elif info:
            # Check for partial match via children
            children = get_children_of(canonical)
            found_children = [c for c in children if c in resume_canonicals]
            if found_children:
                is_matched = True
                match_type = "child_to_parent"
                # Give partial credit (max 1.0 after 3 children)
                credit = min(1.0, len(found_children) / 3.0)
                children_matched = found_children

        sm = SkillMatch(
            skill=canonical,
            category=category,
            matched=is_matched,
            match_type=match_type,
            confidence=1.0 if not is_noun else 0.6,
            jd_section="requirement", # Simplified
            jd_weight=1.0,
            importance=weight,
            credit=credit,
            children_matched=children_matched,
        )
        
        all_skills.append(sm)
        if is_matched:
            matched.append(sm)
        else:
            missing.append(sm)

    # Compute scores
    def _score_category(cat: str) -> float:
        cat_all = [s for s in all_skills if s.category == cat]
        if not cat_all:
            return 1.0
        
        total_weight = sum(s.importance for s in cat_all)
        if total_weight == 0:
            return 1.0
            
        earned = sum(s.importance * s.credit for s in matched if s.category == cat)
        return earned / total_weight

    hard_score = _score_category("hard_skill")
    soft_score = _score_category("soft_skill")
    tool_score = _score_category("tool")
    
    total_w = sum(s.importance for s in all_skills)
    overall = sum(s.importance * s.credit for s in matched) / total_w if total_w else 1.0

    return SkillsResult(
        hard_skills_score=hard_score,
        soft_skills_score=soft_score,
        tools_score=tool_score,
        overall_skills_score=overall,
        confidence=0.9,
        matched=matched,
        missing=missing,
        all_skills=all_skills,
    )


def compute_ats_score(resume_text: str, job_description: str) -> AtsScoreResponse:
    """
    Main entry point for ATS scoring.
    """
    # 1. Parse sections
    resume_sections = parse_resume_sections(resume_text)
    jd_sections = parse_jd_sections(job_description)

    # 2. Detect role
    role = detect_role(job_description)

    # 3. Extract skills
    skills = extract_and_match_skills(resume_text, job_description, role.role)

    # 4. Extract experience & education
    experience = extract_experience(resume_text, job_description)
    education = extract_education(resume_text, job_description)

    # 5. Extract achievements
    achievements = extract_achievements(resume_text)

    # 6. Detect seniority
    seniority = detect_seniority(resume_text, experience, achievements)

    # 7. Domain matching
    domain = match_domains(resume_text, job_description)

    # 8. Semantic chunks
    semantic = compute_semantic_chunks(resume_sections, jd_sections)

    # 9. Parseability
    parseability = score_parseability(resume_text, resume_sections, has_achievements=achievements.impact_score > 0.2)

    # 10. Consistency
    consistency = check_consistency(
        seniority=seniority,
        experience=experience,
        achievements=achievements,
        skills=skills,
        resume_sections=resume_sections,
        resume_text=resume_text,
    )

    # 11. Aggregate
    result = aggregate_signals(
        skills=skills,
        experience=experience,
        education=education,
        achievements=achievements,
        seniority=seniority,
        domain=domain,
        semantic=semantic,
        parseability=parseability,
        consistency=consistency,
        role_detection=role,
    )

    # 12. Rewrite suggestions
    result.rewrite_suggestions = generate_rewrite_suggestions(
        resume_text=resume_text,
        skills=skills,
        experience=experience,
        education=education,
        achievements=achievements,
        parseability=parseability,
    )

    return result
