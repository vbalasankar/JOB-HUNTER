"""
Experience and education extraction — all with confidence scores.

Every extraction returns evidence (the source text that produced the value)
and a confidence level so the aggregator can weight trustworthy signals higher.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from pipeline.ats.models import ConfidentValue, EducationResult, ExperienceResult


# ══════════════════════════════════════════════════════════════════════
#  EXPERIENCE EXTRACTION
# ══════════════════════════════════════════════════════════════════════

# Patterns for explicit years of experience
_YEARS_PATTERNS = [
    # "5+ years", "5+ yrs"
    (re.compile(r"(\d+)\+?\s*(?:years?|yrs?)(?:\s+of)?\s+(?:experience|exp)", re.I), 0.95),
    # "3-5 years", "3 to 5 years"
    (re.compile(r"(\d+)\s*[-–—to]+\s*(\d+)\s*(?:years?|yrs?)(?:\s+of)?\s+(?:experience|exp)?", re.I), 0.93),
    # "minimum 5 years"
    (re.compile(r"(?:minimum|at\s+least|min\.?)\s*(\d+)\s*(?:years?|yrs?)", re.I), 0.93),
    # "5 years experience" (no "of")
    (re.compile(r"(\d+)\s*(?:years?|yrs?)\s+(?:experience|exp|professional)", re.I), 0.90),
    # "5+ years"
    (re.compile(r"(\d+)\+?\s*(?:years?|yrs?)\b", re.I), 0.80),
]

# Vague experience indicators
_VAGUE_EXPERIENCE_MAP = {
    "extensive experience": (7.0, 0.35),
    "significant experience": (6.0, 0.35),
    "deep experience": (7.0, 0.35),
    "strong experience": (5.0, 0.35),
    "substantial experience": (6.0, 0.35),
    "proven experience": (5.0, 0.30),
    "demonstrated experience": (5.0, 0.30),
    "solid experience": (4.0, 0.30),
    "some experience": (2.0, 0.25),
    "familiarity with": (1.0, 0.20),
}

# Date range patterns for implicit experience calculation
_DATE_RANGE_PATTERNS = [
    # "Jan 2019 – Present", "January 2019 - current"
    re.compile(
        r"(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|"
        r"Jul(?:y)?|Aug(?:ust)?|Sep(?:t(?:ember)?)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)"
        r"\s*\.?\s*(\d{4})\s*[-–—]\s*"
        r"(?:((?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|"
        r"Jul(?:y)?|Aug(?:ust)?|Sep(?:t(?:ember)?)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)"
        r"\s*\.?\s*(\d{4}))|present|current|now|ongoing)",
        re.IGNORECASE,
    ),
    # "2019 – 2024", "2019 - Present"
    re.compile(
        r"\b(\d{4})\s*[-–—]\s*(?:(\d{4})|present|current|now|ongoing)\b",
        re.IGNORECASE,
    ),
]

_MONTH_MAP = {
    "jan": 1, "january": 1, "feb": 2, "february": 2, "mar": 3, "march": 3,
    "apr": 4, "april": 4, "may": 5, "jun": 6, "june": 6,
    "jul": 7, "july": 7, "aug": 8, "august": 8, "sep": 9, "sept": 9,
    "september": 9, "oct": 10, "october": 10, "nov": 11, "november": 11,
    "dec": 12, "december": 12,
}


def extract_experience(resume_text: str, jd_text: str) -> ExperienceResult:
    """Extract and compare experience between resume and JD."""

    # Extract JD requirement
    jd_years = _extract_years_from_jd(jd_text)

    # Extract resume experience
    resume_explicit = _extract_explicit_years(resume_text)
    resume_dates = _extract_years_from_dates(resume_text)

    # Use the higher-confidence one
    if resume_explicit.confidence >= resume_dates.confidence:
        resume_years = resume_explicit
    else:
        resume_years = resume_dates

    # Compute score
    score, detail = _compute_experience_score(jd_years, resume_years)

    # Overall confidence is limited by the weaker signal
    if jd_years.confidence > 0 and resume_years.confidence > 0:
        confidence = min(jd_years.confidence, resume_years.confidence)
    elif jd_years.confidence > 0 or resume_years.confidence > 0:
        confidence = max(jd_years.confidence, resume_years.confidence) * 0.5
    else:
        confidence = 0.0

    return ExperienceResult(
        jd_required_years=jd_years.value,
        jd_years_confidence=jd_years.confidence,
        jd_years_evidence=jd_years.evidence,
        resume_years=resume_years.value,
        resume_years_confidence=resume_years.confidence,
        resume_years_evidence=resume_years.evidence,
        score=score,
        confidence=confidence,
        detail=detail,
    )


def _extract_years_from_jd(text: str) -> ConfidentValue[Optional[float]]:
    """Extract required years of experience from a JD."""
    best_match: ConfidentValue[Optional[float]] = ConfidentValue(
        value=None, confidence=0.0, evidence=[], method="none"
    )

    for pattern, base_confidence in _YEARS_PATTERNS:
        for match in pattern.finditer(text):
            groups = match.groups()
            snippet = match.group(0).strip()

            if len(groups) >= 2 and groups[1]:
                # Range like "3-5 years" — use lower bound
                years = float(groups[0])
            else:
                years = float(groups[0])

            if years > 0 and base_confidence > best_match.confidence:
                best_match = ConfidentValue(
                    value=years,
                    confidence=base_confidence,
                    evidence=[snippet],
                    method="regex",
                )

    # Check vague indicators if no explicit match
    if best_match.value is None:
        text_lower = text.lower()
        for phrase, (years, conf) in _VAGUE_EXPERIENCE_MAP.items():
            if phrase in text_lower:
                best_match = ConfidentValue(
                    value=years,
                    confidence=conf,
                    evidence=[phrase],
                    method="heuristic",
                )
                break

    return best_match


def _extract_explicit_years(text: str) -> ConfidentValue[Optional[float]]:
    """Extract explicitly stated years of experience from resume."""
    best: ConfidentValue[Optional[float]] = ConfidentValue(
        value=None, confidence=0.0, evidence=[], method="none"
    )

    for pattern, base_confidence in _YEARS_PATTERNS:
        for match in pattern.finditer(text):
            groups = match.groups()
            snippet = match.group(0).strip()
            years = float(groups[0])

            if years > 0 and base_confidence > best.confidence:
                best = ConfidentValue(
                    value=years,
                    confidence=base_confidence,
                    evidence=[snippet],
                    method="regex",
                )

    return best


def _extract_years_from_dates(text: str) -> ConfidentValue[Optional[float]]:
    """Calculate total years from date ranges in resume work history."""
    current_year = datetime.now().year
    current_month = datetime.now().month
    date_ranges: list[tuple[float, float, str]] = []  # (start_decimal, end_decimal, snippet)

    for pattern in _DATE_RANGE_PATTERNS:
        for match in pattern.finditer(text):
            snippet = match.group(0).strip()
            groups = match.groups()

            try:
                # Determine start year/month
                start_year = None
                end_year = None

                if len(groups) >= 3 and groups[0]:
                    # Pattern with month names
                    start_year = int(groups[0])
                    if groups[2]:
                        end_year = int(groups[2])
                    else:
                        end_year = current_year
                elif len(groups) >= 1 and groups[0]:
                    start_year = int(groups[0])
                    if len(groups) >= 2 and groups[1]:
                        end_year = int(groups[1])
                    else:
                        end_year = current_year

                if start_year and end_year:
                    if 1970 <= start_year <= current_year and start_year <= end_year <= current_year + 1:
                        date_ranges.append((start_year, end_year, snippet))

            except (ValueError, IndexError):
                continue

    if not date_ranges:
        return ConfidentValue(value=None, confidence=0.0, evidence=[], method="none")

    # Sum non-overlapping durations
    # Sort by start year
    date_ranges.sort(key=lambda x: x[0])

    total_years = 0.0
    evidence: list[str] = []
    prev_end = 0.0

    for start, end, snippet in date_ranges:
        effective_start = max(start, prev_end)
        if end > effective_start:
            total_years += end - effective_start
            prev_end = end
            evidence.append(snippet)

    if total_years > 0:
        return ConfidentValue(
            value=round(total_years, 1),
            confidence=0.80,
            evidence=evidence[:5],
            method="date_range_analysis",
        )

    return ConfidentValue(value=None, confidence=0.0, evidence=[], method="none")


def _compute_experience_score(
    jd_years: ConfidentValue[Optional[float]],
    resume_years: ConfidentValue[Optional[float]],
) -> tuple[float, str]:
    """Compute experience match score and generate detail string."""
    if jd_years.value is None:
        return 1.0, "No specific experience requirement in JD"

    if resume_years.value is None:
        return 0.5, f"JD requires {jd_years.value:.0f}+ years but resume doesn't state experience level"

    jd_y = jd_years.value
    res_y = resume_years.value

    if res_y >= jd_y:
        score = 1.0
        detail = f"Exceeds requirement ({res_y:.0f} years vs {jd_y:.0f}+ required)"
    elif res_y >= jd_y - 1:
        score = 0.85
        detail = f"Close to requirement ({res_y:.0f} years vs {jd_y:.0f}+ required)"
    elif res_y >= jd_y - 2:
        score = 0.65
        detail = f"Slightly below ({res_y:.0f} years vs {jd_y:.0f}+ required)"
    elif res_y >= jd_y / 2:
        score = 0.40
        detail = f"Below requirement ({res_y:.0f} years vs {jd_y:.0f}+ required)"
    else:
        score = 0.20
        detail = f"Significantly below ({res_y:.0f} years vs {jd_y:.0f}+ required)"

    return score, detail


# ══════════════════════════════════════════════════════════════════════
#  EDUCATION EXTRACTION
# ══════════════════════════════════════════════════════════════════════

DEGREE_LEVELS: dict[str, int] = {
    "phd": 5, "ph.d": 5, "doctorate": 5, "doctoral": 5, "d.phil": 5,
    "master": 4, "masters": 4, "master's": 4, "ms": 4, "m.s": 4,
    "ma": 4, "m.a": 4, "msc": 4, "m.sc": 4, "mtech": 4, "m.tech": 4,
    "mba": 4, "m.b.a": 4, "m.eng": 4, "meng": 4, "mca": 4, "m.c.a": 4,
    "mcs": 4, "m.cs": 4, "mse": 4,
    "bachelor": 3, "bachelors": 3, "bachelor's": 3, "bs": 3, "b.s": 3,
    "ba": 3, "b.a": 3, "bsc": 3, "b.sc": 3, "btech": 3, "b.tech": 3,
    "b.e": 3, "be": 3, "bca": 3, "b.c.a": 3, "bcs": 3, "b.cs": 3,
    "beng": 3, "b.eng": 3,
    "associate": 2, "associates": 2, "associate's": 2, "a.s": 2, "a.a": 2,
    "certificate": 1, "certification": 1, "bootcamp": 1, "diploma": 1,
    "nanodegree": 1, "professional certificate": 1,
}

_DEGREE_LEVEL_NAMES = {
    5: "PhD/Doctorate",
    4: "Master's",
    3: "Bachelor's",
    2: "Associate's",
    1: "Certificate/Bootcamp",
}

# Patterns to detect degree mentions
_DEGREE_PATTERNS = [
    # "Bachelor's degree in Computer Science"
    re.compile(
        r"\b((?:Ph\.?D|Doctorate|Doctoral|Master(?:'?s)?|M\.?S\.?|M\.?A\.?|M\.?Sc\.?|"
        r"M\.?Tech|MBA|M\.?Eng|M\.?C\.?A|Bachelor(?:'?s)?|B\.?S\.?|B\.?A\.?|B\.?Sc\.?|"
        r"B\.?Tech|B\.?E\.?|B\.?C\.?A|B\.?Eng|Associate(?:'?s)?|A\.?S\.?|A\.?A\.?)"
        r"(?:'s)?(?:\s+degree)?)"
        r"(?:\s+(?:in|of)\s+([\w\s,&]+?))?(?:\s*[,.\n]|\s+(?:from|at)\b|$)",
        re.IGNORECASE,
    ),
]

_PREFERRED_PATTERN = re.compile(
    r"\b(?:preferred|desired|nice\s+to\s+have|bonus|ideal(?:ly)?|plus)\b",
    re.IGNORECASE,
)


def extract_education(resume_text: str, jd_text: str) -> EducationResult:
    """Extract and compare education between resume and JD."""

    jd_level = _extract_education_level(jd_text)
    resume_level = _extract_education_level(resume_text)

    # Check if JD marks it as preferred vs required
    jd_is_preferred = False
    if jd_level.value is not None:
        # Check if "preferred" appears near the education mention
        for ev in jd_level.evidence:
            surrounding = _get_surrounding_text(jd_text, ev, window=100)
            if _PREFERRED_PATTERN.search(surrounding):
                jd_is_preferred = True
                jd_level = ConfidentValue(
                    value=jd_level.value,
                    confidence=jd_level.confidence * 0.7,  # Lower confidence for preferred
                    evidence=jd_level.evidence,
                    method=jd_level.method,
                )
                break

    # Extract field of study from resume
    resume_field = _extract_field_of_study(resume_text)

    # Compute score
    score, detail = _compute_education_score(jd_level, resume_level, jd_is_preferred)

    # Confidence
    if jd_level.confidence > 0 and resume_level.confidence > 0:
        confidence = min(jd_level.confidence, resume_level.confidence)
    elif jd_level.confidence > 0 or resume_level.confidence > 0:
        confidence = max(jd_level.confidence, resume_level.confidence) * 0.5
    else:
        confidence = 0.0

    return EducationResult(
        jd_required_level=jd_level.value,
        jd_level_confidence=jd_level.confidence,
        jd_level_evidence=jd_level.evidence,
        jd_is_preferred=jd_is_preferred,
        resume_level=resume_level.value,
        resume_level_confidence=resume_level.confidence,
        resume_level_evidence=resume_level.evidence,
        resume_field=resume_field,
        score=score,
        confidence=confidence,
        detail=detail,
    )


def _extract_education_level(text: str) -> ConfidentValue[Optional[str]]:
    """Extract the highest education level mentioned in text."""
    best_level = 0
    best_name = None
    best_evidence: list[str] = []

    text_lower = text.lower()

    # Check each degree keyword
    for keyword, level in DEGREE_LEVELS.items():
        # Word boundary search
        pattern = re.compile(r"\b" + re.escape(keyword) + r"\b", re.IGNORECASE)
        if pattern.search(text_lower):
            if level > best_level:
                best_level = level
                best_name = _DEGREE_LEVEL_NAMES.get(level, keyword)
                # Find the actual snippet
                match = pattern.search(text)
                if match:
                    # Get surrounding context
                    start = max(0, match.start() - 20)
                    end = min(len(text), match.end() + 40)
                    best_evidence = [text[start:end].strip()]

    if best_name:
        # Determine canonical level name
        level_key = None
        for key, val in DEGREE_LEVELS.items():
            if val == best_level and key in (
                "phd", "master", "bachelor", "associate", "certificate"
            ):
                level_key = key
                break

        return ConfidentValue(
            value=level_key or best_name.lower(),
            confidence=0.90 if best_level >= 3 else 0.80,
            evidence=best_evidence,
            method="regex",
        )

    return ConfidentValue(value=None, confidence=0.0, evidence=[], method="none")


def _extract_field_of_study(text: str) -> Optional[str]:
    """Extract field of study from resume education section."""
    for pattern in _DEGREE_PATTERNS:
        match = pattern.search(text)
        if match and match.group(2):
            field_raw = match.group(2).strip()
            # Clean up
            field_raw = re.sub(r"\s+", " ", field_raw)
            if len(field_raw) < 60:
                return field_raw
    return None


def _get_surrounding_text(text: str, snippet: str, window: int = 100) -> str:
    """Get text surrounding a snippet."""
    idx = text.lower().find(snippet.lower())
    if idx == -1:
        return ""
    start = max(0, idx - window)
    end = min(len(text), idx + len(snippet) + window)
    return text[start:end]


def _compute_education_score(
    jd_level: ConfidentValue[Optional[str]],
    resume_level: ConfidentValue[Optional[str]],
    jd_is_preferred: bool,
) -> tuple[float, str]:
    """Compute education match score."""
    if jd_level.value is None:
        return 1.0, "No specific education requirement in JD"

    if resume_level.value is None:
        if jd_is_preferred:
            return 0.60, f"JD prefers {_DEGREE_LEVEL_NAMES.get(DEGREE_LEVELS.get(jd_level.value, 3), jd_level.value)} but no education detected in resume"
        return 0.50, f"JD requires {_DEGREE_LEVEL_NAMES.get(DEGREE_LEVELS.get(jd_level.value, 3), jd_level.value)} but no education detected in resume"

    jd_num = DEGREE_LEVELS.get(jd_level.value, 3)
    res_num = DEGREE_LEVELS.get(resume_level.value, 3)
    jd_name = _DEGREE_LEVEL_NAMES.get(jd_num, jd_level.value)
    res_name = _DEGREE_LEVEL_NAMES.get(res_num, resume_level.value)

    if res_num >= jd_num:
        return 1.0, f"Meets/exceeds requirement ({res_name} vs {jd_name} {'preferred' if jd_is_preferred else 'required'})"
    elif res_num == jd_num - 1:
        score = 0.80 if jd_is_preferred else 0.75
        return score, f"One level below ({res_name} vs {jd_name} {'preferred' if jd_is_preferred else 'required'})"
    elif res_num == jd_num - 2:
        score = 0.55 if jd_is_preferred else 0.45
        return score, f"Two levels below ({res_name} vs {jd_name} {'preferred' if jd_is_preferred else 'required'})"
    else:
        return 0.20, f"Significantly below ({res_name} vs {jd_name} {'preferred' if jd_is_preferred else 'required'})"
