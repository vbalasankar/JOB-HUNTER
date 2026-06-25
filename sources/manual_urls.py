"""
Tier 4: Manual search URL generator.

Generates pre-built search URLs for sites we don't scrape,
including LinkedIn, Indeed, Glassdoor, VC portfolio pages,
startup directories, Reddit threads, and more.

These are NEVER scraped -- just printed to console and included
in email digests for the user to click through manually.
"""

from __future__ import annotations

import logging
from urllib.parse import quote_plus

from config import get_settings

logger = logging.getLogger(__name__)


def generate_manual_urls() -> list[dict[str, str]]:
    """
    Generate clickable search URLs for sites we don't scrape.
    Returns list of {"platform": name, "url": search_url, "category": category}.
    """
    settings = get_settings()

    # Build search query from target roles and keywords
    role_query = " OR ".join(f'"{role}"' for role in settings.target_roles_list)
    keyword_query = " ".join(settings.include_keywords_list[:5])
    full_query = f"{role_query} {keyword_query}"

    urls: list[dict[str, str]] = []

    # --- Job search sites ---
    for location in settings.locations_list:
        encoded_query = quote_plus(full_query)
        encoded_location = quote_plus(location)

        # LinkedIn Jobs search
        urls.append(
            {
                "platform": "LinkedIn",
                "category": "Job Search",
                "location": location,
                "url": (
                    f"https://www.linkedin.com/jobs/search/"
                    f"?keywords={encoded_query}"
                    f"&location={encoded_location}"
                    f"&f_E=3%2C4"
                    f"&sortBy=DD"
                ),
            }
        )

        # Indeed search
        urls.append(
            {
                "platform": "Indeed",
                "category": "Job Search",
                "location": location,
                "url": (
                    f"https://www.indeed.com/jobs"
                    f"?q={encoded_query}"
                    f"&l={encoded_location}"
                    f"&sort=date"
                ),
            }
        )

        # Glassdoor search
        urls.append(
            {
                "platform": "Glassdoor",
                "category": "Job Search",
                "location": location,
                "url": (
                    f"https://www.glassdoor.com/Job/jobs.htm"
                    f"?sc.keyword={encoded_query}"
                    f"&locT=C&locKeyword={encoded_location}"
                    f"&sortBy=date_desc"
                ),
            }
        )

    # --- VC portfolio pages ---
    vc_portfolios = [
        ("Sequoia Capital", "https://www.sequoiacap.com/our-companies/"),
        ("Andreessen Horowitz (a16z)", "https://a16z.com/portfolio/"),
        ("Accel", "https://www.accel.com/portfolio"),
        ("Lightspeed Venture Partners", "https://lsvp.com/portfolio/"),
        ("Bessemer Venture Partners", "https://www.bvp.com/portfolio"),
        ("General Catalyst", "https://www.generalcatalyst.com/portfolio"),
        ("Khosla Ventures", "https://www.khoslaventures.com/portfolio/"),
        ("Greylock Partners", "https://greylock.com/portfolio/"),
        ("Insight Partners", "https://www.insightpartners.com/portfolio/"),
        ("Battery Ventures", "https://www.battery.com/our-portfolio/"),
        ("First Round Capital", "https://firstround.com/companies/"),
        ("Sapphire Ventures", "https://sapphireventures.com/portfolio/"),
        ("Index Ventures", "https://www.indexventures.com/companies/"),
        ("NEA", "https://www.nea.com/portfolio"),
        ("Redpoint Ventures", "https://www.redpoint.com/companies/"),
        ("Founders Fund", "https://foundersfund.com/portfolio/"),
        ("GV (Google Ventures)", "https://www.gv.com/portfolio/"),
        ("OpenView Partners", "https://openviewpartners.com/portfolio/"),
        ("Peak XV (Sequoia India)", "https://www.peakxv.com/companies/"),
    ]

    for name, url in vc_portfolios:
        urls.append(
            {
                "platform": name,
                "category": "VC Portfolio",
                "url": url,
            }
        )

    # --- Startup directories ---
    directories = [
        ("Y Combinator Directory", "https://www.ycombinator.com/companies"),
        ("Wellfound Startup Directory", "https://wellfound.com/startups"),
        (
            "Crunchbase Startups",
            "https://www.crunchbase.com/discover/organization.companies",
        ),
        ("Product Hunt Launches", "https://www.producthunt.com/"),
        ("BetaList Startups", "https://betalist.com/"),
        ("Techstars Portfolio", "https://www.techstars.com/portfolio"),
        ("Seedcamp Portfolio", "https://seedcamp.com/portfolio/"),
        ("Antler Portfolio", "https://www.antler.co/portfolio"),
        ("500 Global Portfolio", "https://500.co/portfolio"),
        ("StartX Companies", "https://startx.com/companies/"),
        ("Entrepreneur First", "https://www.joinef.com/companies/"),
        ("Plug and Play Portfolio", "https://www.plugandplaytechcenter.com/portfolio/"),
        ("Station F Startups", "https://stationf.co/startups"),
        ("On Deck Companies", "https://www.beondeck.com/companies"),
    ]

    for name, url in directories:
        urls.append(
            {
                "platform": name,
                "category": "Startup Directory",
                "url": url,
            }
        )

    # --- Accelerator job boards ---
    accelerator_jobs = [
        ("Techstars Jobs", "https://www.techstars.com/talent"),
        ("500 Global Jobs", "https://500.co/jobs"),
        ("Alchemist Accelerator Jobs", "https://alchemistaccelerator.com/portfolio/"),
        ("Founder Institute Jobs", "https://fi.co/companies"),
    ]

    for name, url in accelerator_jobs:
        urls.append(
            {
                "platform": name,
                "category": "Accelerator Jobs",
                "url": url,
            }
        )

    # --- Community / hidden gem sources ---
    community = [
        (
            "Reddit r/startups Hiring",
            "https://www.reddit.com/r/startups/search/?q=hiring&sort=new",
        ),
        ("Reddit r/forhire", "https://www.reddit.com/r/forhire/"),
        ("Reddit r/remotework", "https://www.reddit.com/r/remotework/"),
        ("Otta (Welcome to the Jungle)", "https://app.otta.com/"),
        ("FlexJobs", "https://www.flexjobs.com/"),
        ("NoDesk", "https://nodesk.co/remote-jobs/"),
        ("Working Nomads", "https://www.workingnomads.com/jobs"),
        ("Remote.co", "https://remote.co/remote-jobs/"),
        ("SkipTheDrive", "https://www.skipthedrive.com/"),
        ("Virtual Vocations", "https://www.virtualvocations.com/jobs"),
        ("Pangian", "https://pangian.com/job-travel-remote/"),
        (
            "MindTheProduct Jobs",
            "https://www.mindtheproduct.com/product-management-jobs/",
        ),
        ("ProductHired", "https://producthired.com/"),
        ("Indie Hackers Jobs", "https://www.indiehackers.com/jobs"),
        ("Acquire.com Jobs", "https://acquire.com/"),
        ("Jobgether", "https://jobgether.com/"),
        ("JustRemote", "https://justremote.co/"),
        ("PowerToFly", "https://powertofly.com/jobs/"),
        ("Monster", "https://www.monster.com/jobs/"),
        ("CareerBuilder", "https://www.careerbuilder.com/"),
        ("Upwork", "https://www.upwork.com/"),
        ("Toptal", "https://www.toptal.com/"),
        ("Guru", "https://www.guru.com/"),
        ("PeoplePerHour", "https://www.peopleperhour.com/"),
        ("Twine", "https://www.twine.net/"),
        ("Authentic Jobs", "https://authenticjobs.com/"),
        ("Jooble", "https://jooble.org/"),
        ("Codeable", "https://codeable.io/"),
        ("WPHired", "https://www.wphired.com/"),
        ("ScalablePath", "https://www.scalablepath.com/"),
        ("Gun.io", "https://www.gun.io/"),
        ("Flexiple", "https://flexiple.com/"),
        ("Behance Jobs", "https://www.behance.net/joblist"),
        ("Coroflot", "https://www.coroflot.com/design-jobs"),
        ("YunoJuno", "https://www.yunojuno.com/"),
        ("CrowdSpring", "https://www.crowdspring.com/"),
        ("DesignBro", "https://designbro.com/"),
        ("Working Not Working", "https://workingnotworking.com/"),
    ]

    for name, url in community:
        urls.append(
            {
                "platform": name,
                "category": "Community",
                "url": url,
            }
        )

    # --- AI company career pages ---
    ai_careers = [
        ("OpenAI Careers", "https://openai.com/careers/"),
        ("Anthropic Careers", "https://www.anthropic.com/careers"),
        ("Cohere Careers", "https://cohere.com/careers"),
        ("Scale AI Careers", "https://scale.com/careers"),
        ("Perplexity Careers", "https://www.perplexity.ai/hub/careers"),
        ("Mistral AI Careers", "https://mistral.ai/careers/"),
        ("Hugging Face Careers", "https://apply.workable.com/huggingface/"),
        ("AI Talent Hub", "https://www.aitalenthub.com/"),
    ]

    for name, url in ai_careers:
        urls.append(
            {
                "platform": name,
                "category": "AI Careers",
                "url": url,
            }
        )

    # --- Developer-specific boards ---
    dev_boards = [
        ("JS Remotely", "https://jsremotely.com/"),
        ("Vue Jobs", "https://vuejobs.com/"),
        ("React Jobs", "https://www.react-jobs.com/"),
        ("Django Jobs", "https://djangojobs.net/jobs/"),
        ("Elixir Jobs", "https://elixirjobs.net/"),
        ("DevITJobs", "https://devitjobs.com/"),
        ("Cord", "https://cord.co/"),
    ]

    for name, url in dev_boards:
        urls.append(
            {
                "platform": name,
                "category": "Developer Boards",
                "url": url,
            }
        )

    # --- Web3/Crypto ---
    web3_boards = [
        ("Web3 Career", "https://web3.career/"),
        ("Cryptocurrency Jobs", "https://cryptocurrencyjobs.co/"),
        ("UseWeb3 Jobs", "https://www.useweb3.xyz/jobs"),
        ("Paradigm Portfolio", "https://www.paradigm.xyz/portfolio"),
        ("Electric Capital Jobs", "https://www.electriccapital.com/"),
    ]

    for name, url in web3_boards:
        urls.append(
            {
                "platform": name,
                "category": "Web3 / Crypto",
                "url": url,
            }
        )

    logger.info(f"Generated {len(urls)} manual search URLs")
    return urls


