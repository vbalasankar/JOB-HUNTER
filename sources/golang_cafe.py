"""
Golang Cafe source.

Fetches Go-specific jobs from Golang Cafe via RSS.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

import feedparser
import httpx

from config import get_settings
from sources.base import (
    BaseJobSource,
    RawJob,
    clean_html,
    extract_remote_type,
    extract_salary_range,
    safe_parse_date,
)
from storage.models import Job

logger = logging.getLogger(__name__)

RSS_URL = "https://golang.cafe/rss"


class GolangCafeSource(BaseJobSource):
    """Fetches Go jobs from Golang Cafe RSS."""

    name = "golang_cafe"

    async def fetch(self, client: httpx.AsyncClient) -> list[RawJob]:
        settings = get_settings()
        all_jobs: list[RawJob] = []

        try:
            resp = await client.get(
                RSS_URL,
                timeout=settings.request_timeout,
                headers={"User-Agent": settings.user_agent},
            )
            resp.raise_for_status()

            feed = feedparser.parse(resp.text)
            for entry in feed.entries:
                link = entry.get("link", "")
                entry_id = entry.get("id", link)
                all_jobs.append(
                    RawJob(
                        source_id=entry_id,
                        source_name=self.name,
                        raw_data=dict(entry),
                        url=link,
                    )
                )

            logger.info(f"[golang_cafe] Fetched {len(feed.entries)} jobs")

        except Exception as e:
            logger.warning(f"[golang_cafe] Failed: {e}")

        return all_jobs

    def normalize(self, raw: RawJob) -> Job:
        d = raw.raw_data
        title_full = d.get("title", "")
        description = clean_html(d.get("summary", "") or d.get("description", ""))
        salary_min, salary_max = extract_salary_range(title_full + " " + description)

        # Golang Cafe: "Title at Company - Location"
        company = ""
        location = ""
        title = title_full

        if " at " in title_full:
            parts = title_full.split(" at ", 1)
            title = parts[0].strip()
            rest = parts[1]
            if " - " in rest:
                company, location = rest.rsplit(" - ", 1)
                company = company.strip()
                location = location.strip()
            else:
                company = rest.strip()

        return Job(
            id=f"{self.name}:{raw.source_id}",
            source=self.name,
            title=title,
            company=company,
            location=location or None,
            remote_type=extract_remote_type(title, location or description[:200]),
            url=raw.url,
            description_raw=description + "\n\nLanguage: Go",
            posted_date=safe_parse_date(d.get("published") or d.get("updated")),
            salary_min=salary_min,
            salary_max=salary_max,
            fetched_at=datetime.now(timezone.utc),
        )
