"""
Lever job board API source (Tier 1).

API: https://api.lever.co/v0/postings/{company}?mode=json
Public JSON API — no authentication needed.
"""

from __future__ import annotations

import logging
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

BASE_URL = "https://api.lever.co/v0/postings/{slug}"


class LeverSource(BaseJobSource):
    """Fetches jobs from Lever postings API for configured companies."""

    name = "lever"

    def __init__(self, companies: list[str] | None = None):
        self.companies = companies or get_settings().lever_companies_list

    async def fetch(self, client: httpx.AsyncClient) -> list[RawJob]:
        all_jobs: list[RawJob] = []

        for slug in self.companies:
            url = BASE_URL.format(slug=slug)
            try:
                resp = await client.get(
                    url,
                    params={"mode": "json"},
                    timeout=get_settings().request_timeout,
                )
                resp.raise_for_status()
                data = resp.json()

                if not isinstance(data, list):
                    logger.warning(f"[lever/{slug}] Unexpected response format")
                    continue

                for job_data in data:
                    all_jobs.append(
                        RawJob(
                            source_id=str(job_data.get("id", "")),
                            source_name=self.name,
                            raw_data={**job_data, "_company_slug": slug},
                            url=job_data.get("hostedUrl", ""),
                        )
                    )

                logger.info(f"[lever/{slug}] Fetched {len(data)} jobs")

            except httpx.HTTPStatusError as e:
                if e.response.status_code == 404:
                    logger.debug(f"[lever/{slug}] Board not found (404) — skipping")
                else:
                    logger.warning(f"[lever/{slug}] HTTP {e.response.status_code}: {e}")
            except Exception as e:
                logger.warning(f"[lever/{slug}] Failed: {e}")

        return all_jobs

    def normalize(self, raw: RawJob) -> Job:
        d = raw.raw_data
        slug = d.get("_company_slug", "")

        # Lever uses categories object
        categories = d.get("categories", {})
        location = categories.get("location", "")

        # Build description from description + additional + lists
        parts = []
        if d.get("descriptionPlain"):
            parts.append(d["descriptionPlain"])
        for lst in d.get("lists", []):
            parts.append(lst.get("text", ""))
            parts.append(clean_html(lst.get("content", "")))
        if d.get("additional"):
            parts.append(clean_html(d["additional"]))

        description = "\n".join(p for p in parts if p)
        title = d.get("text", "")
        salary_min, salary_max = extract_salary_range(description)

        # Lever provides createdAt as millisecond timestamp
        created_ms = d.get("createdAt")
        posted = (
            datetime.fromtimestamp(created_ms / 1000, tz=timezone.utc)
            if created_ms
            else None
        )

        return Job(
            id=f"{self.name}:{raw.source_id}",
            source=self.name,
            title=title,
            company=slug,
            location=location or None,
            remote_type=extract_remote_type(title, location),
            url=raw.url,
            description_raw=description,
            posted_date=posted,
            salary_min=salary_min,
            salary_max=salary_max,
            fetched_at=datetime.now(timezone.utc),
        )
