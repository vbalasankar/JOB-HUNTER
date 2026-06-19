"""Per-domain async rate limiter with configurable requests/second."""

from __future__ import annotations

import asyncio
import logging
import time
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


class DomainRateLimiter:
    """
    Enforces a per-domain rate limit (default 1 req/sec).
    Thread-safe via asyncio locks per domain.
    """

    def __init__(self, default_rps: float = 1.0):
        self._default_delay = 1.0 / default_rps
        self._domain_overrides: dict[str, float] = {}
        self._last_request: dict[str, float] = {}
        self._locks: dict[str, asyncio.Lock] = {}

    def set_domain_limit(self, domain: str, rps: float) -> None:
        """Override rate limit for a specific domain."""
        self._domain_overrides[domain] = 1.0 / rps

    def _get_delay(self, domain: str) -> float:
        return self._domain_overrides.get(domain, self._default_delay)

    def _get_lock(self, domain: str) -> asyncio.Lock:
        if domain not in self._locks:
            self._locks[domain] = asyncio.Lock()
        return self._locks[domain]

    async def acquire(self, url: str) -> None:
        """Wait until it's safe to make a request to this domain."""
        domain = urlparse(url).netloc
        lock = self._get_lock(domain)

        async with lock:
            delay = self._get_delay(domain)
            last = self._last_request.get(domain, 0.0)
            elapsed = time.monotonic() - last
            if elapsed < delay:
                wait_time = delay - elapsed
                logger.debug(f"Rate limit: waiting {wait_time:.2f}s for {domain}")
                await asyncio.sleep(wait_time)
            self._last_request[domain] = time.monotonic()
