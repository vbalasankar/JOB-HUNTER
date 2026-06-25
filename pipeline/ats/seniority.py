"""
Candidate seniority inference from resume signals.

Multi-signal approach:
  - Title keywords (35%)
  - Total years of experience (25%)
  - Scope signals (20%)
  - Achievement scale (10%)
  - Reporting/team signals (10%)

Also detects career trajectory and stability patterns.
"""

from __future__ import annotations

import re
from pipeline.ats.models import SeniorityResult, ExperienceResult, AchievementResult


# ── Seniority Levels ─────────────────────────────────────────────────

SENIORITY_LEVELS = ["intern", "junior", "mid", "senior", "staff", "principal"]

_TITLE_PATTERNS: dict[str, list[re.Pattern]] = {
    "intern": [re.compile(r"\bintern\b", re.I), re.compile(r"\binternship\b", re.I)],
    "junior": [
        re.compile(r"\bjunior\b", re.I), re.compile(r"\bjr\.?\b", re.I),
        re.compile(r"\bentry[- ]?level\b", re.I), re.compile(r"\bnew\s+grad\b", re.I),
    ],
    "mid": [re.compile(r"\bmid[- ]?level\b", re.I)],
    "senior": [
        re.compile(r"\bsenior\b", re.I), re.compile(r"\bsr\.?\b", re.I),
    ],
    "staff": [re.compile(r"\bstaff\b", re.I)],
    "principal": [
        re.compile(r"\bprincipal\b", re.I), re.compile(r"\bdistinguished\b", re.I),
        re.compile(r"\bfellow\b", re.I),
    ],
}

_LEADERSHIP_TITLE_PATTERNS: dict[str, list[re.Pattern]] = {
    "senior": [
        re.compile(r"\blead\b", re.I), re.compile(r"\bteam\s+lead\b", re.I),
        re.compile(r"\btech\s+lead\b", re.I),
    ],
    "staff": [
        re.compile(r"\bmanager\b", re.I), re.compile(r"\bengineering\s+manager\b", re.I),
    ],
    "principal": [
        re.compile(r"\bdirector\b", re.I), re.compile(r"\bvp\b", re.I),
        re.compile(r"\bvice\s+president\b", re.I), re.compile(r"\bhead\s+of\b", re.I),
        re.compile(r"\bc[tio]o\b", re.I),
    ],
}

# ── Scope Signals ────────────────────────────────────────────────────

_SCOPE_PATTERNS = [
    (re.compile(r"(?:across|spanning)\s+(\d+)\s+teams?", re.I), "multi_team"),
    (re.compile(r"\bcompany[- ]?wide\b", re.I), "company_wide"),
    (re.compile(r"\borg(?:anization)?[- ]?(?:level|wide)\b", re.I), "org_level"),
    (re.compile(r"\bcross[- ]?functional\b", re.I), "cross_functional"),
    (re.compile(r"\bmulti[- ]?team\b", re.I), "multi_team"),
    (re.compile(r"\barchitect(?:ed|ure)?\b", re.I), "architecture"),
    (re.compile(r"\bstrategic\b", re.I), "strategic"),
    (re.compile(r"\benterprise[- ]?(?:level|wide|scale)\b", re.I), "enterprise"),
]

# ── Career Trajectory Patterns ───────────────────────────────────────

_TITLE_HIERARCHY = {
    "intern": 0, "internship": 0,
    "junior": 1, "jr": 1, "associate": 1,
    "engineer": 2, "developer": 2, "analyst": 2,
    "senior": 3, "sr": 3, "lead": 3,
    "staff": 4, "principal": 5, "distinguished": 6,
    "manager": 4, "director": 5, "vp": 6, "head": 5,
    "cto": 7, "cio": 7, "ceo": 7,
}


