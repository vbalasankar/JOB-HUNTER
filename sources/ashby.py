"""
Ashby job board API source (Tier 1).

API: https://api.ashbyhq.com/posting-api/job-board/{company}
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

BASE_URL = "https://api.ashbyhq.com/posting-api/job-board/{slug}"


class AshbySource(BaseJobSource):
    """Fetches jobs from Ashby job board API for configured companies."""

    name = "ashby"

    def __init__(self, companies: list[str] | None = None):
        self.companies = companies or get_settings().ashby_companies_list

    async def fetch(self, client: httpx.AsyncClient) -> list[RawJob]:
        all_jobs: list[RawJob] = []

        for slug in self.companies:
            url = BASE_URL.format(slug=slug)
            try:
                resp = await client.get(
                    url,
                    timeout=get_settings().request_timeout,
                )
                resp.raise_for_status()
                data = resp.json()

                jobs_data = data.get("jobs", [])
                for job_data in jobs_data:
                    job_url = (
                        job_data.get("jobUrl")
                        or f"https://jobs.ashbyhq.com/{slug}/{job_data.get('id', '')}"
                    )
                    all_jobs.append(
                        RawJob(
                            source_id=str(job_data.get("id", "")),
                            source_name=self.name,
                            raw_data={**job_data, "_company_slug": slug},
                            url=job_url,
                        )
                    )

                logger.info(f"[ashby/{slug}] Fetched {len(jobs_data)} jobs")

            except httpx.HTTPStatusError as e:
                logger.warning(f"[ashby/{slug}] HTTP {e.response.status_code}: {e}")
            except Exception as e:
                logger.warning(f"[ashby/{slug}] Failed: {e}")

        return all_jobs

    def normalize(self, raw: RawJob) -> Job:
        d = raw.raw_data
        slug = d.get("_company_slug", "")

        title = d.get("title", "")
        location = d.get("location", "")
        department = d.get("department", "")

        # Ashby may provide description as HTML
        description = clean_html(d.get("descriptionHtml", "")) or d.get(
            "description", ""
        )
        if department:
            description = f"Department: {department}\n\n{description}"

        salary_min, salary_max = extract_salary_range(description)

        # Ashby provides publishedAt
        published = d.get("publishedAt") or d.get("createdAt")

        # Check for employment type / remote info
        employment_type = d.get("employmentType", "")
        is_remote = d.get("isRemote", False)
        remote_type = "remote" if is_remote else extract_remote_type(title, location)

        return Job(
            id=f"{self.name}:{raw.source_id}",
            source=self.name,
            title=title,
            company=slug,
            location=location or None,
            remote_type=remote_type,
            url=raw.url,
            description_raw=description,
            posted_date=safe_parse_date(published),
            salary_min=salary_min,
            salary_max=salary_max,
            fetched_at=datetime.now(timezone.utc),
        )
