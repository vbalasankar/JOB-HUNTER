"""
Remotive source.

Fetches remote jobs from the Remotive public JSON API.
API: https://remotive.com/api/remote-jobs
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

API_URL = "https://remotive.com/api/remote-jobs"


class RemotiveSource(BaseJobSource):
    """Fetches remote jobs from Remotive JSON API."""

    name = "remotive"

    async def fetch(self, client: httpx.AsyncClient) -> list[RawJob]:
        settings = get_settings()
        all_jobs: list[RawJob] = []

        try:
            resp = await client.get(
                API_URL,
                params={"limit": 100},
                timeout=settings.request_timeout,
                headers={
                    "User-Agent": settings.user_agent,
                    "Accept": "application/json",
                },
            )
            resp.raise_for_status()
            data = resp.json()

            jobs_data = data.get("jobs", [])
            for job_data in jobs_data:
                job_id = str(job_data.get("id", ""))
                if not job_id:
                    continue
                all_jobs.append(
                    RawJob(
                        source_id=job_id,
                        source_name=self.name,
                        raw_data=job_data,
                        url=job_data.get("url", ""),
                    )
                )

            logger.info(f"[remotive] Fetched {len(all_jobs)} jobs")

        except Exception as e:
            logger.warning(f"[remotive] Failed: {e}")

        return all_jobs

    def normalize(self, raw: RawJob) -> Job:
        d = raw.raw_data

        title = d.get("title", "")
        company = d.get("company_name", "")
        location = d.get("candidate_required_location", "Worldwide")
        description = clean_html(d.get("description", ""))

        salary = d.get("salary", "")
        salary_min, salary_max = extract_salary_range(salary or description)

        category = d.get("category", "")
        job_type = d.get("job_type", "")
        if category:
            description += f"\n\nCategory: {category}"
        if job_type:
            description += f"\nType: {job_type}"

        tags = d.get("tags", [])
        if tags:
            description += f"\nTags: {', '.join(tags)}"

        return Job(
            id=f"{self.name}:{raw.source_id}",
            source=self.name,
            title=title,
            company=company,
            location=location or None,
            remote_type="remote",
            url=raw.url,
            description_raw=description,
            posted_date=safe_parse_date(d.get("publication_date")),
            salary_min=salary_min,
            salary_max=salary_max,
            fetched_at=datetime.now(timezone.utc),
        )
