"""
Tier 3: Custom career page scraper.

Supports static pages via BeautifulSoup and JS-heavy pages via Playwright.
Always checks robots.txt before crawling.

Config format (in .env as JSON):
CAREER_PAGES=[
  {"slug": "company", "url": "https://...", "selector": "div.job", "js_render": false},
  ...
]
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

import httpx

from compliance.robots import RobotsChecker
from config import get_settings
from sources.base import (
    BaseJobSource,
    RawJob,
    clean_html,
    extract_remote_type,
)
from storage.models import Job

logger = logging.getLogger(__name__)

_robots_checker = RobotsChecker()


class CareerPageSource(BaseJobSource):
    """
    Scrapes custom career pages for companies not on Tier 1/2 boards.
    Respects robots.txt. Uses BS4 for static pages, Playwright for JS-heavy ones.
    """

    name = "career_page"

    async def fetch(self, client: httpx.AsyncClient) -> list[RawJob]:
        settings = get_settings()
        all_jobs: list[RawJob] = []

        for page_cfg in settings.career_pages:
            slug = page_cfg.get("slug", "unknown")
            url = page_cfg.get("url", "")
            selector = page_cfg.get("selector", "")
            js_render = page_cfg.get("js_render", False)

            if not url or not selector:
                logger.warning(
                    f"[career_page/{slug}] Missing url or selector, skipping"
                )
                continue

            # Compliance: check robots.txt
            if not await _robots_checker.is_allowed(url, client):
                logger.warning(f"[career_page/{slug}] Blocked by robots.txt, skipping")
                continue

            try:
                if js_render:
                    jobs = await self._fetch_with_playwright(slug, url, selector)
                else:
                    jobs = await self._fetch_with_bs4(slug, url, selector, client)
                all_jobs.extend(jobs)
            except Exception as e:
                logger.warning(f"[career_page/{slug}] Failed: {e}")

        return all_jobs

    async def _fetch_with_bs4(
        self, slug: str, url: str, selector: str, client: httpx.AsyncClient
    ) -> list[RawJob]:
        """Fetch a static career page with BeautifulSoup."""
        from bs4 import BeautifulSoup

        settings = get_settings()
        resp = await client.get(
            url,
            timeout=settings.request_timeout,
            headers={"User-Agent": settings.user_agent},
        )
        resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "lxml")
        elements = soup.select(selector)

        jobs = []
        for i, el in enumerate(elements):
            # Try to find a link
            link_el = el.find("a", href=True)
            job_url = link_el["href"] if link_el else url  # type: ignore
            if job_url.startswith("/"):
                from urllib.parse import urljoin

                job_url = urljoin(url, job_url)

            title = el.get_text(strip=True)[:200]

            jobs.append(
                RawJob(
                    source_id=f"{slug}-{i}",
                    source_name=self.name,
                    raw_data={
                        "title": title,
                        "url": job_url,
                        "html": str(el),
                        "_company_slug": slug,
                    },
                    url=job_url,
                )
            )

        logger.info(f"[career_page/{slug}] Found {len(jobs)} jobs (BS4)")
        return jobs

    async def _fetch_with_playwright(
        self, slug: str, url: str, selector: str
    ) -> list[RawJob]:
        """Fetch a JS-rendered career page with Playwright."""
        try:
            from playwright.async_api import async_playwright  # type: ignore
        except ImportError:
            logger.warning(
                f"[career_page/{slug}] Playwright not installed. "
                "Install with: pip install playwright && playwright install chromium"
            )
            return []

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page(
                user_agent=get_settings().user_agent,
            )

            try:
                await page.goto(url, wait_until="networkidle", timeout=30000)
                elements = await page.query_selector_all(selector)

                jobs = []
                for i, el in enumerate(elements):
                    title = (await el.text_content() or "").strip()[:200]
                    link = await el.query_selector("a")
                    job_url = await link.get_attribute("href") if link else url
                    if job_url and job_url.startswith("/"):
                        from urllib.parse import urljoin

                        job_url = urljoin(url, job_url)

                    jobs.append(
                        RawJob(
                            source_id=f"{slug}-pw-{i}",
                            source_name=self.name,
                            raw_data={
                                "title": title,
                                "url": job_url or url,
                                "_company_slug": slug,
                            },
                            url=job_url or url,
                        )
                    )

                logger.info(f"[career_page/{slug}] Found {len(jobs)} jobs (Playwright)")
                return jobs

            finally:
                await browser.close()

    def normalize(self, raw: RawJob) -> Job:
        d = raw.raw_data
        slug = d.get("_company_slug", "unknown")
        title = d.get("title", "")
        description = clean_html(d.get("html", title))

        return Job(
            id=f"{self.name}:{raw.source_id}",
            source=self.name,
            title=title,
            company=slug,
            location=None,
            remote_type=extract_remote_type(title, ""),
            url=raw.url,
            description_raw=description,
            posted_date=None,
            salary_min=None,
            salary_max=None,
            fetched_at=datetime.now(timezone.utc),
        )
