"""
RemoteOK API source (Tier 2).

API: https://remoteok.com/api
Returns JSON array — first element is metadata, rest are jobs.
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

API_URL = "https://remoteok.com/api"


class RemoteOKSource(BaseJobSource):
    """Fetches jobs from the RemoteOK JSON API."""

    name = "remoteok"

    async def fetch(self, client: httpx.AsyncClient) -> list[RawJob]:
        try:
            resp = await client.get(
                API_URL,
                timeout=get_settings().request_timeout,
                headers={
                    "User-Agent": get_settings().user_agent,
                    "Accept": "application/json",
                },
            )
            resp.raise_for_status()
            data = resp.json()

            # First element is metadata/legal notice, skip it
            jobs_data = data[1:] if isinstance(data, list) and len(data) > 1 else []

            all_jobs = []
            for job_data in jobs_data:
                job_id = str(job_data.get("id", ""))
                if not job_id:
                    continue
                all_jobs.append(
                    RawJob(
                        source_id=job_id,
                        source_name=self.name,
                        raw_data=job_data,
                        url=job_data.get(
                            "url", f"https://remoteok.com/remote-jobs/{job_id}"
                        ),
                    )
                )

            logger.info(f"[remoteok] Fetched {len(all_jobs)} jobs")
            return all_jobs

        except Exception as e:
            logger.warning(f"[remoteok] Failed: {e}")
            return []

    def normalize(self, raw: RawJob) -> Job:
        d = raw.raw_data

        title = d.get("position", "")
        company = d.get("company", "")
        location = d.get("location", "Worldwide")
        description = clean_html(d.get("description", ""))

        # RemoteOK provides salary as strings
        salary_min_str = d.get("salary_min")
        salary_max_str = d.get("salary_max")
        try:
            salary_min = float(salary_min_str) if salary_min_str else None
        except (ValueError, TypeError):
            salary_min = None
        try:
            salary_max = float(salary_max_str) if salary_max_str else None
        except (ValueError, TypeError):
            salary_max = None

        # If no explicit salary, try extracting from description
        if salary_min is None and salary_max is None:
            salary_min, salary_max = extract_salary_range(description)

        # Tags can provide additional context
        tags = d.get("tags", [])
        if tags:
            description += f"\n\nTags: {', '.join(tags)}"

        return Job(
            id=f"{self.name}:{raw.source_id}",
            source=self.name,
            title=title,
            company=company,
            location=location,
            remote_type="remote",  # RemoteOK is all remote
            url=raw.url,
            description_raw=description,
            posted_date=safe_parse_date(d.get("date")),
            salary_min=salary_min,
            salary_max=salary_max,
            fetched_at=datetime.now(timezone.utc),
        )
