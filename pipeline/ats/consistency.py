"""
Contradiction and consistency detection across all ATS signals.

Runs after all extractors and cross-references signals to detect
contradictions, suspicious patterns, and flag potential issues.
Each flag carries a severity penalty applied to the consistency score.
"""

from __future__ import annotations

import re
from pipeline.ats.models import (
    AchievementResult,
    ConsistencyResult,
    ExperienceResult,
    SeniorityResult,
    SkillsResult,
)
from pipeline.ats.section_parser import Section


# Flag severity weights (penalty per flag)
_FLAG_SEVERITY = {
    "title_vs_experience": 0.08,
    "title_vs_leadership": 0.06,
    "management_no_reports": 0.07,
    "cloud_claims_no_skills": 0.06,
    "senior_no_achievements": 0.04,
    "skill_breadth_no_depth": 0.05,
    "experience_gap": 0.03,
}


def check_consistency(
    seniority: SeniorityResult | None,
    experience: ExperienceResult | None,
    achievements: AchievementResult | None,
    skills: SkillsResult | None,
    resume_sections: list[Section],
    resume_text: str = "",
) -> ConsistencyResult:
    """
    Cross-reference all signals and detect contradictions.

    Returns a consistency score (1.0 = no issues) and list of flags.
    """
    flags: list[str] = []
    penalties: list[float] = []

    full_text = resume_text or " ".join(s.text for s in resume_sections)

    # 1. Title vs Experience
    if seniority and experience and experience.resume_years is not None:
        years = experience.resume_years
        level = seniority.level

        if level == "senior" and years < 3:
            flags.append(
                f"Senior-level title detected but only ~{years:.0f} years of experience. "
                "Consider clarifying your seniority or ensuring date ranges are complete."
            )
            penalties.append(_FLAG_SEVERITY["title_vs_experience"])

        elif level == "staff" and years < 5:
            flags.append(
                f"Staff-level title detected but only ~{years:.0f} years of experience. "
                "Ensure your work history dates are accurately represented."
            )
            penalties.append(_FLAG_SEVERITY["title_vs_experience"])

        elif level == "principal" and years < 8:
            flags.append(
                f"Principal-level title detected but only ~{years:.0f} years of experience."
            )
            penalties.append(_FLAG_SEVERITY["title_vs_experience"])

    # 2. Staff/Principal without leadership evidence
    if seniority and achievements:
        level = seniority.level
        if level in ("staff", "principal") and achievements.leadership_score < 0.3:
            flags.append(
                f"{level.capitalize()}-level seniority detected without strong leadership evidence. "
                "Consider adding mentoring, cross-team collaboration, or architectural decision examples."
            )
            penalties.append(_FLAG_SEVERITY["title_vs_leadership"])

    # 3. Management title without team/reports signals
    if seniority:
        title_lower = full_text[:1000].lower()
        has_mgmt_title = any(
            w in title_lower for w in ["manager", "director", "vp", "head of"]
        )
        has_team_signal = bool(
            re.search(r"(?:team\s+of|managed|led)\s+\d+|direct\s+reports?|\d+\s+reports?", full_text, re.I)
        )

        if has_mgmt_title and not has_team_signal:
            flags.append(
                "Management/leadership title detected but no team size or reporting structure mentioned. "
                "Add specific team sizes (e.g., 'Managed team of 6 engineers')."
            )
            penalties.append(_FLAG_SEVERITY["management_no_reports"])

    # 4. Cloud expertise claims without cloud skills
    if skills:
        summary_text = " ".join(
            s.text for s in resume_sections if s.section_type in ("summary", "other")
        )[:500].lower()

        claims_cloud = any(
            phrase in summary_text
            for phrase in [
                "cloud expert", "cloud architect", "cloud native",
                "cloud infrastructure", "cloud platform", "cloud engineering",
            ]
        )

        cloud_skills_matched = sum(
            1 for s in (skills.matched or [])
            if s.skill in (
                "aws", "gcp", "azure", "ec2", "s3", "lambda",
                "kubernetes", "docker", "terraform",
            )
        )

        if claims_cloud and cloud_skills_matched == 0:
            flags.append(
                "Cloud expertise claimed in summary but no specific cloud technologies "
                "(AWS, GCP, Azure services) detected. Add specific cloud services you've used."
            )
            penalties.append(_FLAG_SEVERITY["cloud_claims_no_skills"])

    # 5. Senior+ without quantified achievements
    if seniority and achievements:
        if (
            seniority.level in ("senior", "staff", "principal")
            and achievements.impact_score < 0.3
        ):
            flags.append(
                f"{seniority.level.capitalize()}-level candidate without quantified impact metrics. "
                "Add measurable achievements (%, $, users, latency improvements)."
            )
            penalties.append(_FLAG_SEVERITY["senior_no_achievements"])

    # 6. Skill breadth without depth evidence
    if skills:
        total_skills = len(skills.matched or [])
        has_deep_descriptions = bool(
            re.findall(r"(?:built|designed|architected|implemented)\s+\w+", full_text, re.I)
        )

        if total_skills > 25 and not has_deep_descriptions:
            flags.append(
                f"Large number of skills listed ({total_skills}) but limited depth evidence "
                "in experience descriptions. Focus on your strongest skills with detailed examples."
            )
            penalties.append(_FLAG_SEVERITY["skill_breadth_no_depth"])

    # Compute consistency score
    total_penalty = sum(penalties)
    consistency_score = max(0.0, 1.0 - total_penalty)

    # Confidence: higher when we had more signals to cross-reference
    signal_count = sum(1 for x in [seniority, experience, achievements, skills] if x is not None)
    confidence = min(0.95, 0.3 + signal_count * 0.15)

    return ConsistencyResult(
        consistency_score=round(consistency_score, 3),
        flags=flags,
        confidence=confidence,
    )
