"""
Greenhouse job board API source (Tier 1).

API: https://boards-api.greenhouse.io/v1/boards/{company}/jobs?content=true
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
    safe_parse_date,
)
from storage.models import Job

logger = logging.getLogger(__name__)

BASE_URL = "https://boards-api.greenhouse.io/v1/boards/{slug}/jobs"


class GreenhouseSource(BaseJobSource):
    """Fetches jobs from Greenhouse board API for configured companies."""

    name = "greenhouse"

    def __init__(self, companies: list[str] | None = None):
        self.companies = companies or get_settings().greenhouse_companies_list

    async def fetch(self, client: httpx.AsyncClient) -> list[RawJob]:
        all_jobs: list[RawJob] = []

        for slug in self.companies:
            url = BASE_URL.format(slug=slug)
            try:
                resp = await client.get(
                    url,
                    params={"content": "true"},
                    timeout=get_settings().request_timeout,
                )
                resp.raise_for_status()
                data = resp.json()

                jobs_data = data.get("jobs", [])
                for job_data in jobs_data:
                    all_jobs.append(
                        RawJob(
                            source_id=str(job_data.get("id", "")),
                            source_name=self.name,
                            raw_data={**job_data, "_company_slug": slug},
                            url=job_data.get("absolute_url", ""),
                        )
                    )

                logger.info(f"[greenhouse/{slug}] Fetched {len(jobs_data)} jobs")

            except httpx.HTTPStatusError as e:
                if e.response.status_code == 404:
                    logger.debug(
                        f"[greenhouse/{slug}] Board not found (404) — skipping"
                    )
                else:
                    logger.warning(
                        f"[greenhouse/{slug}] HTTP {e.response.status_code}: {e}"
                    )
            except Exception as e:
                logger.warning(f"[greenhouse/{slug}] Failed: {e}")

        return all_jobs

    def normalize(self, raw: RawJob) -> Job:
        d = raw.raw_data
        location_data = d.get("location", {})
        location = (
            location_data.get("name") if isinstance(location_data, dict) else None
        )

        # Get description from content field
        description = clean_html(d.get("content", ""))

        title = d.get("title", "")
        salary_min, salary_max = extract_salary_range(description)

        return Job(
            id=f"{self.name}:{raw.source_id}",
            source=self.name,
            title=title,
            company=d.get("_company_slug", ""),
            location=location,
            remote_type=extract_remote_type(title, location),
            url=raw.url,
            description_raw=description,
            posted_date=safe_parse_date(d.get("updated_at")),
            salary_min=salary_min,
            salary_max=salary_max,
            fetched_at=datetime.now(timezone.utc),
        )
