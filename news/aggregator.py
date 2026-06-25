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
            # Startup / VC / Founder
            "techcrunch": ("TechCrunch", "https://techcrunch.com/feed/"),
            "techmeme": ("Techmeme", "https://www.techmeme.com/feed.xml"),
            "the_information": ("The Information", "https://www.theinformation.com/feed"),
            "venturebeat": ("VentureBeat", "https://venturebeat.com/feed/"),
            "geekwire": ("GeekWire", "https://www.geekwire.com/feed/"),
            "sifted": ("Sifted", "https://sifted.eu/feed/"),
            "crunchbase_news": ("Crunchbase News", "https://news.crunchbase.com/feed/"),
            "indie_hackers": ("Indie Hackers", "https://www.indiehackers.com/feed/"),
            "producthunt": ("Product Hunt", "https://www.producthunt.com/feed"),
            "startup_grind": ("Startup Grind", "https://medium.com/feed/startup-grind"),
            "ycombinator_blog": ("Y Combinator Blog", "https://blog.ycombinator.com/feed/"),
            "first_round_review": ("First Round Review", "https://review.firstround.com/feed.xml"),
            "openview_blog": ("OpenView Blog", "https://openviewpartners.com/feed/"),
            "a16z_blog": ("a16z Blog", "https://a16z.com/feed/"),
            "sequoia_blog": ("Sequoia Capital Blog", "https://www.sequoiacap.com/feed/"),
            "bvp_blog": ("Bessemer Venture Partners Blog", "https://www.bvp.com/feed"),
            "nfx_blog": ("NFX Blog", "https://www.nfx.com/post/feed/"),
            "signalfire_blog": ("SignalFire Blog", "https://signalfire.com/feed/"),
            "saastr": ("SaaStr", "https://www.saastr.com/feed/"),
            "both_sides": ("Both Sides of the Table", "https://bothsidesofthetable.com/feed"),
            "avc": ("AVC (Fred Wilson)", "https://avc.com/feed/"),
            "tomasz_tunguz": ("Tomasz Tunguz", "https://tomtunguz.com/index.xml"),
            "feld_thoughts": ("Feld Thoughts", "https://feld.com/feed/"),
            "tech_eu": ("Tech.eu", "https://tech.eu/feed/"),
            "eu_startups": ("EU-Startups", "https://www.eu-startups.com/feed/"),
            "siliconangle": ("SiliconANGLE", "https://siliconangle.com/feed/"),
            "alleywatch": ("AlleyWatch", "https://www.alleywatch.com/feed/"),
            "finsmes": ("Finsmes", "https://www.finsmes.com/feed"),

            # General Tech News
            "theverge": ("The Verge", "https://www.theverge.com/rss/index.xml"),
            "wired": ("WIRED", "https://www.wired.com/feed/rss"),
            "arstechnica": ("Ars Technica", "https://feeds.arstechnica.com/arstechnica/index"),
            "cnet": ("CNET", "https://www.cnet.com/rss/news/"),
            "zdnet": ("ZDNet", "https://www.zdnet.com/news/rss.xml"),
            "mashable": ("Mashable", "https://mashable.com/feeds/rss/all"),
            "techradar": ("TechRadar", "https://www.techradar.com/rss"),
            "digital_trends": ("Digital Trends", "https://www.digitaltrends.com/feed/"),
            "slashdot": ("Slashdot", "http://rss.slashdot.org/Slashdot/slashdotMain"),
            "engadget": ("Engadget", "https://www.engadget.com/rss.xml"),
            "gizmodo": ("Gizmodo", "https://gizmodo.com/rss"),
            "fast_company_tech": ("Fast Company Tech", "https://www.fastcompany.com/technology/rss"),
            "pcmag": ("PCMag", "https://www.pcmag.com/rss"),
            "toms_hardware": ("Tom's Hardware", "https://www.tomshardware.com/feeds/all"),
            "android_authority": ("Android Authority", "https://www.androidauthority.com/feed/"),
            "android_central": ("Android Central", "https://www.androidcentral.com/feed"),
            "macrumors": ("MacRumors", "https://feeds.macrumors.com/MacRumors-All"),
            "9to5mac": ("9to5Mac", "https://9to5mac.com/feed/"),
            "9to5google": ("9to5Google", "https://9to5google.com/feed/"),
            "xda_developers": ("XDA Developers", "https://www.xda-developers.com/feed/"),
            "windows_central": ("Windows Central", "https://www.windowscentral.com/feed"),

            # AI / ML News
            "mit_tech_review_ai": ("MIT Technology Review (AI)", "https://www.technologyreview.com/topic/artificial-intelligence/feed"),
            "bens_bites": ("Ben's Bites", "https://bensbites.beehiiv.com/rss"),
            "the_batch": ("The Batch", "https://www.deeplearning.ai/the-batch/feed/"),
            "import_ai": ("Import AI", "https://jack-clark.net/feed/"),
            "latent_space": ("Latent Space", "https://www.latent.space/feed"),
            "ai_supremacy": ("AI Supremacy", "https://aisupremacy.substack.com/feed"),
            "the_rundown_ai": ("The Rundown AI", "https://www.therundown.ai/rss"),
            "superhuman_ai": ("Superhuman AI", "https://www.joinsuperhuman.ai/rss"),
            "alphasignal": ("AlphaSignal", "https://alphasignal.ai/feed"),
            "interconnects": ("Interconnects", "https://www.interconnects.ai/feed"),
            "last_week_in_ai": ("Last Week in AI", "https://lastweekin.ai/feed"),
            "machine_learning_street_talk": ("Machine Learning Street Talk", "https://anchor.fm/s/1d0a5198/podcast/rss"),
            "hugging_face_blog": ("Hugging Face Blog", "https://huggingface.co/blog/feed.xml"),
            "openai_blog": ("OpenAI Blog", "https://openai.com/blog/rss.xml"),
            "anthropic_news": ("Anthropic News", "https://www.anthropic.com/feed.xml"),
            "deepmind_blog": ("DeepMind Blog", "https://deepmind.google/blog/rss.xml"),
            "stability_ai_blog": ("Stability AI Blog", "https://stability.ai/blog?format=rss"),
            "scale_ai_blog": ("Scale AI Blog", "https://scale.com/blog/rss"),
            "nvidia_blog": ("NVIDIA Blog", "https://blogs.nvidia.com/feed/"),
            "towards_ai": ("Towards AI", "https://pub.towardsai.net/feed"),
            "kdnuggets": ("KDnuggets", "https://www.kdnuggets.com/feed"),

            # Engineering / Developer News
            "infoq": ("InfoQ", "https://feed.infoq.com/"),
            "github_blog": ("GitHub Blog", "https://github.blog/feed/"),
            "stack_overflow_blog": ("Stack Overflow Blog", "https://stackoverflow.blog/feed/"),
            "cloudflare_blog": ("Cloudflare Blog", "https://blog.cloudflare.com/rss/"),
            "netflix_tech_blog": ("Netflix Tech Blog", "https://netflixtechblog.com/feed"),
            "uber_engineering": ("Uber Engineering", "https://eng.uber.com/feed/"),
            "airbnb_engineering": ("Airbnb Engineering", "https://medium.com/feed/airbnb-engineering"),
            "spotify_engineering": ("Spotify Engineering", "https://engineering.atspotify.com/feed/"),
            "meta_engineering": ("Meta Engineering", "https://engineering.fb.com/feed/"),
            "google_developers_blog": ("Google Developers Blog", "https://developers.googleblog.com/feeds/posts/default?alt=rss"),
            "aws_news_blog": ("AWS News Blog", "https://aws.amazon.com/blogs/aws/feed/"),
            "microsoft_dev_blogs": ("Microsoft Dev Blogs", "https://devblogs.microsoft.com/feed/"),
            "stripe_engineering": ("Stripe Engineering", "https://stripe.com/blog/feed"),
            "slack_engineering": ("Slack Engineering", "https://slack.engineering/feed/"),
            "linkedin_engineering": ("LinkedIn Engineering", "https://engineering.linkedin.com/blog.rss.html"),
            "pinterest_engineering": ("Pinterest Engineering", "https://medium.com/feed/@Pinterest_Engineering"),
            "dropbox_tech_blog": ("Dropbox Tech Blog", "https://dropbox.tech/feed"),
            "discord_engineering": ("Discord Engineering", "https://discord.com/blog/rss.xml"),
            "datadog_engineering": ("Datadog Engineering", "https://www.datadoghq.com/blog/engineering/index.xml"),
            "shopify_engineering": ("Shopify Engineering", "https://engineering.shopify.com/blogs/engineering.atom"),
            "cockroach_labs_blog": ("Cockroach Labs Blog", "https://www.cockroachlabs.com/blog/index.xml"),
            "confluent_blog": ("Confluent Blog", "https://www.confluent.io/blog/rss.xml"),
            "planetscale_blog": ("PlanetScale Blog", "https://planetscale.com/blog/rss.xml"),
            "vercel_blog": ("Vercel Blog", "https://vercel.com/atom"),
            "hashicorp_blog": ("HashiCorp Blog", "https://www.hashicorp.com/blog/feed.xml"),

            # Cybersecurity
            "krebs_on_security": ("Krebs on Security", "https://krebsonsecurity.com/feed/"),
            "the_hacker_news": ("The Hacker News", "https://feeds.feedburner.com/TheHackersNews"),
            "dark_reading": ("Dark Reading", "https://www.darkreading.com/rss.xml"),
            "bleepingcomputer": ("BleepingComputer", "https://www.bleepingcomputer.com/feed/"),
            "securityweek": ("SecurityWeek", "https://www.securityweek.com/feed/"),
            "help_net_security": ("Help Net Security", "https://www.helpnetsecurity.com/feed/"),
            "sans_newsbites": ("SANS NewsBites", "https://www.sans.org/webcasts/rss/"),
            "schneier_on_security": ("Schneier on Security", "https://www.schneier.com/feed/atom/"),
            "threatpost": ("Threatpost", "https://threatpost.com/feed/"),
            "security_boulevard": ("Security Boulevard", "https://securityboulevard.com/feed/"),
            "malwarebytes_labs": ("Malwarebytes Labs", "https://blog.malwarebytes.com/feed/"),
            "cisco_talos_blog": ("Cisco Talos Blog", "https://blog.talosintelligence.com/feeds/posts/default"),
            "mandiant_blog": ("Mandiant Blog", "https://www.mandiant.com/resources/blog/rss.xml"),
            "crowdstrike_blog": ("CrowdStrike Blog", "https://www.crowdstrike.com/blog/feed/"),

            # Big Tech / Business
            "stratechery": ("Stratechery", "https://stratechery.com/feed/"),
            "platformer": ("Platformer", "https://www.platformer.news/feed"),
            "big_technology": ("Big Technology", "https://bigtechnology.substack.com/feed"),
            "semafor_technology": ("Semafor Technology", "https://www.semafor.com/feed/technology"),
            "bloomberg_technology": ("Bloomberg Technology", "https://www.bloomberg.com/feeds/podcasts/technology.xml"),
            "cnbc_technology": ("CNBC Technology", "https://search.cnbc.com/rs/search/combinedcms/view.xml?profile=120000000&id=19854910"),
            "fortune_tech": ("Fortune Tech", "https://fortune.com/feed/fortune-feeds/?topic=tech"),
            "financial_times_tech": ("Financial Times Tech", "https://www.ft.com/technology?format=rss"),
            "reuters_technology": ("Reuters Technology", "https://www.reutersagency.com/feed/?best-topics=tech&post_type=best"),
            "wsj_technology": ("WSJ Technology", "https://feeds.a.dj.com/rss/RSSWSJAdvancedTechnology.xml"),
            "axios_pro_rata": ("Axios Pro Rata", "https://api.axios.com/feed/top/"),
            "dealbook": ("DealBook", "https://rss.nytimes.com/services/xml/rss/nyt/Dealbook.xml"),
            "protocol_archive": ("Protocol Archive", "https://www.protocol.com/feeds/feed.rss"),
            "quartz_tech": ("Quartz Tech", "https://qz.com/technology/feed"),

            # Programming / Coding
            "hashnode": ("Hashnode", "https://hashnode.com/feed/featured"),
            "freecodecamp": ("freeCodeCamp", "https://www.freecodecamp.org/news/rss/"),
            "css_tricks": ("CSS-Tricks", "https://css-tricks.com/feed/"),
            "smashing_magazine": ("Smashing Magazine", "https://www.smashingmagazine.com/feed/"),
            "sitepoint": ("SitePoint", "https://www.sitepoint.com/feed/"),
            "dzone": ("DZone", "https://feeds.dzone.com/home"),
            "hackernoon": ("HackerNoon", "https://hackernoon.com/feed"),
            "codrops": ("Codrops", "https://tympanus.net/codrops/feed/"),
            "javascript_weekly": ("JavaScript Weekly", "https://cprss.s3.amazonaws.com/javascriptweekly.com.xml"),
            "python_weekly": ("Python Weekly", "https://cprss.s3.amazonaws.com/pythonweekly.com.xml"),
            "golang_weekly": ("Golang Weekly", "https://cprss.s3.amazonaws.com/golangweekly.com.xml"),
            "tldr_newsletter": ("TLDR Newsletter", "https://tldr.tech/tech/rss"),
            "bytes_dev": ("Bytes.dev", "https://bytes.dev/rss.xml"),
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

    # Sort by published date (newest first), handling naive vs aware datetimes
    def _sort_key(item: NewsItem):
        dt = item.published_at
        if not dt:
            return datetime.min.replace(tzinfo=timezone.utc)
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt

    all_items.sort(key=_sort_key, reverse=True)

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
