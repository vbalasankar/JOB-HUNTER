"""Database operations — SQLite via SQLModel."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path

from sqlmodel import Session, SQLModel, create_engine, select

from config import get_settings
from storage.models import ETagCache, Job

logger = logging.getLogger(__name__)


def _get_engine():
    settings = get_settings()
    db_path = Path(settings.db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    url = f"sqlite:///{db_path}"
    return create_engine(url, echo=False)


_engine = None


def get_engine():
    global _engine
    if _engine is None:
        _engine = _get_engine()
        SQLModel.metadata.create_all(_engine)
    return _engine


def get_session() -> Session:
    return Session(get_engine(), expire_on_commit=False)


# ---------- Job CRUD ----------


def job_exists(session: Session, job_id: str) -> bool:
    """Check if a job with this exact ID already exists."""
    return session.get(Job, job_id) is not None


def find_by_dedup_hash(session: Session, dedup_hash: str) -> Job | None:
    """Find a job by its fuzzy dedup hash."""
    stmt = select(Job).where(Job.dedup_hash == dedup_hash)
    return session.exec(stmt).first()


def upsert_job(session: Session, job: Job) -> bool:
    """
    Insert or update a job.
    Returns True if this was a new insert, False if updated.
    """
    existing = session.get(Job, job.id)
    if existing:
        # Update score fields but preserve notification state
        existing.match_score = job.match_score
        existing.match_reasons = job.match_reasons
        existing.fetched_at = job.fetched_at
        session.add(existing)
        return False
    else:
        session.add(job)
        return True


def bulk_upsert_jobs(jobs: list[Job]) -> tuple[int, int]:
    """
    Upsert a batch of jobs.
    Returns (new_count, updated_count).
    """
    new_count, updated_count = 0, 0
    with get_session() as session:
        for job in jobs:
            is_new = upsert_job(session, job)
            if is_new:
                new_count += 1
            else:
                updated_count += 1
        session.commit()
    logger.info(f"DB: {new_count} new, {updated_count} updated")
    return new_count, updated_count


def get_unnotified_matches(threshold: float) -> list[Job]:
    """Get jobs above threshold that haven't been notified yet."""
    with get_session() as session:
        stmt = (
            select(Job)
            .where(Job.match_score >= threshold)  # type: ignore[operator]
            .where(Job.notified_at.is_(None))  # type: ignore[union-attr]
            .order_by(Job.match_score.desc())  # type: ignore[union-attr]
        )
        results = list(session.exec(stmt).all())
        # Expunge so objects can be accessed after session closes
        for r in results:
            session.expunge(r)
        return results


def mark_notified(job_ids: list[str]) -> None:
    """Mark jobs as notified so they're never re-sent."""
    now = datetime.now(timezone.utc)
    with get_session() as session:
        for jid in job_ids:
            job = session.get(Job, jid)
            if job:
                job.notified_at = now
                session.add(job)
        session.commit()
    logger.info(f"Marked {len(job_ids)} jobs as notified")


def get_all_dedup_hashes(session: Session) -> set[str]:
    """Get all existing dedup hashes for fuzzy matching."""
    stmt = select(Job.dedup_hash).where(Job.dedup_hash != "")
    return set(session.exec(stmt).all())


def get_total_job_count() -> int:
    with get_session() as session:
        stmt = select(Job)
        return len(session.exec(stmt).all())


# ---------- ETag Cache ----------


def get_etag(url: str) -> tuple[str | None, str | None]:
    """Get cached ETag and Last-Modified for a URL."""
    with get_session() as session:
        cached = session.get(ETagCache, url)
        if cached:
            return cached.etag, cached.last_modified
    return None, None


def save_etag(url: str, etag: str | None, last_modified: str | None) -> None:
    """Save ETag/Last-Modified from a response."""
    with get_session() as session:
        existing = session.get(ETagCache, url)
        if existing:
            existing.etag = etag
            existing.last_modified = last_modified
            existing.cached_at = datetime.now(timezone.utc)
            session.add(existing)
        else:
            session.add(
                ETagCache(
                    url=url,
                    etag=etag,
                    last_modified=last_modified,
                )
            )
        session.commit()
