"""robots.txt compliance checker for Tier 3 scrapers."""

from __future__ import annotations

import logging
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

import httpx

from config import get_settings

logger = logging.getLogger(__name__)


class RobotsChecker:
    """
    Checks robots.txt before crawling.
    Caches parsed robots.txt per domain for the run duration.
    """

    def __init__(self):
        self._parsers: dict[str, RobotFileParser | None] = {}

    async def _fetch_robots(
        self, domain: str, client: httpx.AsyncClient
    ) -> RobotFileParser | None:
        """Fetch and parse robots.txt for a domain."""
        robots_url = f"https://{domain}/robots.txt"
        try:
            settings = get_settings()
            resp = await client.get(
                robots_url,
                headers={"User-Agent": settings.user_agent},
                timeout=10,
            )
            if resp.status_code == 200:
                parser = RobotFileParser()
                parser.parse(resp.text.splitlines())
                return parser
            else:
                # No robots.txt = everything allowed
                logger.debug(
                    f"No robots.txt at {robots_url} (status {resp.status_code})"
                )
                return None
        except Exception as e:
            logger.warning(f"Failed to fetch robots.txt for {domain}: {e}")
            return None

    async def is_allowed(self, url: str, client: httpx.AsyncClient) -> bool:
        """
        Check if crawling this URL is allowed by robots.txt.
        Returns True if allowed or if robots.txt can't be fetched.
        """
        domain = urlparse(url).netloc
        settings = get_settings()

        if domain not in self._parsers:
            self._parsers[domain] = await self._fetch_robots(domain, client)

        parser = self._parsers[domain]
        if parser is None:
            return True  # No robots.txt = allowed

        allowed = parser.can_fetch(settings.user_agent, url)
        if not allowed:
            logger.warning(f"robots.txt DISALLOWS crawling: {url}")
        return allowed
