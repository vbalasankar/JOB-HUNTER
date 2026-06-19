"""
Arbeitnow API source (Tier 2).

API: https://www.arbeitnow.com/api/job-board-api
Paginated JSON API, free and public.
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

API_URL = "https://www.arbeitnow.com/api/job-board-api"


class ArbeitnowSource(BaseJobSource):
    """Fetches jobs from the Arbeitnow API."""

    name = "arbeitnow"

    async def fetch(self, client: httpx.AsyncClient) -> list[RawJob]:
        all_jobs: list[RawJob] = []
        page = 1
        max_pages = 3  # Don't crawl too deep

        while page <= max_pages:
            try:
                resp = await client.get(
                    API_URL,
                    params={"page": page},
                    timeout=get_settings().request_timeout,
                    headers={"User-Agent": get_settings().user_agent},
                )
                resp.raise_for_status()
                data = resp.json()

                jobs_data = data.get("data", [])
                if not jobs_data:
                    break

                for job_data in jobs_data:
                    slug = job_data.get("slug", "")
                    all_jobs.append(
                        RawJob(
                            source_id=slug or str(job_data.get("id", "")),
                            source_name=self.name,
                            raw_data=job_data,
                            url=job_data.get(
                                "url", f"https://www.arbeitnow.com/view/{slug}"
                            ),
                        )
                    )

                # Check for next page
                if not data.get("links", {}).get("next"):
                    break
                page += 1

            except Exception as e:
                logger.warning(f"[arbeitnow] Failed on page {page}: {e}")
                break

        logger.info(f"[arbeitnow] Fetched {len(all_jobs)} jobs across {page} pages")
        return all_jobs

    def normalize(self, raw: RawJob) -> Job:
        d = raw.raw_data

        title = d.get("title", "")
        company = d.get("company_name", "")
        location = d.get("location", "")
        description = clean_html(d.get("description", ""))

        remote = d.get("remote", False)
        tags = d.get("tags", [])

        salary_min, salary_max = extract_salary_range(description)

        # Arbeitnow provides created_at timestamp
        created = d.get("created_at")
        posted = None
        if created:
            try:
                posted = datetime.fromtimestamp(int(created), tz=timezone.utc)
            except (ValueError, TypeError):
                posted = safe_parse_date(str(created))

        if tags:
            description += f"\n\nTags: {', '.join(tags)}"

        return Job(
            id=f"{self.name}:{raw.source_id}",
            source=self.name,
            title=title,
            company=company,
            location=location or None,
            remote_type="remote" if remote else extract_remote_type(title, location),
            url=raw.url,
            description_raw=description,
            posted_date=posted,
            salary_min=salary_min,
            salary_max=salary_max,
            fetched_at=datetime.now(timezone.utc),
        )
