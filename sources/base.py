"""
Base classes for the job source plugin system.

Every source implements BaseJobSource with:
  - fetch() → list[RawJob]  (async, gets raw data)
  - normalize(RawJob) → Job  (converts to canonical schema)

Adding a new source = one file, one class, register in main.py.
"""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any

import httpx
from pydantic import BaseModel

from storage.models import Job


class RawJob(BaseModel):
    """Raw job data as received from a source, before normalization."""

    source_id: str
    source_name: str
    raw_data: dict[str, Any]
    url: str


class BaseJobSource(ABC):
    """Plugin interface — every source implements this."""

    name: str = "base"

    @abstractmethod
    async def fetch(self, client: httpx.AsyncClient) -> list[RawJob]:
        """
        Fetch job postings from this source.
        Must handle errors gracefully and return [] on failure.
        """
        ...

    @abstractmethod
    def normalize(self, raw: RawJob) -> Job:
        """Convert a RawJob to the canonical Job model."""
        ...

    def normalize_all(self, raws: list[RawJob]) -> list[Job]:
        """Normalize a batch of raw jobs, skipping failures."""
        import logging

        logger = logging.getLogger(__name__)
        jobs: list[Job] = []
        for raw in raws:
            try:
                jobs.append(self.normalize(raw))
            except Exception as e:
                logger.warning(
                    f"[{self.name}] Failed to normalize job {raw.source_id}: {e}"
                )
        return jobs


# ---------- Shared utilities ----------


def extract_remote_type(title: str, location: str | None) -> str | None:
    """Heuristic to extract remote/hybrid/onsite from title and location."""
    combined = f"{title} {location or ''}".lower()
    if re.search(r"\bremote\b", combined):
        if re.search(r"\bhybrid\b", combined):
            return "hybrid"
        return "remote"
    if re.search(r"\bhybrid\b", combined):
        return "hybrid"
    if re.search(r"\bon[- ]?site\b", combined):
        return "onsite"
    return None


_SALARY_PATTERN = re.compile(
    r"[\$€£₹]?\s*(\d{2,3}[,.]?\d{3})\s*[-–—to]+\s*[\$€£₹]?\s*(\d{2,3}[,.]?\d{3})",
    re.IGNORECASE,
)


def extract_salary_range(text: str) -> tuple[float | None, float | None]:
    """Extract salary min/max from text via regex."""
    match = _SALARY_PATTERN.search(text)
    if match:
        try:
            low = float(match.group(1).replace(",", "").replace(".", ""))
            high = float(match.group(2).replace(",", "").replace(".", ""))
            return low, high
        except ValueError:
            pass
    return None, None


def clean_html(html: str) -> str:
    """Strip HTML tags to get plain text."""
    from bs4 import BeautifulSoup

    if "<" in html and ">" in html:
        return BeautifulSoup(html, "lxml").get_text(separator=" ", strip=True)
    return html


def safe_parse_date(date_str: str | None) -> datetime | None:
    """Try multiple date formats."""
    if not date_str:
        return None
    from dateutil import parser as dateutil_parser

    try:
        return dateutil_parser.parse(date_str)
    except (ValueError, TypeError):
        return None
