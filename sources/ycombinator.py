"""
YC Work at a Startup source.

Uses the Algolia-powered search behind workatastartup.com
to fetch startup job listings from Y Combinator companies.
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

# YC uses Algolia for job search
ALGOLIA_URL = "https://45bwzj1sgc-dsn.algolia.net/1/indexes/*/queries"
ALGOLIA_APP_ID = "45BWZJ1SGC"
settings = get_settings()
ALGOLIA_API_KEY = settings.ycombinator_algolia_key


class YCombinatorSource(BaseJobSource):
    """Fetches jobs from YC Work at a Startup via Algolia search."""

    name = "ycombinator"

    async def fetch(self, client: httpx.AsyncClient) -> list[RawJob]:
        settings = get_settings()
        all_jobs: list[RawJob] = []

        try:
            # Use the public Algolia endpoint that powers workatastartup.com
            resp = await client.post(
                ALGOLIA_URL,
                headers={
                    "User-Agent": settings.user_agent,
                    "X-Algolia-Application-Id": ALGOLIA_APP_ID,
                    "X-Algolia-API-Key": ALGOLIA_API_KEY,
                    "Content-Type": "application/json",
                },
                json={
                    "requests": [
                        {
                            "indexName": "WaaSJobs_production",
                            "params": "hitsPerPage=100&page=0",
                        }
                    ]
                },
                timeout=settings.request_timeout,
            )

            if resp.status_code == 200:
                data = resp.json()
                results = data.get("results", [])
                if results:
                    hits = results[0].get("hits", [])
                    for hit in hits:
                        job_id = str(hit.get("objectID", ""))
                        if not job_id:
                            continue
                        all_jobs.append(
                            RawJob(
                                source_id=job_id,
                                source_name=self.name,
                                raw_data=hit,
                                url=hit.get(
                                    "url",
                                    f"https://www.workatastartup.com/jobs/{job_id}",
                                ),
                            )
                        )
                    logger.info(
                        f"[ycombinator] Fetched {len(all_jobs)} jobs via Algolia"
                    )
            else:
                # Fallback: try the simpler API
                logger.info("[ycombinator] Algolia failed, trying public listing")
                resp2 = await client.get(
                    "https://www.workatastartup.com/companies.json",
                    timeout=settings.request_timeout,
                    headers={"User-Agent": settings.user_agent},
                )
                if resp2.status_code == 200:
                    companies = resp2.json()
                    for company in companies[:50]:  # Limit to avoid overload
                        for job in company.get("jobs", []):
                            job_id = str(job.get("id", ""))
                            if not job_id:
                                continue
                            job["_company"] = company.get("name", "")
                            job["_company_url"] = company.get("url", "")
                            all_jobs.append(
                                RawJob(
                                    source_id=job_id,
                                    source_name=self.name,
                                    raw_data=job,
                                    url=job.get(
                                        "url",
                                        f"https://www.workatastartup.com/jobs/{job_id}",
                                    ),
                                )
                            )
                    logger.info(
                        f"[ycombinator] Fetched {len(all_jobs)} jobs via companies.json"
                    )

        except Exception as e:
            logger.warning(f"[ycombinator] Failed: {e}")

        return all_jobs

    def normalize(self, raw: RawJob) -> Job:
        d = raw.raw_data

        title = d.get("title", "") or d.get("job_title", "")
        company = d.get("company_name", "") or d.get("_company", "")
        location = d.get("location", "") or d.get("pretty_location", "")
        description = clean_html(d.get("description", "") or d.get("body", ""))

        remote = d.get("remote", False)
        salary_min, salary_max = extract_salary_range(description)

        # Try structured salary
        if d.get("salary_min"):
            try:
                salary_min = float(d["salary_min"])
            except (ValueError, TypeError):
                pass
        if d.get("salary_max"):
            try:
                salary_max = float(d["salary_max"])
            except (ValueError, TypeError):
                pass

        return Job(
            id=f"{self.name}:{raw.source_id}",
            source=self.name,
            title=title,
            company=company,
            location=location or None,
            remote_type="remote" if remote else extract_remote_type(title, location),
            url=raw.url,
            description_raw=description,
            posted_date=None,
            salary_min=salary_min,
            salary_max=salary_max,
            fetched_at=datetime.now(timezone.utc),
        )
