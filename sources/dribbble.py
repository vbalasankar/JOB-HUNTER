"""
Dribbble Jobs source.

Fetches design jobs from Dribbble via RSS feed.
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

RSS_URL = "https://dribbble.com/jobs.rss"


class DribbbleSource(BaseJobSource):
    """Fetches design jobs from Dribbble RSS."""

    name = "dribbble"

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

            logger.info(f"[dribbble] Fetched {len(feed.entries)} jobs")

        except Exception as e:
            logger.warning(f"[dribbble] Failed: {e}")

        return all_jobs

    def normalize(self, raw: RawJob) -> Job:
        d = raw.raw_data
        title = d.get("title", "")
        description = clean_html(d.get("summary", "") or d.get("description", ""))
        salary_min, salary_max = extract_salary_range(description)

        company = d.get("author", "")
        if not company and " at " in title:
            parts = title.rsplit(" at ", 1)
            title = parts[0].strip()
            company = parts[1].strip()

        return Job(
            id=f"{self.name}:{raw.source_id}",
            source=self.name,
            title=title,
            company=company,
            location=None,
            remote_type=extract_remote_type(title, description[:200]),
            url=raw.url,
            description_raw=description,
            posted_date=safe_parse_date(d.get("published") or d.get("updated")),
            salary_min=salary_min,
            salary_max=salary_max,
            fetched_at=datetime.now(timezone.utc),
        )
