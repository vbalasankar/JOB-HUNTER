"""
News aggregator — fetches tech news from multiple sources.

Sources:
  - Hacker News (top stories via API)
  - TechCrunch (RSS)
  - The Verge (RSS)
  - Ars Technica (RSS)
  - Dev.to (API)
  - Product Hunt (RSS)

Results are cached in-memory with a configurable TTL.
"""

from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from typing import Any

import feedparser
import httpx

from config import get_settings
from news.models import NewsItem

logger = logging.getLogger(__name__)

# In-memory cache
_cache: dict[str, Any] = {
    "items": [],
    "fetched_at": 0,
}


async def get_news(
    skills: list[str] | None = None,
    roles: list[str] | None = None,
    limit: int = 50,
) -> list[NewsItem]:
    """
    Get aggregated tech news, optionally filtered by skills/roles.
    Uses in-memory cache with TTL from config.
    """
    settings = get_settings()
    now = time.time()

    # Check cache
    if (
        _cache["items"]
        and (now - _cache["fetched_at"]) < settings.news_cache_ttl_seconds
    ):
        items = _cache["items"]
    else:
        items = await _fetch_all_news()
        _cache["items"] = items
        _cache["fetched_at"] = now

    # Filter by skills/roles if provided
    if skills or roles:
        keywords: set[str] = set()
        if skills:
            keywords.update(s.lower() for s in skills)
        if roles:
            keywords.update(r.lower() for r in roles)

        if keywords:
            scored: list[tuple[int, NewsItem]] = []
            for item in items:
                searchable = (
                    f"{item.title} {item.summary} {' '.join(item.tags)}".lower()
                )
                score = len([kw for kw in keywords if kw in searchable])
                scored.append((score, item))

            # Sort: matching items first (by score desc), then the rest
            scored.sort(key=lambda x: x[0], reverse=True)
            items = [item for _, item in scored]

    return items[:limit]


async def _fetch_all_news() -> list[NewsItem]:
    """Fetch news from all enabled sources concurrently."""
    settings = get_settings()
    enabled = set(settings.news_sources_list)

    all_items: list[NewsItem] = []

    async with httpx.AsyncClient(
        headers={"User-Agent": settings.user_agent},
        follow_redirects=True,
        timeout=15,
    ) as client:
        # Hacker News
        if "hackernews" in enabled:
            try:
                items = await _fetch_hackernews(client)
                all_items.extend(items)
            except Exception as e:
                logger.warning(f"[news/hackernews] Failed: {e}")

        # RSS-based sources
        rss_sources = {
            "techcrunch": ("TechCrunch", "https://techcrunch.com/feed/"),
            "theverge": ("The Verge", "https://www.theverge.com/rss/index.xml"),
            "arstechnica": (
                "Ars Technica",
                "https://feeds.arstechnica.com/arstechnica/index",
            ),
            "producthunt": ("Product Hunt", "https://www.producthunt.com/feed"),
        }

        for source_key, (source_name, feed_url) in rss_sources.items():
            if source_key in enabled:
                try:
                    items = await _fetch_rss(client, source_name, feed_url)
                    all_items.extend(items)
                except Exception as e:
                    logger.warning(f"[news/{source_key}] Failed: {e}")

        # Dev.to API
        if "devto" in enabled:
            try:
                items = await _fetch_devto(client)
                all_items.extend(items)
            except Exception as e:
                logger.warning(f"[news/devto] Failed: {e}")

    # Sort by published date (newest first)
    all_items.sort(
        key=lambda x: x.published_at or datetime.min.replace(tzinfo=timezone.utc),
        reverse=True,
    )

    logger.info(f"[news] Aggregated {len(all_items)} news items")
    return all_items


async def _fetch_hackernews(client: httpx.AsyncClient) -> list[NewsItem]:
    """Fetch top stories from Hacker News API."""
    resp = await client.get("https://hacker-news.firebaseio.com/v0/topstories.json")
    resp.raise_for_status()
    story_ids = resp.json()[:30]  # Top 30

    items: list[NewsItem] = []
    for story_id in story_ids:
        try:
            resp = await client.get(
                f"https://hacker-news.firebaseio.com/v0/item/{story_id}.json"
            )
            resp.raise_for_status()
            story = resp.json()

            if not story or story.get("type") != "story":
                continue

            title = story.get("title", "")
            url = story.get("url", f"https://news.ycombinator.com/item?id={story_id}")

            items.append(
                NewsItem(
                    id=f"hn:{story_id}",
                    title=title,
                    url=url,
                    source="Hacker News",
                    published_at=(
                        datetime.fromtimestamp(story.get("time", 0), tz=timezone.utc)
                        if story.get("time")
                        else None
                    ),
                    summary="",
                    author=story.get("by", ""),
                    points=story.get("score"),
                    comment_count=story.get("descendants"),
                )
            )

        except Exception:
            continue

    logger.info(f"[news/hackernews] Fetched {len(items)} stories")
    return items


async def _fetch_rss(
    client: httpx.AsyncClient,
    source_name: str,
    feed_url: str,
) -> list[NewsItem]:
    """Fetch news from an RSS feed."""
    resp = await client.get(feed_url)
    resp.raise_for_status()

    feed = feedparser.parse(resp.text)
    items: list[NewsItem] = []

    for entry in feed.entries[:20]:  # Limit per source
        link = entry.get("link", "")
        entry_id = entry.get("id", link)

        # Parse published date
        published = None
        for date_field in ("published", "updated", "created"):
            if entry.get(date_field):
                try:
                    from dateutil import parser as dateutil_parser

                    published = dateutil_parser.parse(entry[date_field])
                    break
                except (ValueError, TypeError):
                    continue

        summary = entry.get("summary", "") or entry.get("description", "")
        # Strip HTML from summary
        if "<" in summary:
            from bs4 import BeautifulSoup

            summary = BeautifulSoup(summary, "lxml").get_text(strip=True)
        summary = summary[:300]

        tags = [t.get("term", "") for t in entry.get("tags", []) if t.get("term")]

        items.append(
            NewsItem(
                id=f"{source_name.lower().replace(' ', '_')}:{entry_id}",
                title=entry.get("title", ""),
                url=link,
                source=source_name,
                published_at=published,
                summary=summary,
                tags=tags,
                author=entry.get("author", ""),
            )
        )

    logger.info(f"[news/{source_name.lower()}] Fetched {len(items)} articles")
    return items


async def _fetch_devto(client: httpx.AsyncClient) -> list[NewsItem]:
    """Fetch top articles from Dev.to API."""
    resp = await client.get(
        "https://dev.to/api/articles",
        params={"per_page": 20, "top": 7},
    )
    resp.raise_for_status()
    articles = resp.json()

    items: list[NewsItem] = []
    for article in articles:
        published = None
        if article.get("published_at"):
            try:
                from dateutil import parser as dateutil_parser

                published = dateutil_parser.parse(article["published_at"])
            except (ValueError, TypeError):
                pass

        items.append(
            NewsItem(
                id=f"devto:{article.get('id', '')}",
                title=article.get("title", ""),
                url=article.get("url", ""),
                source="Dev.to",
                published_at=published,
                summary=article.get("description", "")[:300],
                tags=article.get("tag_list", []),
                author=article.get("user", {}).get("name", ""),
                points=article.get("public_reactions_count"),
                comment_count=article.get("comments_count"),
            )
        )

    logger.info(f"[news/devto] Fetched {len(items)} articles")
    return items
