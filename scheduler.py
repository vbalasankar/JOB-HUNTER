"""
Scheduler — runs the pipeline on a configurable interval using APScheduler.

Also provides a crontab-compatible entry for OS-level scheduling.
"""

from __future__ import annotations

import asyncio
import logging
import signal
import sys

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.interval import IntervalTrigger

from config import get_settings

logger = logging.getLogger(__name__)


def _run_pipeline_sync(dry_run: bool = False):
    """Synchronous wrapper for the async pipeline."""
    from main import run_pipeline

    try:
        result = asyncio.run(run_pipeline(dry_run=dry_run))
        logger.info(f"Scheduled run complete: {result}")
    except Exception as e:
        logger.error(f"Scheduled run failed: {e}", exc_info=True)
        # Never crash the scheduler — just log and wait for next run


def start_scheduler(dry_run: bool = False):
    """Start the APScheduler with the configured interval."""
    settings = get_settings()
    interval_hours = settings.crawl_interval_hours

    scheduler = BlockingScheduler()

    scheduler.add_job(
        _run_pipeline_sync,
        trigger=IntervalTrigger(hours=interval_hours),
        kwargs={"dry_run": dry_run},
        id="job_crawler_pipeline",
        name=f"Job Crawler (every {interval_hours}h)",
        replace_existing=True,
        max_instances=1,  # Never overlap runs
    )

    # Also run immediately on start
    scheduler.add_job(
        _run_pipeline_sync,
        kwargs={"dry_run": dry_run},
        id="job_crawler_initial",
        name="Job Crawler (initial run)",
    )

    # Graceful shutdown
    def shutdown(signum, frame):
        logger.info("Received shutdown signal — stopping scheduler")
        scheduler.shutdown(wait=False)
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    logger.info(f"🕐 Scheduler started — running every {interval_hours} hours")
    logger.info("   Press Ctrl+C to stop")
    print(f"\n📅 Scheduler running. Next crawl in {interval_hours} hours.")
    print(f"   Dry run: {dry_run}")
    print(
        f"   Crontab equivalent: 0 */{interval_hours} * * * cd {_get_project_dir()} && python main.py"
    )
    print()

    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Scheduler stopped")


def print_crontab_entry():
    """Print a crontab entry for OS-level scheduling."""
    settings = get_settings()
    hours = settings.crawl_interval_hours
    project_dir = _get_project_dir()

    entry = f"0 */{hours} * * * cd {project_dir} && python main.py >> {project_dir}/data/cron.log 2>&1"
    print(f"\n📋 Add this to your crontab (run 'crontab -e'):\n")
    print(f"  {entry}\n")


def _get_project_dir() -> str:
    from pathlib import Path

    return str(Path(__file__).parent.resolve())