def format_manual_urls_text() -> str:
    """Format manual URLs for console output."""
    urls = generate_manual_urls()
    if not urls:
        return ""

    lines = ["\nManual Search URLs (click to open in browser):"]
    lines.append("=" * 60)

    current_category = ""
    for u in urls:
        category = u.get("category", "")
        if category != current_category:
            current_category = category
            lines.append(f"\n--- {current_category} ---")

        location = u.get("location", "")
        label = u["platform"]
        if location:
            label += f" [{location}]"
        lines.append(f"  {label}: {u['url']}")

    return "\n".join(lines)


def format_manual_urls_html() -> str:
    """Format manual URLs as HTML for email digest."""
    urls = generate_manual_urls()
    if not urls:
        return ""

    html = [
        '<div style="margin-top: 30px; padding: 20px; background: #f8f9fa; border-radius: 8px;">'
    ]
    html.append('<h3 style="margin-top: 0;">Manual Search Links</h3>')
    html.append(
        "<p><em>These platforms don't allow automated search. Click to search manually:</em></p>"
    )

    current_category = ""
    for u in urls:
        category = u.get("category", "")
        if category != current_category:
            if current_category:
                html.append("</ul>")
            current_category = category
            html.append(f"<h4>{current_category}</h4><ul>")

        location = u.get("location", "")
        label = u["platform"]
        if location:
            label += f" ({location})"
        html.append(f'<li><a href="{u["url"]}" target="_blank">{label}</a></li>')
    html.append("</ul></div>")

    return "\n".join(html)
