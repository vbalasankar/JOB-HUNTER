"""
Hacker News "Who is Hiring?" thread source (Tier 2).

Uses HN Algolia API to find the latest monthly thread,
then iterates child comments to extract job postings.
"""

from __future__ import annotations

import logging
import re
from datetime import datetime, timezone

import httpx

from config import get_settings
from sources.base import (
    BaseJobSource,
    RawJob,
    clean_html,
    extract_remote_type,
    extract_salary_range,
)
from storage.models import Job

logger = logging.getLogger(__name__)

# HN Algolia search API
SEARCH_URL = "https://hn.algolia.com/api/v1/search"
ITEM_URL = "https://hn.algolia.com/api/v1/items/{item_id}"


class HackerNewsSource(BaseJobSource):
    """
    Finds the latest "Ask HN: Who is Hiring?" thread
    and parses top-level comments as job postings.
    """

    name = "hackernews"

    async def _find_latest_thread(self, client: httpx.AsyncClient) -> int | None:
        """Find the latest 'Who is hiring?' thread ID."""
        try:
            resp = await client.get(
                SEARCH_URL,
                params={
                    "query": '"Ask HN: Who is hiring?"',
                    "tags": "story,author_whoishiring",
                    "hitsPerPage": 1,
                },
                timeout=get_settings().request_timeout,
            )
            resp.raise_for_status()
            data = resp.json()
            hits = data.get("hits", [])
            if hits:
                return int(hits[0]["objectID"])
        except Exception as e:
            logger.warning(f"[hackernews] Failed to find hiring thread: {e}")
        return None

    async def fetch(self, client: httpx.AsyncClient) -> list[RawJob]:
        thread_id = await self._find_latest_thread(client)
        if not thread_id:
            logger.warning("[hackernews] No hiring thread found")
            return []

        try:
            resp = await client.get(
                ITEM_URL.format(item_id=thread_id),
                timeout=get_settings().request_timeout,
            )
            resp.raise_for_status()
            data = resp.json()

            all_jobs = []
            children = data.get("children", [])

            for comment in children:
                # Only top-level comments are job postings
                text = comment.get("text", "")
                if not text or len(text) < 50:
                    continue

                comment_id = str(comment.get("id", ""))
                all_jobs.append(
                    RawJob(
                        source_id=comment_id,
                        source_name=self.name,
                        raw_data={
                            "text": text,
                            "author": comment.get("author", ""),
                            "created_at": comment.get("created_at", ""),
                            "thread_id": thread_id,
                        },
                        url=f"https://news.ycombinator.com/item?id={comment_id}",
                    )
                )

            logger.info(
                f"[hackernews] Fetched {len(all_jobs)} comments from thread {thread_id}"
            )
            return all_jobs

        except Exception as e:
            logger.warning(f"[hackernews] Failed to fetch thread {thread_id}: {e}")
            return []

    def normalize(self, raw: RawJob) -> Job:
        d = raw.raw_data
        text = clean_html(d.get("text", ""))

        # HN job posts typically start with "Company | Role | Location | ..."
        first_line = text.split("\n")[0].strip()
        parts = [p.strip() for p in re.split(r"[|/]", first_line)]

        company = parts[0] if len(parts) > 0 else "Unknown"
        title = parts[1] if len(parts) > 1 else first_line[:100]
        location = parts[2] if len(parts) > 2 else None

        # Truncate overly long company names (sometimes it's a full sentence)
        if len(company) > 60:
            company = company[:60]

        salary_min, salary_max = extract_salary_range(text)

        return Job(
            id=f"{self.name}:{raw.source_id}",
            source=self.name,
            title=title,
            company=company,
            location=location,
            remote_type=extract_remote_type(title, location or text[:200]),
            url=raw.url,
            description_raw=text,
            posted_date=None,  # Comments don't have structured dates
            salary_min=salary_min,
            salary_max=salary_max,
            fetched_at=datetime.now(timezone.utc),
        )
