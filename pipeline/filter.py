"""
Pre-filter — cheap keyword/location/seniority checks before expensive embedding.

Filters are applied as an AND of:
  - At least one include_keyword appears in title OR description
  - No exclude_keyword appears in title or description
  - Location matches configured locations (with remote logic)
  - Seniority matches configured levels
"""

from __future__ import annotations

import logging
import re

from config import get_settings
from storage.models import Job

logger = logging.getLogger(__name__)

# Seniority patterns
SENIORITY_PATTERNS: dict[str, list[str]] = {
    "intern": [r"\bintern\b", r"\binternship\b"],
    "junior": [r"\bjunior\b", r"\bjr\.?\b", r"\bentry[- ]?level\b"],
    "mid": [r"\bmid[- ]?level\b", r"\bmid\b"],
    "senior": [r"\bsenior\b", r"\bsr\.?\b"],
    "staff": [r"\bstaff\b"],
    "principal": [r"\bprincipal\b"],
    "lead": [r"\blead\b", r"\bteam lead\b"],
    "manager": [r"\bmanager\b", r"\bengineering manager\b", r"\bem\b"],
    "director": [r"\bdirector\b"],
    "vp": [r"\bvp\b", r"\bvice president\b"],
}


def filter_jobs(jobs: list[Job]) -> list[Job]:
    """
    Apply cheap pre-filters. Returns jobs that pass all criteria.
    """
    settings = get_settings()
    include_kw = [kw.lower() for kw in settings.include_keywords_list]
    exclude_kw = [kw.lower() for kw in settings.exclude_keywords_list]
    locations = [loc.lower() for loc in settings.locations_list]
    seniority = [s.lower() for s in settings.seniority_list]

    passed: list[Job] = []
    reasons: dict[str, int] = {
        "no_keyword_match": 0,
        "excluded_keyword": 0,
        "location_mismatch": 0,
        "seniority_mismatch": 0,
    }

    for job in jobs:
        title_lower = job.title.lower()
        desc_lower = job.description_raw.lower()
        searchable = f"{title_lower} {desc_lower}"
        location_lower = (job.location or "").lower()

        # --- Include keywords (at least one must match) ---
        if include_kw:
            if not any(kw in searchable for kw in include_kw):
                reasons["no_keyword_match"] += 1
                continue

        # --- Exclude keywords (none must match) ---
        if any(kw in searchable for kw in exclude_kw):
            reasons["excluded_keyword"] += 1
            continue

        # --- Location filter ---
        if locations:
            location_match = False
            for loc in locations:
                if loc == "remote":
                    # "Remote" matches: remote_type == remote, or "remote" in location
                    if job.remote_type == "remote" or "remote" in location_lower:
                        location_match = True
                        break
                else:
                    if loc in location_lower:
                        location_match = True
                        break
            if not location_match:
                reasons["location_mismatch"] += 1
                continue

        # --- Seniority filter ---
        if seniority:
            detected = _detect_seniority(title_lower)
            if detected:
                # If we can detect seniority, it must match config
                if not any(s in detected for s in seniority):
                    reasons["seniority_mismatch"] += 1
                    continue
            # If seniority can't be detected, let it through (err on inclusion)

        passed.append(job)

    total_filtered = len(jobs) - len(passed)
    logger.info(
        f"Filter: {len(jobs)} → {len(passed)} ({total_filtered} filtered: {reasons})"
    )
    return passed


def _detect_seniority(title: str) -> set[str]:
    """Detect seniority level(s) from a job title."""
    detected = set()
    for level, patterns in SENIORITY_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, title, re.IGNORECASE):
                detected.add(level)
                break
    return detected
