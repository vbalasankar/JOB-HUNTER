"""
Actionable ATS rewrite suggestions referencing actual resume content.

Generates specific, prioritized recommendations to improve ATS visibility.
Each suggestion includes the category, priority, what's in the resume now,
what to change, and why it matters.
"""

from __future__ import annotations

from pipeline.ats.models import (
    AchievementResult,
    EducationResult,
    ExperienceResult,
    ParseabilityResult,
    RewriteSuggestion,
    SkillMatch,
    SkillsResult,
)
from pipeline.ats.taxonomy import get_children_of, get_parent_of


def generate_rewrite_suggestions(
    resume_text: str,
    skills: SkillsResult | None,
    experience: ExperienceResult | None,
    education: EducationResult | None,
    achievements: AchievementResult | None,
    parseability: ParseabilityResult | None,
) -> list[RewriteSuggestion]:
    """
    Generate actionable rewrite suggestions for ATS optimization.
    """
    suggestions: list[RewriteSuggestion] = []

    # 1. Missing parent skills
    if skills:
        _suggest_missing_parents(skills, suggestions)

    # 2. Missing years of experience
    if experience:
        _suggest_experience_clarity(experience, resume_text, suggestions)

    # 3. Missing skills section
    if parseability and not parseability.has_skills_section:
        suggestions.append(RewriteSuggestion(
            category="missing_skills_section",
            priority="critical",
            current_text=None,
            suggestion=(
                "Add a 'Technical Skills' section near the top of your resume listing "
                "your key technologies, languages, and tools. Example:\n\n"
                "Technical Skills\n"
                "Languages: Python, Go, TypeScript\n"
                "Cloud: AWS (EC2, S3, Lambda), GCP\n"
                "Tools: Docker, Kubernetes, Terraform"
            ),
            reasoning=(
                "ATS systems parse the Skills section first when scanning for keyword matches. "
                "Without it, your skills may only be detected from context in experience descriptions, "
                "which is less reliable."
            ),
        ))

    # 4. Weak action verbs
    if achievements and achievements.weak_verbs_found:
        for weak_line in achievements.weak_verbs_found[:3]:
            suggestions.append(RewriteSuggestion(
                category="weak_action_verb",
                priority="important",
                current_text=weak_line[:100],
                suggestion=(
                    "Replace weak verbs ('helped', 'assisted', 'worked on') with strong action verbs "
                    "('built', 'designed', 'led', 'optimized'). "
                    "Example: 'Helped with migration' → 'Led database migration reducing downtime by 60%'"
                ),
                reasoning=(
                    "Strong action verbs signal ownership and impact. Passive language "
                    "('helped', 'assisted') makes contributions appear minor to both ATS and recruiters."
                ),
            ))

    # 5. No quantified achievements
    if achievements and achievements.impact_score < 0.3:
        suggestions.append(RewriteSuggestion(
            category="no_quantified_impact",
            priority="critical",
            current_text=None,
            suggestion=(
                "Add quantified achievements to your experience entries. Examples:\n"
                "• 'Reduced API latency by 40% through caching optimization'\n"
                "• 'Processed 2M events/day with 99.9% uptime'\n"
                "• 'Led migration saving $500K/year in infrastructure costs'"
            ),
            reasoning=(
                "Quantified achievements are the strongest signal to recruiters. "
                "Numbers (%, $, users) make your impact concrete and memorable. "
                "Resumes with metrics are 40% more likely to get callbacks."
            ),
        ))

    # 6. Missing certifications mentioned in JD
    if skills:
        _suggest_missing_certifications(skills, suggestions)

    # 7. Vague seniority
    _suggest_seniority_clarity(resume_text, experience, suggestions)

    # 8. Density warnings
    if parseability:
        if parseability.density_rating == "sparse":
            suggestions.append(RewriteSuggestion(
                category="density_warning",
                priority="important",
                current_text=f"~{parseability.word_count} words",
                suggestion=(
                    "Your resume is very sparse. Expand your experience descriptions with:\n"
                    "• Specific technologies used in each role\n"
                    "• Quantified outcomes and achievements\n"
                    "• Scale of systems you worked on\n"
                    "Aim for 400–600 words for a one-page resume."
                ),
                reasoning=(
                    "ATS systems need enough text to extract keywords and context. "
                    "Very short resumes produce fewer keyword matches and lower scores."
                ),
            ))

    # 9. Missing summary
    if parseability and not parseability.has_summary_section:
        suggestions.append(RewriteSuggestion(
            category="missing_summary",
            priority="nice_to_have",
            current_text=None,
            suggestion=(
                "Add a 2-3 line summary at the top of your resume. Example:\n\n"
                "'Senior Backend Engineer with 6+ years of experience building "
                "distributed systems at scale. Expert in Python, Go, and AWS. "
                "Passionate about API design and system reliability.'"
            ),
            reasoning=(
                "A summary helps ATS systems quickly identify your role, seniority, "
                "and top skills. It also gives recruiters a quick overview during "
                "the 6-second initial scan."
            ),
        ))

    # Sort by priority
    priority_order = {"critical": 0, "important": 1, "nice_to_have": 2}
    suggestions.sort(key=lambda s: priority_order.get(s.priority, 1))

    return suggestions[:10]


