"""
Achievement, impact, and leadership extraction from resumes.

Extracts:
  - Quantified metrics (%, $, users, latency)
  - Leadership signals (led, managed, mentored)
  - Impact signals (improved, optimized, launched)
  - Weak verbs that should be rewritten
"""

from __future__ import annotations

import re

from pipeline.ats.models import AchievementResult


# ── Metric Patterns ──────────────────────────────────────────────────

_METRIC_PATTERNS = [
    # Percentages: "by 40%", "18% improvement"
    re.compile(r"(?:by\s+)?(\d+(?:\.\d+)?)\s*%", re.I),
    # Dollar amounts: "$1.2M", "$500K", "$2 million"
    re.compile(r"\$\s*(\d+(?:\.\d+)?)\s*([MBKmk]|million|billion|thousand)?\b", re.I),
    # Large numbers with units: "1,000,000 users", "10K requests/sec"
    re.compile(
        r"(\d{1,3}(?:,\d{3})+|\d+[KMBkmb])\s*(?:\+\s*)?"
        r"(?:users?|requests?|events?|transactions?|records?|"
        r"customers?|clients?|downloads?|sessions?|queries?|"
        r"orders?|messages?|documents?)",
        re.I,
    ),
    # Multipliers: "3x", "10x improvement"
    re.compile(r"(\d+(?:\.\d+)?)\s*[×x]\s*(?:improvement|increase|faster|reduction)?", re.I),
    # Latency/throughput: "reduced latency to 50ms", "99.9% uptime"
    re.compile(r"(\d+(?:\.\d+)?)\s*(?:ms|milliseconds?|seconds?)\s*(?:latency|response\s+time)?", re.I),
    re.compile(r"(\d+(?:\.\d+)?)\s*%\s*(?:uptime|availability|SLA)", re.I),
    # Team size: "team of 6", "managed 12 engineers"
    re.compile(r"(?:team\s+of|managed|led)\s+(\d+)\s+(?:engineers?|developers?|people|members?|reports?)", re.I),
    # Revenue/cost: "saved $X", "generated $X"
    re.compile(r"(?:saved?|generated?|reduced?\s+costs?\s+by)\s+\$?\s*(\d+(?:\.\d+)?)\s*([MBKmk])?", re.I),
]

# ── Leadership Patterns ──────────────────────────────────────────────

_LEADERSHIP_VERBS = [
    "led", "lead", "leading", "managed", "managing",
    "mentored", "mentoring", "coached", "coaching",
    "directed", "directing", "coordinated", "coordinating",
    "spearheaded", "oversaw", "guided", "guiding",
    "supervised", "supervising", "headed",
    "built team", "grew team", "hired",
    "established", "founded", "co-founded",
]

_LEADERSHIP_PATTERN = re.compile(
    r"\b(" + "|".join(re.escape(v) for v in _LEADERSHIP_VERBS) + r")\b",
    re.IGNORECASE,
)

# ── Impact Patterns ──────────────────────────────────────────────────

_IMPACT_VERBS = [
    "improved", "optimized", "reduced", "launched",
    "architected", "scaled", "designed", "implemented",
    "migrated", "automated", "transformed", "streamlined",
    "accelerated", "consolidated", "pioneered", "revamped",
    "delivered", "deployed", "built", "created",
    "developed", "engineered", "integrated", "modernized",
    "refactored", "simplified", "upgraded",
]

_IMPACT_PATTERN = re.compile(
    r"\b(" + "|".join(re.escape(v) for v in _IMPACT_VERBS) + r")\b",
    re.IGNORECASE,
)

# ── Weak Verb Patterns ───────────────────────────────────────────────

_WEAK_VERBS = [
    "helped", "assisted", "participated",
    "was responsible for", "responsible for",
    "worked on", "involved in", "contributed to",
    "tasked with", "dealt with", "handled",
    "took part in", "was involved in",
    "supported",
]

