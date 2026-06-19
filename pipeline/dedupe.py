"""
Deduplication — two-stage:
  1. Exact: skip if job.id already in DB
  2. Fuzzy: skip if (company, title, location) is too similar to an existing job

Uses rapidfuzz for fast fuzzy string matching.
"""

from __future__ import annotations

import hashlib
import logging
import re

from rapidfuzz import fuzz

from storage.db import get_all_dedup_hashes, get_session, job_exists
from storage.models import Job

logger = logging.getLogger(__name__)

# Fuzzy similarity threshold (0-100)
FUZZY_THRESHOLD = 85


def compute_dedup_hash(company: str, title: str, location: str | None) -> str:
    """
    Compute a deterministic hash for fuzzy dedup.
    Normalizes text before hashing so minor variations match.
    """
    norm_company = _normalize_text(company)
    norm_title = _normalize_text(title)
    norm_location = _normalize_text(location or "")

    fingerprint = f"{norm_company}|{norm_title}|{norm_location}"
    return hashlib.sha256(fingerprint.encode()).hexdigest()[:16]


def _normalize_text(text: str) -> str:
    """Lowercase, strip whitespace, remove punctuation for comparison."""
    text = text.lower().strip()
    text = re.sub(r"[^\w\s]", "", text)
    text = re.sub(r"\s+", " ", text)
    return text


def deduplicate(jobs: list[Job]) -> list[Job]:
    """
    Remove duplicates from a batch of jobs.

    Stage 1: Skip if exact job.id exists in DB
    Stage 2: Skip if fuzzy match with (company, title, location) to existing DB records
    Stage 3: Skip intra-batch duplicates
    """
    unique_jobs: list[Job] = []
    seen_ids: set[str] = set()
    seen_hashes: set[str] = set()
    skipped_exact = 0
    skipped_fuzzy = 0
    skipped_intra = 0

    with get_session() as session:
        # Load existing dedup hashes from DB
        existing_hashes = get_all_dedup_hashes(session)

        for job in jobs:
            # Stage 1: Exact ID match
            if job_exists(session, job.id):
                skipped_exact += 1
                continue

            if job.id in seen_ids:
                skipped_intra += 1
                continue
            seen_ids.add(job.id)

            # Compute dedup fingerprint
            dedup_hash = compute_dedup_hash(job.company, job.title, job.location)
            job.dedup_hash = dedup_hash

            # Stage 2: Fuzzy match against DB
            if dedup_hash in existing_hashes:
                skipped_fuzzy += 1
                continue

            # Stage 3: Fuzzy match against current batch
            if dedup_hash in seen_hashes:
                skipped_intra += 1
                continue

            # Extra fuzzy check: use rapidfuzz for titles that hash differently
            # but are semantically the same
            is_fuzzy_dup = False
            for existing_job in unique_jobs:
                title_sim = fuzz.ratio(
                    _normalize_text(job.title),
                    _normalize_text(existing_job.title),
                )
                company_sim = fuzz.ratio(
                    _normalize_text(job.company),
                    _normalize_text(existing_job.company),
                )
                if title_sim > FUZZY_THRESHOLD and company_sim > FUZZY_THRESHOLD:
                    is_fuzzy_dup = True
                    skipped_fuzzy += 1
                    break

            if not is_fuzzy_dup:
                seen_hashes.add(dedup_hash)
                unique_jobs.append(job)

    logger.info(
        f"Dedup: {len(jobs)} → {len(unique_jobs)} "
        f"(exact={skipped_exact}, fuzzy={skipped_fuzzy}, intra-batch={skipped_intra})"
    )
    return unique_jobs
