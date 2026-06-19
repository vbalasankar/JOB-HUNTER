"""Pydantic models for normalized news articles."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class NewsItem(BaseModel):
    """A single news article from any source."""

    id: str
    title: str
    url: str
    source: str
    published_at: Optional[datetime] = None
    summary: str = ""
    tags: list[str] = []
    author: str = ""
    points: Optional[int] = None
    comment_count: Optional[int] = None
