"""SQLModel schema for the jobs database."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlmodel import Field, SQLModel


class Job(SQLModel, table=True):
    """Normalized job posting — the single canonical data model."""

    __tablename__ = "jobs"

    id: str = Field(primary_key=True, description="Composite key: {source}:{source_id}")
    source: str = Field(index=True, description="Source name, e.g. greenhouse, lever")
    title: str
    company: str = Field(index=True)
    location: Optional[str] = Field(default=None)
    remote_type: Optional[str] = Field(
        default=None, description="remote | hybrid | onsite | None"
    )
    url: str
    description_raw: str
    posted_date: Optional[datetime] = Field(default=None)
    salary_min: Optional[float] = Field(default=None)
    salary_max: Optional[float] = Field(default=None)
    fetched_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    match_score: Optional[float] = Field(default=None, index=True)
    match_reasons: Optional[str] = Field(
        default=None, description="JSON-serialized list of match reasons"
    )
    notified_at: Optional[datetime] = Field(
        default=None, index=True, description="Set when notification is sent"
    )
    dedup_hash: str = Field(
        default="", index=True, description="Fuzzy dedup fingerprint"
    )


class ETagCache(SQLModel, table=True):
    """Cache for HTTP conditional request headers per URL."""

    __tablename__ = "etag_cache"

    url: str = Field(primary_key=True)
    etag: Optional[str] = Field(default=None)
    last_modified: Optional[str] = Field(default=None)
    cached_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
