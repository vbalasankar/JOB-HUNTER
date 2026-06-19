"""
Built In source.

Fetches tech jobs from Built In via RSS feeds for various tech hubs.
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
    extract_salary_range,
    safe_parse_date,
)
from storage.models import Job

logger = logging.getLogger(__name__)

RSS_FEEDS = [
    "https://builtin.com/jobs/remote/dev-engineering/entry-level/rss",
    "https://builtin.com/jobs/remote/dev-engineering/mid-level/rss",
    "https://builtin.com/jobs/remote/dev-engineering/senior/rss",
    "https://builtin.com/jobs/remote/data-analytics/mid-level/rss",
    "https://builtin.com/jobs/remote/data-analytics/senior/rss",
]


class BuiltInSource(BaseJobSource):
    """Fetches tech jobs from Built In RSS feeds."""

    name = "builtin"

    async def fetch(self, client: httpx.AsyncClient) -> list[RawJob]:
        settings = get_settings()
        all_jobs: list[RawJob] = []

        for feed_url in RSS_FEEDS:
            try:
                resp = await client.get(
                    feed_url,
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

                logger.info(
                    f"[builtin] Fetched {len(feed.entries)} jobs from {feed_url}"
                )

            except Exception as e:
                logger.warning(f"[builtin] Failed for {feed_url}: {e}")

        return all_jobs

    def normalize(self, raw: RawJob) -> Job:
        d = raw.raw_data
        title = d.get("title", "")
        description = clean_html(d.get("summary", "") or d.get("description", ""))
        salary_min, salary_max = extract_salary_range(description)

        # Try to extract company from title or author
        company = d.get("author", "")
        if not company and " at " in title:
            parts = title.rsplit(" at ", 1)
            title = parts[0].strip()
            company = parts[1].strip()

        published = d.get("published") or d.get("updated")

        return Job(
            id=f"{self.name}:{raw.source_id}",
            source=self.name,
            title=title,
            company=company,
            location="Remote",
            remote_type="remote",
            url=raw.url,
            description_raw=description,
            posted_date=safe_parse_date(published),
            salary_min=salary_min,
            salary_max=salary_max,
            fetched_at=datetime.now(timezone.utc),
        )
