"""
Wellfound (formerly AngelList Talent) source.

Fetches startup job listings from Wellfound's public API.
Uses their GraphQL-like public endpoint for startup jobs.
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

# Wellfound public job search API
API_URL = "https://wellfound.com/api/jobs"
SEARCH_URL = "https://wellfound.com/role/r/software-engineer"


class WellfoundSource(BaseJobSource):
    """Fetches jobs from Wellfound (AngelList) startup job listings."""

    name = "wellfound"

    async def fetch(self, client: httpx.AsyncClient) -> list[RawJob]:
        settings = get_settings()
        all_jobs: list[RawJob] = []

        # Wellfound exposes a JSON endpoint for job listings
        try:
            resp = await client.get(
                "https://wellfound.com/api/v2/jobs",
                params={
                    "per_page": 100,
                    "page": 1,
                },
                timeout=settings.request_timeout,
                headers={
                    "User-Agent": settings.user_agent,
                    "Accept": "application/json",
                },
            )

            if resp.status_code == 200:
                data = resp.json()
                jobs_data = data if isinstance(data, list) else data.get("jobs", [])
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
                                "url", f"https://wellfound.com/jobs/{slug}"
                            ),
                        )
                    )
                logger.info(f"[wellfound] Fetched {len(all_jobs)} jobs")
            else:
                logger.warning(f"[wellfound] HTTP {resp.status_code}")

        except Exception as e:
            logger.warning(f"[wellfound] Failed: {e}")

        return all_jobs

    def normalize(self, raw: RawJob) -> Job:
        d = raw.raw_data
        title = d.get("title", "") or d.get("name", "")
        company_data = d.get("startup", {}) or d.get("company", {})
        if isinstance(company_data, dict):
            company = company_data.get("name", "")
        else:
            company = str(company_data)
        location = d.get("location", "") or d.get("city", "")
        description = clean_html(d.get("description", "") or d.get("body", ""))

        remote = d.get("remote", False)
        salary_min_val = d.get("salary_min")
        salary_max_val = d.get("salary_max")

        try:
            salary_min = float(salary_min_val) if salary_min_val else None
        except (ValueError, TypeError):
            salary_min = None
        try:
            salary_max = float(salary_max_val) if salary_max_val else None
        except (ValueError, TypeError):
            salary_max = None

        if salary_min is None and salary_max is None:
            salary_min, salary_max = extract_salary_range(description)

        return Job(
            id=f"{self.name}:{raw.source_id}",
            source=self.name,
            title=title,
            company=company,
            location=location or None,
            remote_type="remote" if remote else extract_remote_type(title, location),
            url=raw.url,
            description_raw=description,
            posted_date=safe_parse_date(d.get("published_at") or d.get("created_at")),
            salary_min=salary_min,
            salary_max=salary_max,
            fetched_at=datetime.now(timezone.utc),
        )