def detect_seniority(
    resume_text: str,
    experience: ExperienceResult | None = None,
    achievements: AchievementResult | None = None,
) -> SeniorityResult:
    """
    Infer candidate seniority from multiple resume signals.
    """
    signals: list[str] = []
    scores: dict[str, float] = {level: 0.0 for level in SENIORITY_LEVELS}

    # 1. Title keywords (weight 0.35)
    title_level = _detect_from_titles(resume_text)
    if title_level:
        scores[title_level] += 0.35
        signals.append(f"Title contains '{title_level}'-level keywords")

    # Also check leadership titles
    for level, patterns in _LEADERSHIP_TITLE_PATTERNS.items():
        for pattern in patterns:
            if pattern.search(resume_text[:1000]):
                scores[level] += 0.10
                signals.append(f"Leadership title pattern detected (→ {level})")
                break

    # 2. Total years (weight 0.25)
    years = experience.resume_years if experience else None
    if years is not None:
        year_level = _years_to_level(years)
        scores[year_level] += 0.25
        signals.append(f"~{years:.0f} years of experience → {year_level} level")

    # 3. Scope signals (weight 0.20)
    scope_count = 0
    for pattern, scope_type in _SCOPE_PATTERNS:
        if pattern.search(resume_text):
            scope_count += 1
            signals.append(f"Scope signal: {scope_type}")

    if scope_count >= 3:
        scores["principal"] += 0.15
        scores["staff"] += 0.05
    elif scope_count >= 2:
        scores["staff"] += 0.12
        scores["senior"] += 0.08
    elif scope_count >= 1:
        scores["senior"] += 0.15
        scores["mid"] += 0.05

    # 4. Achievement scale (weight 0.10)
    if achievements:
        if achievements.impact_score >= 0.8:
            scores["staff"] += 0.05
            scores["senior"] += 0.05
        elif achievements.impact_score >= 0.5:
            scores["senior"] += 0.05
            scores["mid"] += 0.05

    # 5. Reporting signals (weight 0.10)
    team_match = re.search(r"(?:team\s+of|managed|led)\s+(\d+)", resume_text, re.I)
    if team_match:
        team_size = int(team_match.group(1))
        signals.append(f"Team/report size: {team_size}")
        if team_size >= 10:
            scores["staff"] += 0.08
            scores["principal"] += 0.02
        elif team_size >= 5:
            scores["senior"] += 0.08
            scores["staff"] += 0.02
        elif team_size >= 2:
            scores["senior"] += 0.05
            scores["mid"] += 0.05

    # Find the winning level
    best_level = max(scores, key=lambda k: scores[k])
    best_score = scores[best_level]

    # Confidence based on how decisive the signal is
    total_score = sum(scores.values())
    confidence = best_score / max(total_score, 0.01) if total_score > 0 else 0.0
    confidence = min(0.95, confidence)

    # Career trajectory
    trajectory, trajectory_detail = _detect_trajectory(resume_text)
    stability_note = _detect_stability(resume_text)

    if trajectory:
        signals.append(f"Career trajectory: {trajectory}")
    if stability_note:
        signals.append(stability_note)

    return SeniorityResult(
        level=best_level if best_score > 0 else "mid",
        confidence=confidence,
        signals=signals,
        trajectory=trajectory,
        trajectory_detail=trajectory_detail,
        stability_note=stability_note,
    )


def _detect_from_titles(text: str) -> str | None:
    """Detect seniority from title keywords in the first part of resume."""
    # Focus on the first ~1000 chars (usually contains current title)
    search_text = text[:1000]

    # Check from highest to lowest
    for level in reversed(SENIORITY_LEVELS):
        if level in _TITLE_PATTERNS:
            for pattern in _TITLE_PATTERNS[level]:
                if pattern.search(search_text):
                    return level
    return None


def _years_to_level(years: float) -> str:
    """Map years of experience to expected seniority level."""
    if years < 1:
        return "intern"
    elif years < 3:
        return "junior"
    elif years < 5:
        return "mid"
    elif years < 9:
        return "senior"
    elif years < 13:
        return "staff"
    else:
        return "principal"


def _detect_trajectory(text: str) -> tuple[str | None, str | None]:
    """Detect career trajectory from title progression."""
    # Find all title-like lines (short lines that contain seniority keywords)
    title_lines = re.findall(
        r"^(.{10,80})$",
        text,
        re.MULTILINE,
    )

    levels_found: list[int] = []
    for line in title_lines:
        line_lower = line.lower()
        for keyword, rank in _TITLE_HIERARCHY.items():
            if re.search(r"\b" + re.escape(keyword) + r"\b", line_lower):
                levels_found.append(rank)
                break

    if len(levels_found) < 2:
        return None, None

    # Check if trajectory is consistently upward
    is_ascending = all(
        levels_found[i] <= levels_found[i - 1]
        for i in range(1, len(levels_found))
    )
    # Note: resume lists most recent first, so descending order = ascending career
    is_positive = levels_found[0] > levels_found[-1]

    if is_positive and is_ascending:
        return "positive", "Consistent upward career progression detected"
    elif levels_found[0] < levels_found[-1]:
        return "concern", "Recent role appears at a lower level than previous roles"
    else:
        return "lateral", "Lateral career moves detected"


def _detect_stability(text: str) -> str | None:
    """Detect job stability patterns."""
    # Count date ranges (approximate number of positions)
    date_ranges = re.findall(
        r"\b\d{4}\s*[-–—]\s*(?:\d{4}|present|current)\b",
        text,
        re.IGNORECASE,
    )

    if len(date_ranges) < 2:
        return None

    # Extract years to estimate tenure
    years_found = re.findall(r"\b(20\d{2}|19\d{2})\b", text)
    if len(years_found) >= 2:
        years_int = [int(y) for y in years_found]
        career_span = max(years_int) - min(years_int)

        if career_span > 0:
            avg_tenure = career_span / len(date_ranges)
            if avg_tenure < 1.0 and len(date_ranges) >= 4:
                return f"High job mobility: ~{len(date_ranges)} positions in {career_span} years (avg {avg_tenure:.1f} years/role)"
            elif avg_tenure >= 3.0:
                return f"Strong stability: ~{len(date_ranges)} positions in {career_span} years (avg {avg_tenure:.1f} years/role)"

    return None
