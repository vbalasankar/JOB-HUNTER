"""
main.py -- CLI entry point for the job crawler pipeline.

Usage:
  python main.py              # Single run
  python main.py --schedule   # Continuous scheduled runs
  python main.py --dry-run    # Fetch + score, but don't notify
  python main.py --urls-only  # Just print manual search URLs
  python main.py --serve      # Start the web frontend server
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import time
from datetime import datetime, timezone

import httpx

from config import get_settings
from notify.email import send_digest
from pipeline.dedupe import deduplicate
from pipeline.filter import filter_jobs
from pipeline.match import score_jobs
from sources.base import BaseJobSource, RawJob
from sources.manual_urls import format_manual_urls_text
from storage.db import bulk_upsert_jobs
from storage.models import Job

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("job_crawler")


def _build_sources() -> list[BaseJobSource]:
    """Build the list of active sources based on config."""
    settings = get_settings()
    sources: list[BaseJobSource] = []

    # Tier 1: ATS APIs
    from sources.greenhouse import GreenhouseSource
    from sources.lever import LeverSource
    from sources.ashby import AshbySource

    if settings.greenhouse_companies_list:
        sources.append(GreenhouseSource())
    if settings.lever_companies_list:
        sources.append(LeverSource())
    if settings.ashby_companies_list:
        sources.append(AshbySource())

    # Tier 2: Aggregators (original)
    from sources.remoteok import RemoteOKSource
    from sources.weworkremotely import WeWorkRemotelySource
    from sources.hackernews import HackerNewsSource
    from sources.arbeitnow import ArbeitnowSource

    if settings.enable_remoteok:
        sources.append(RemoteOKSource())
    if settings.enable_weworkremotely:
        sources.append(WeWorkRemotelySource())
    if settings.enable_hackernews:
        sources.append(HackerNewsSource())
    if settings.enable_arbeitnow:
        sources.append(ArbeitnowSource())

    # Tier 2: New aggregator sources
    from sources.wellfound import WellfoundSource
    from sources.ycombinator import YCombinatorSource
    from sources.builtin import BuiltInSource
    from sources.himalayas import HimalayasSource
    from sources.dynamite_jobs import DynamiteJobsSource
    from sources.remotive import RemotiveSource
    from sources.arc_dev import ArcDevSource
    from sources.jobspresso import JobspressoSource
    from sources.crypto_jobs import CryptoJobsSource
    from sources.ai_jobs import AIJobsSource
    from sources.golang_cafe import GolangCafeSource
    from sources.rustjobs import RustJobsSource
    from sources.python_jobs import PythonJobsSource
    from sources.dribbble import DribbbleSource

    if settings.enable_wellfound:
        sources.append(WellfoundSource())
    if settings.enable_ycombinator:
        sources.append(YCombinatorSource())
    if settings.enable_builtin:
        sources.append(BuiltInSource())
    if settings.enable_himalayas:
        sources.append(HimalayasSource())
    if settings.enable_dynamite_jobs:
        sources.append(DynamiteJobsSource())
    if settings.enable_remotive:
        sources.append(RemotiveSource())
    if settings.enable_arc_dev:
        sources.append(ArcDevSource())
    if settings.enable_jobspresso:
        sources.append(JobspressoSource())
    if settings.enable_crypto_jobs:
        sources.append(CryptoJobsSource())
    if settings.enable_ai_jobs:
        sources.append(AIJobsSource())
    if settings.enable_golang_cafe:
        sources.append(GolangCafeSource())
    if settings.enable_rustjobs:
        sources.append(RustJobsSource())
    if settings.enable_python_jobs:
        sources.append(PythonJobsSource())
    if settings.enable_dribbble:
        sources.append(DribbbleSource())

    # Tier 3: Career pages
    if settings.career_pages:
        from sources.career_page import CareerPageSource

        sources.append(CareerPageSource())

    logger.info(f"Active sources: {[s.name for s in sources]}")
    return sources


async def _fetch_all(
    sources: list[BaseJobSource],
    client: httpx.AsyncClient,
) -> list[RawJob]:
    """Fetch from all sources concurrently, logging and skipping failures."""
    tasks = []
    for source in sources:
        tasks.append(_fetch_source(source, client))

    results = await asyncio.gather(*tasks, return_exceptions=True)

    all_raws: list[RawJob] = []
    for source, result in zip(sources, results):
        if isinstance(result, Exception):
            logger.warning(f"[{source.name}] Source failed with exception: {result}")
        elif isinstance(result, list):
            all_raws.extend(result)
        else:
            logger.warning(f"[{source.name}] Unexpected result type: {type(result)}")

    return all_raws


async def _fetch_source(
    source: BaseJobSource,
    client: httpx.AsyncClient,
) -> list[RawJob]:
    """Fetch from a single source with error handling."""
    try:
        raws = await source.fetch(client)
        logger.info(f"[{source.name}] -> {len(raws)} raw jobs")
        return raws
    except Exception as e:
        logger.warning(f"[{source.name}] Fetch failed: {e}")
        return []


def _normalize_all(
    sources: list[BaseJobSource],
    raws: list[RawJob],
) -> list[Job]:
    """Normalize all raw jobs, grouping by source."""
    source_map = {s.name: s for s in sources}
    all_jobs: list[Job] = []

    for raw in raws:
        source = source_map.get(raw.source_name)
        if not source:
            logger.warning(f"No source handler for {raw.source_name}")
            continue
        try:
            job = source.normalize(raw)
            all_jobs.append(job)
        except Exception as e:
            logger.warning(
                f"[{raw.source_name}] Normalize failed for {raw.source_id}: {e}"
            )

    return all_jobs


async def run_pipeline(dry_run: bool = False) -> dict:
    """
    Execute the full pipeline:
    Fetch -> Normalize -> Deduplicate -> Filter -> Match -> Persist -> Notify

    Returns a summary dict with counts.
    """
    settings = get_settings()
    start_time = time.monotonic()

    logger.info("=" * 60)
    logger.info(f"Pipeline run started at {datetime.now(timezone.utc).isoformat()}")
    logger.info("=" * 60)

    # 1. Build sources
    sources = _build_sources()

    # 2. Fetch
    async with httpx.AsyncClient(
        headers={
            "User-Agent": settings.user_agent,
            "Accept": "application/json",
        },
        follow_redirects=True,
        http2=True,
    ) as client:
        raws = await _fetch_all(sources, client)

    logger.info(f"Total raw jobs fetched: {len(raws)}")

    if not raws:
        logger.warning("No jobs fetched from any source -- pipeline complete")
        return {
            "fetched": 0,
            "normalized": 0,
            "deduped": 0,
            "filtered": 0,
            "scored": 0,
            "persisted_new": 0,
            "notified": 0,
        }

    # 3. Normalize
    jobs = _normalize_all(sources, raws)
    logger.info(f"Normalized: {len(jobs)} jobs")

    # 4. Deduplicate
    jobs = deduplicate(jobs)
    logger.info(f"After dedup: {len(jobs)} unique jobs")

    if not jobs:
        logger.info("All jobs are duplicates -- nothing new to process")
        return {
            "fetched": len(raws),
            "normalized": len(jobs),
            "deduped": 0,
            "filtered": 0,
            "scored": 0,
            "persisted_new": 0,
            "notified": 0,
        }

    # 5. Filter
    filtered_jobs = filter_jobs(jobs)
    logger.info(f"After filter: {len(filtered_jobs)} relevant jobs")

    # 6. Match (score)
    scored_jobs = await score_jobs(filtered_jobs)
    above_threshold = [
        j for j in scored_jobs if (j.match_score or 0) >= settings.min_match_score
    ]
    logger.info(
        f"Scored: {len(scored_jobs)} jobs, "
        f"{len(above_threshold)} above threshold ({settings.min_match_score})"
    )

    # 7. Persist
    # Persist all scored jobs (not just above threshold) for future retuning
    new_count, updated_count = bulk_upsert_jobs(scored_jobs)
    logger.info(f"Persisted: {new_count} new, {updated_count} updated")

    # 8. Notify
    notified = 0
    if dry_run:
        logger.info(f"DRY RUN -- would notify about {len(above_threshold)} jobs")
        for j in above_threshold[:10]:
            logger.info(f"  -> [{j.match_score:.3f}] {j.title} @ {j.company}")
    else:
        notified = send_digest()

    # Print manual URLs
    if settings.generate_manual_urls:
        print(format_manual_urls_text())

    elapsed = time.monotonic() - start_time
    logger.info(f"Pipeline complete in {elapsed:.1f}s")

    return {
        "fetched": len(raws),
        "normalized": len(jobs),
        "deduped": len(jobs),
        "filtered": len(filtered_jobs),
        "scored": len(scored_jobs),
        "persisted_new": new_count,
        "notified": notified,
    }


def cli():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Multi-source job hunting pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py              # Single run
  python main.py --schedule   # Run on schedule (every N hours)
  python main.py --dry-run    # Fetch + score, skip notifications
  python main.py --urls-only  # Just print manual search URLs
  python main.py --serve      # Start the web frontend server
        """,
    )
    parser.add_argument(
        "--schedule",
        action="store_true",
        help="Run on a schedule (interval from config)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run pipeline but don't send notifications",
    )
    parser.add_argument(
        "--urls-only",
        action="store_true",
        help="Just generate and print manual search URLs",
    )
    parser.add_argument(
        "--serve", action="store_true", help="Start the web frontend server"
    )

    args = parser.parse_args()

    if args.urls_only:
        print(format_manual_urls_text())
        return

    if args.serve:
        import uvicorn
        from config import get_settings

        settings = get_settings()
        print(f"Starting server at http://localhost:{settings.server_port}")
        uvicorn.run(
            "server:app",
            host=settings.server_host,
            port=settings.server_port,
            reload=True,
        )
        return

    if args.schedule:
        from scheduler import start_scheduler

        start_scheduler(dry_run=args.dry_run)
    else:
        result = asyncio.run(run_pipeline(dry_run=args.dry_run))
        _print_summary(result)


def _print_summary(result: dict):
    """Print a nice summary of the pipeline run."""
    print("\n" + "=" * 50)
    print("Pipeline Run Summary")
    print("=" * 50)
    print(f"  Fetched:      {result['fetched']}")
    print(f"  Normalized:   {result['normalized']}")
    print(f"  After dedup:  {result['deduped']}")
    print(f"  After filter: {result['filtered']}")
    print(f"  Scored:       {result['scored']}")
    print(f"  New in DB:    {result['persisted_new']}")
    print(f"  Notified:     {result['notified']}")
    print("=" * 50)


if __name__ == "__main__":
    cli()
