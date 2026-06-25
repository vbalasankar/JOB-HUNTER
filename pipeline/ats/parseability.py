"""
Resume structure and ATS parseability scoring.

Analyzes text-level signals since we receive plain text:
  - Section headers present
  - Contact info detectable
  - Chronological dates
  - Quantified achievements
  - Information density
"""

from __future__ import annotations

import re
from pipeline.ats.models import ParseabilityResult
from pipeline.ats.section_parser import Section, has_section_headers


def score_parseability(
    resume_text: str,
    resume_sections: list[Section],
    has_achievements: bool = False,
) -> ParseabilityResult:
    """Score resume parseability for ATS systems."""

    checks: dict[str, bool] = {}
    recommendations: list[str] = []

    # 1. Section headers
    checks["has_sections"] = has_section_headers(resume_sections, "other")
    if not checks["has_sections"]:
        recommendations.append(
            "Add clear section headers (Skills, Experience, Education) — "
            "ATS systems use these to categorize your information."
        )

    # 2. Skills section
    checks["has_skills"] = any(
        s.section_type == "skills" for s in resume_sections
    )
    if not checks["has_skills"]:
        recommendations.append(
            "Add a dedicated 'Skills' or 'Technical Skills' section — "
            "ATS systems scan for this heading first when matching keywords."
        )

    # 3. Experience section
    checks["has_experience"] = any(
        s.section_type == "experience" for s in resume_sections
    )
    if not checks["has_experience"]:
        recommendations.append(
            "Add a 'Work Experience' or 'Professional Experience' section "
            "with clear company names and date ranges."
        )

    # 4. Education section
    checks["has_education"] = any(
        s.section_type == "education" for s in resume_sections
    )
    if not checks["has_education"]:
        recommendations.append(
            "Add an 'Education' section listing your degrees and institutions."
        )

    # 5. Summary section
    checks["has_summary"] = any(
        s.section_type == "summary" for s in resume_sections
    )
    if not checks["has_summary"]:
        recommendations.append(
            "Consider adding a 2-3 line 'Summary' at the top with your title, "
            "years of experience, and top skills."
        )

    # 6. Contact info
    has_email = bool(re.search(r"\b[\w.+-]+@[\w-]+\.[\w.]+\b", resume_text))
    has_phone = bool(re.search(
        r"(?:\+?\d{1,3}[\s.-]?)?\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}",
        resume_text,
    ))
    has_linkedin = bool(re.search(r"linkedin\.com/in/", resume_text, re.I))
    checks["has_contact"] = has_email or has_phone or has_linkedin
    if not has_email:
        recommendations.append("Add your email address for ATS contact extraction.")
    if not has_linkedin:
        recommendations.append("Add your LinkedIn profile URL.")

    # 7. Chronological dates
    date_ranges = re.findall(
        r"\b\d{4}\s*[-–—]\s*(?:\d{4}|present|current)\b",
        resume_text,
        re.IGNORECASE,
    )
    checks["has_dates"] = len(date_ranges) >= 2
    if not checks["has_dates"]:
        recommendations.append(
            "Add clear date ranges (e.g., '2020 – 2024') to your experience entries."
        )

    # 8. Quantified achievements
    checks["has_achievements"] = has_achievements or bool(
        re.search(r"\d+\s*%|\$\s*\d+|\d+[xX]\s", resume_text)
    )
    if not checks["has_achievements"]:
        recommendations.append(
            "Add quantified achievements (e.g., 'Reduced latency by 40%', "
            "'Processed 1M events/day'). Numbers stand out to recruiters."
        )

    # 9. Word count & density
    words = resume_text.split()
    word_count = len(words)

    if word_count < 150:
        density = "sparse"
        recommendations.append(
            f"Your resume has only ~{word_count} words. "
            "Expand your experience descriptions with specific technologies and outcomes. "
            "Aim for 400–600 words for a one-page resume."
        )
    elif word_count > 1200:
        density = "dense"
        recommendations.append(
            f"Your resume has ~{word_count} words, which may be too dense. "
            "Focus on the most relevant experiences and keep it concise."
        )
    else:
        density = "good"

    # Compute score
    check_weights = {
        "has_sections": 0.15,
        "has_skills": 0.12,
        "has_experience": 0.12,
        "has_education": 0.08,
        "has_summary": 0.05,
        "has_contact": 0.10,
        "has_dates": 0.13,
        "has_achievements": 0.15,
    }

    score = sum(
        weight for check_name, weight in check_weights.items()
        if checks.get(check_name, False)
    )

    # Density bonus
    if density == "good":
        score += 0.10
    elif density == "sparse":
        score += 0.02
    elif density == "dense":
        score += 0.05

    score = min(1.0, score)

    return ParseabilityResult(
        score=round(score, 3),
        has_skills_section=checks.get("has_skills", False),
        has_experience_section=checks.get("has_experience", False),
        has_education_section=checks.get("has_education", False),
        has_summary_section=checks.get("has_summary", False),
        has_contact_info=checks.get("has_contact", False),
        has_quantified_achievements=checks.get("has_achievements", False),
        has_chronological_dates=checks.get("has_dates", False),
        word_count=word_count,
        density_rating=density,
        recommendations=recommendations,
    )
