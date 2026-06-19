"""Shared test fixtures."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Use a temp DB for tests
os.environ.setdefault("DB_PATH", ":memory:")
os.environ.setdefault("EMBEDDING_PROVIDER", "keyword")
os.environ.setdefault("RESUME_PATH", "")
os.environ.setdefault("GREENHOUSE_COMPANIES", "")
os.environ.setdefault("LEVER_COMPANIES", "")
os.environ.setdefault("ASHBY_COMPANIES", "")
os.environ.setdefault("ENABLE_REMOTEOK", "false")
os.environ.setdefault("ENABLE_WEWORKREMOTELY", "false")
os.environ.setdefault("ENABLE_HACKERNEWS", "false")
os.environ.setdefault("ENABLE_ARBEITNOW", "false")


@pytest.fixture
def sample_job():
    """A sample Job for testing."""
    from datetime import datetime, timezone
    from storage.models import Job

    return Job(
        id="test:123",
        source="test",
        title="Senior Backend Engineer",
        company="testcorp",
        location="Remote, USA",
        remote_type="remote",
        url="https://example.com/job/123",
        description_raw=(
            "We are looking for a Senior Backend Engineer with experience in "
            "Python, AWS, distributed systems, and Kubernetes. "
            "You will work on microservices architecture, build scalable APIs, "
            "and contribute to our data pipeline infrastructure."
        ),
        posted_date=datetime(2024, 6, 1, tzinfo=timezone.utc),
        salary_min=150000,
        salary_max=200000,
        fetched_at=datetime.now(timezone.utc),
        match_score=None,
        match_reasons=None,
        notified_at=None,
        dedup_hash="",
    )


@pytest.fixture
def sample_jobs():
    """A list of sample Jobs with varying relevance."""
    from datetime import datetime, timezone
    from storage.models import Job

    return [
        Job(
            id="test:1",
            source="greenhouse",
            title="Senior Backend Engineer",
            company="stripe",
            location="Remote",
            remote_type="remote",
            url="https://example.com/1",
            description_raw="Python AWS Kubernetes distributed systems microservices",
            posted_date=datetime(2024, 6, 1, tzinfo=timezone.utc),
            fetched_at=datetime.now(timezone.utc),
        ),
        Job(
            id="test:2",
            source="lever",
            title="Frontend Designer",
            company="figma",
            location="San Francisco, CA",
            remote_type="onsite",
            url="https://example.com/2",
            description_raw="React CSS Figma design system UI/UX wireframes",
            posted_date=datetime(2024, 6, 1, tzinfo=timezone.utc),
            fetched_at=datetime.now(timezone.utc),
        ),
        Job(
            id="test:3",
            source="greenhouse",
            title="Data Engineer",
            company="datadog",
            location="Remote, India",
            remote_type="remote",
            url="https://example.com/3",
            description_raw="Python Apache Spark AWS data pipeline ETL distributed",
            posted_date=datetime(2024, 6, 1, tzinfo=timezone.utc),
            fetched_at=datetime.now(timezone.utc),
        ),
        Job(
            id="test:4",
            source="remoteok",
            title="Unpaid Marketing Internship",
            company="startup",
            location="Remote",
            remote_type="remote",
            url="https://example.com/4",
            description_raw="Unpaid internship in social media marketing",
            posted_date=datetime(2024, 6, 1, tzinfo=timezone.utc),
            fetched_at=datetime.now(timezone.utc),
        ),
    ]


@pytest.fixture
def temp_db(tmp_path):
    """Set up a temporary SQLite database."""
    db_path = tmp_path / "test_jobs.db"
    os.environ["DB_PATH"] = str(db_path)

    # Reset both singletons so new settings/engine are created
    import config as config_mod
    import storage.db as db_mod

    config_mod._settings = None
    db_mod._engine = None

    yield db_path

    # Clean up
    if db_mod._engine:
        db_mod._engine.dispose()
    db_mod._engine = None
    config_mod._settings = None


@pytest.fixture
def resume_text():
    """Sample resume text for matching tests."""
    return """
    Senior Backend Engineer with 8 years of experience.

    Skills:
    - Python, Go, Java
    - AWS (EC2, S3, Lambda, ECS, EKS)
    - Kubernetes, Docker, Terraform
    - Distributed systems, microservices
    - PostgreSQL, Redis, Kafka
    - REST APIs, gRPC
    - CI/CD, GitHub Actions

    Experience:
    - Built scalable data pipelines processing 10M events/day
    - Designed microservices architecture serving 50K RPS
    - Led migration from monolith to Kubernetes-based microservices
    """
