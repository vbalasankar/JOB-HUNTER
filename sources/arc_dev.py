"""
Arc.dev source.

Fetches developer-focused remote jobs from Arc.dev.
Uses their public job listings endpoint.
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

API_URL = "https://arc.dev/api/jobs"


class ArcDevSource(BaseJobSource):
    """Fetches developer jobs from Arc.dev."""

    name = "arc_dev"

    async def fetch(self, client: httpx.AsyncClient) -> list[RawJob]:
        settings = get_settings()
        all_jobs: list[RawJob] = []

        try:
            resp = await client.get(
                API_URL,
                params={"page": 1, "per_page": 100},
                timeout=settings.request_timeout,
                headers={
                    "User-Agent": settings.user_agent,
                    "Accept": "application/json",
                },
            )
            resp.raise_for_status()
            data = resp.json()

            jobs_data = data if isinstance(data, list) else data.get("jobs", [])
            for job_data in jobs_data:
                job_id = str(job_data.get("id", "") or job_data.get("slug", ""))
                if not job_id:
                    continue
                slug = job_data.get("slug", job_id)
                all_jobs.append(
                    RawJob(
                        source_id=job_id,
                        source_name=self.name,
                        raw_data=job_data,
                        url=job_data.get("url", f"https://arc.dev/remote-jobs/{slug}"),
                    )
                )

            logger.info(f"[arc_dev] Fetched {len(all_jobs)} jobs")

        except Exception as e:
            logger.warning(f"[arc_dev] Failed: {e}")

        return all_jobs

    def normalize(self, raw: RawJob) -> Job:
        d = raw.raw_data

        title = d.get("title", "")
        company = d.get("company_name", "") or d.get("company", "")
        if isinstance(company, dict):
            company = company.get("name", "")
        location = d.get("location", "Remote")
        description = clean_html(d.get("description", ""))

        remote = d.get("remote", True)
        salary_min, salary_max = extract_salary_range(description)

        skills = d.get("skills", []) or d.get("technologies", [])
        if skills:
            description += f"\n\nSkills: {', '.join(skills)}"

        return Job(
            id=f"{self.name}:{raw.source_id}",
            source=self.name,
            title=title,
            company=company,
            location=location or None,
            remote_type="remote" if remote else extract_remote_type(title, location),
            url=raw.url,
            description_raw=description,
            posted_date=safe_parse_date(d.get("created_at") or d.get("published_at")),
            salary_min=salary_min,
            salary_max=salary_max,
            fetched_at=datetime.now(timezone.utc),
        )
