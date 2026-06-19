"""
Himalayas.app source.

Fetches remote jobs from the Himalayas public JSON API.
API: https://himalayas.app/jobs/api
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
    extract_salary_range,
    safe_parse_date,
)
from storage.models import Job

logger = logging.getLogger(__name__)

API_URL = "https://himalayas.app/jobs/api"


class HimalayasSource(BaseJobSource):
    """Fetches remote jobs from Himalayas.app JSON API."""

    name = "himalayas"

    async def fetch(self, client: httpx.AsyncClient) -> list[RawJob]:
        settings = get_settings()
        all_jobs: list[RawJob] = []

        try:
            resp = await client.get(
                API_URL,
                params={"limit": 100, "offset": 0},
                timeout=settings.request_timeout,
                headers={
                    "User-Agent": settings.user_agent,
                    "Accept": "application/json",
                },
            )
            resp.raise_for_status()
            data = resp.json()

            jobs_data = data.get("jobs", []) if isinstance(data, dict) else data
            for job_data in jobs_data:
                job_id = str(job_data.get("id", ""))
                if not job_id:
                    continue
                slug = job_data.get("slug", job_id)
                all_jobs.append(
                    RawJob(
                        source_id=job_id,
                        source_name=self.name,
                        raw_data=job_data,
                        url=job_data.get(
                            "applicationUrl", f"https://himalayas.app/jobs/{slug}"
                        ),
                    )
                )

            logger.info(f"[himalayas] Fetched {len(all_jobs)} jobs")

        except Exception as e:
            logger.warning(f"[himalayas] Failed: {e}")

        return all_jobs

    def normalize(self, raw: RawJob) -> Job:
        d = raw.raw_data

        title = d.get("title", "")
        company = d.get("companyName", "") or d.get("company", "")
        location = d.get("location", "Remote")
        description = clean_html(d.get("description", ""))

        salary_min = d.get("minSalary")
        salary_max = d.get("maxSalary")
        try:
            salary_min = float(salary_min) if salary_min else None
        except (ValueError, TypeError):
            salary_min = None
        try:
            salary_max = float(salary_max) if salary_max else None
        except (ValueError, TypeError):
            salary_max = None

        if salary_min is None and salary_max is None:
            salary_min, salary_max = extract_salary_range(description)

        categories = d.get("categories", [])
        if categories:
            description += f"\n\nCategories: {', '.join(categories)}"

        return Job(
            id=f"{self.name}:{raw.source_id}",
            source=self.name,
            title=title,
            company=company,
            location=location or None,
            remote_type="remote",
            url=raw.url,
            description_raw=description,
            posted_date=safe_parse_date(d.get("pubDate") or d.get("publishedAt")),
            salary_min=salary_min,
            salary_max=salary_max,
            fetched_at=datetime.now(timezone.utc),
        )