def _suggest_missing_parents(skills: SkillsResult, suggestions: list[RewriteSuggestion]):
    """Suggest adding parent technologies when children are present."""
    matched_set = {m.skill for m in (skills.matched or []) if m.matched}
    missing_set = {m.skill for m in (skills.missing or [])}

    # Find parents that are missing but have matched children
    checked_parents: set[str] = set()
    for m in (skills.matched or []):
        parent = get_parent_of(m.skill)
        if parent and parent in missing_set and parent not in checked_parents:
            checked_parents.add(parent)
            siblings_matched = [
                s.skill for s in (skills.matched or [])
                if get_parent_of(s.skill) == parent and s.matched
            ]
            if siblings_matched:
                child_list = ", ".join(siblings_matched[:4])
                suggestions.append(RewriteSuggestion(
                    category="missing_parent_skill",
                    priority="critical",
                    current_text=f"Resume mentions: {child_list}",
                    suggestion=(
                        f"Add '{parent.title()}' to your Skills section. "
                        f"You already list {child_list}, which "
                        f"{'are' if len(siblings_matched) > 1 else 'is'} part of the "
                        f"{parent.title()} ecosystem. ATS systems often search for "
                        f"the parent technology name."
                    ),
                    reasoning=(
                        f"The JD requires '{parent.title()}' but your resume only mentions "
                        f"specific tools within that ecosystem. ATS keyword matching is often "
                        f"exact — explicitly listing the parent technology ensures a match."
                    ),
                ))

        if len(suggestions) >= 3:
            break


def _suggest_experience_clarity(
    experience: ExperienceResult,
    resume_text: str,
    suggestions: list[RewriteSuggestion],
):
    """Suggest clarifying years of experience."""
    if experience.resume_years is None and experience.jd_required_years is not None:
        suggestions.append(RewriteSuggestion(
            category="missing_years",
            priority="critical",
            current_text=None,
            suggestion=(
                f"The JD requires {experience.jd_required_years:.0f}+ years of experience "
                "but your resume doesn't clearly state your total years. "
                "Add a summary line like:\n\n"
                f"'Backend Engineer with X+ years of experience in distributed systems and cloud infrastructure.'"
            ),
            reasoning=(
                "Many ATS systems specifically search for years of experience. "
                "Without an explicit statement, the system must infer from date ranges, "
                "which is less reliable and may undercount your experience."
            ),
        ))
    elif (
        experience.resume_years_confidence < 0.6
        and experience.resume_years is not None
    ):
        suggestions.append(RewriteSuggestion(
            category="unclear_years",
            priority="important",
            current_text=f"Detected ~{experience.resume_years:.0f} years (low confidence)",
            suggestion=(
                "Your years of experience were inferred from date ranges but aren't explicitly stated. "
                f"Add a clear statement like '{experience.resume_years:.0f}+ years of experience' "
                "in your summary or first line."
            ),
            reasoning=(
                "Explicitly stating your years of experience removes ambiguity for both "
                "ATS systems and recruiters doing quick scans."
            ),
        ))


def _suggest_missing_certifications(
    skills: SkillsResult,
    suggestions: list[RewriteSuggestion],
):
    """Suggest adding certifications mentioned in JD."""
    missing_certs = [
        s for s in (skills.missing or [])
        if s.category == "certification"
    ]
    for cert in missing_certs[:2]:
        suggestions.append(RewriteSuggestion(
            category="missing_certification",
            priority="nice_to_have",
            current_text=None,
            suggestion=(
                f"The JD mentions '{cert.skill}' as preferred. "
                "If you hold this certification, make sure it's listed in a "
                "'Certifications' section."
            ),
            reasoning=(
                "Certifications are easy keyword wins. ATS systems often filter candidates "
                "by certification status, so having them listed ensures you pass automated screens."
            ),
        ))


def _suggest_seniority_clarity(
    resume_text: str,
    experience: ExperienceResult | None,
    suggestions: list[RewriteSuggestion],
):
    """Suggest clarifying seniority when experience suggests senior but title doesn't."""
    if experience and experience.resume_years is not None and experience.resume_years >= 5:
        # Check if resume title area lacks seniority indicators
        first_500 = resume_text[:500].lower()
        has_seniority = any(
            kw in first_500
            for kw in ["senior", "sr.", "staff", "principal", "lead", "manager", "director"]
        )
        if not has_seniority:
            suggestions.append(RewriteSuggestion(
                category="vague_seniority",
                priority="important",
                current_text=None,
                suggestion=(
                    f"Your experience (~{experience.resume_years:.0f} years) suggests a senior-level role, "
                    "but your current title doesn't clearly reflect seniority. "
                    "Consider using 'Senior', 'Staff', or 'Lead' in your title if applicable."
                ),
                reasoning=(
                    "ATS systems and recruiters use title keywords to quickly assess seniority level. "
                    "A clear seniority indicator in your title helps with filtering and role matching."
                ),
            ))