_WEAK_VERB_PATTERN = re.compile(
    r"\b(" + "|".join(re.escape(v) for v in _WEAK_VERBS) + r")\b",
    re.IGNORECASE,
)


def extract_achievements(resume_text: str) -> AchievementResult:
    """
    Extract achievements, metrics, leadership signals, and weak verbs
    from resume text.
    """
    # Split into sentences/lines for granular extraction
    lines = re.split(r"[.\n•–—]", resume_text)
    lines = [line.strip() for line in lines if line.strip()]

    achievements: list[str] = []
    metrics_found: list[str] = []
    leadership_signals: list[str] = []
    impact_signals: list[str] = []
    weak_verbs_found: list[str] = []

    for line in lines:
        if len(line) < 10:
            continue

        # Check for metrics
        has_metric = False
        for pattern in _METRIC_PATTERNS:
            match = pattern.search(line)
            if match:
                has_metric = True
                metrics_found.append(line[:120])
                break

        # Check for leadership
        has_leadership = False
        leadership_match = _LEADERSHIP_PATTERN.search(line)
        if leadership_match:
            has_leadership = True
            leadership_signals.append(line[:120])

        # Check for impact verbs
        has_impact = False
        impact_match = _IMPACT_PATTERN.search(line)
        if impact_match:
            has_impact = True
            if has_metric or has_leadership:
                # Impact + metric/leadership = achievement
                if line[:120] not in achievements:
                    achievements.append(line[:120])

        # Check for weak verbs
        weak_match = _WEAK_VERB_PATTERN.search(line)
        if weak_match:
            weak_verbs_found.append(line[:120])

        # Also flag impact lines without metrics
        if has_impact and not has_metric and not has_leadership:
            impact_signals.append(line[:120])

    # Deduplicate
    achievements = list(dict.fromkeys(achievements))[:10]
    metrics_found = list(dict.fromkeys(metrics_found))[:10]
    leadership_signals = list(dict.fromkeys(leadership_signals))[:10]
    weak_verbs_found = list(dict.fromkeys(weak_verbs_found))[:10]

    # Compute scores
    impact_score = _compute_impact_score(len(metrics_found), len(achievements))
    leadership_score = _compute_leadership_score(len(leadership_signals))
    ownership_score = _compute_ownership_score(
        len(impact_signals), len(achievements), len(weak_verbs_found)
    )

    # Confidence based on evidence quantity
    total_evidence = len(metrics_found) + len(leadership_signals) + len(achievements)
    confidence = min(0.95, 0.3 + total_evidence * 0.08) if total_evidence > 0 else 0.20

    return AchievementResult(
        impact_score=impact_score,
        leadership_score=leadership_score,
        ownership_score=ownership_score,
        achievements=achievements,
        metrics_found=metrics_found,
        leadership_signals=leadership_signals,
        weak_verbs_found=weak_verbs_found,
        confidence=confidence,
    )


def _compute_impact_score(metrics_count: int, achievement_count: int) -> float:
    """Score based on quantified achievements."""
    if metrics_count >= 5:
        return 1.0
    elif metrics_count >= 3:
        return 0.85
    elif metrics_count >= 1:
        return 0.60 + (achievement_count * 0.05)
    elif achievement_count >= 1:
        return 0.40
    return 0.15


def _compute_leadership_score(leadership_count: int) -> float:
    """Score based on leadership signals."""
    if leadership_count >= 5:
        return 1.0
    elif leadership_count >= 3:
        return 0.80
    elif leadership_count >= 1:
        return 0.50
    return 0.10


def _compute_ownership_score(
    impact_count: int, achievement_count: int, weak_verb_count: int
) -> float:
    """Score based on ownership vs passive language."""
    strong = impact_count + achievement_count
    weak = weak_verb_count

    if strong == 0 and weak == 0:
        return 0.30

    ratio = strong / max(strong + weak, 1)
    return min(1.0, ratio * 1.2)
