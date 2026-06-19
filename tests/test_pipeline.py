"""Tests for the pipeline: filter, dedupe, match."""

from __future__ import annotations

import os

import pytest


class TestFilter:
    def test_include_keyword_match(self, sample_jobs):
        os.environ["INCLUDE_KEYWORDS"] = "Python"
        os.environ["EXCLUDE_KEYWORDS"] = ""
        os.environ["LOCATIONS"] = ""
        os.environ["SENIORITY"] = ""

        # Reset settings singleton
        import config

        config._settings = None

        from pipeline.filter import filter_jobs

        result = filter_jobs(sample_jobs)

        # Jobs 1 (Python) and 3 (Python) should pass, 2 (Frontend) and 4 (marketing) should not
        titles = [j.title for j in result]
        assert "Senior Backend Engineer" in titles
        assert "Data Engineer" in titles
        assert "Frontend Designer" not in titles

    def test_exclude_keyword_blocks(self, sample_jobs):
        os.environ["INCLUDE_KEYWORDS"] = ""
        os.environ["EXCLUDE_KEYWORDS"] = "unpaid,internship"
        os.environ["LOCATIONS"] = ""
        os.environ["SENIORITY"] = ""

        import config

        config._settings = None

        from pipeline.filter import filter_jobs

        result = filter_jobs(sample_jobs)

        titles = [j.title for j in result]
        assert "Unpaid Marketing Internship" not in titles

    def test_location_filter_remote(self, sample_jobs):
        os.environ["INCLUDE_KEYWORDS"] = ""
        os.environ["EXCLUDE_KEYWORDS"] = ""
        os.environ["LOCATIONS"] = "Remote"
        os.environ["SENIORITY"] = ""

        import config

        config._settings = None

        from pipeline.filter import filter_jobs

        result = filter_jobs(sample_jobs)

        # Only remote jobs should pass
        for job in result:
            assert (
                job.remote_type == "remote" or "remote" in (job.location or "").lower()
            )

    def test_seniority_filter(self, sample_jobs):
        os.environ["INCLUDE_KEYWORDS"] = ""
        os.environ["EXCLUDE_KEYWORDS"] = ""
        os.environ["LOCATIONS"] = ""
        os.environ["SENIORITY"] = "Senior"

        import config

        config._settings = None

        from pipeline.filter import filter_jobs

        result = filter_jobs(sample_jobs)

        # "Senior Backend Engineer" matches, others lack seniority indicators so pass through
        assert any("Senior" in j.title for j in result)


class TestDedupe:
    def test_intra_batch_dedup(self, temp_db):
        from datetime import datetime, timezone
        from storage.models import Job
        from pipeline.dedupe import deduplicate

        # Create two jobs with same content but different IDs (from different sources)
        jobs = [
            Job(
                id="greenhouse:123",
                source="greenhouse",
                title="Senior Backend Engineer",
                company="stripe",
                location="Remote",
                url="https://a.com",
                description_raw="Python developer",
                fetched_at=datetime.now(timezone.utc),
            ),
            Job(
                id="lever:456",
                source="lever",
                title="Senior Backend Engineer",
                company="stripe",
                location="Remote",
                url="https://b.com",
                description_raw="Python developer",
                fetched_at=datetime.now(timezone.utc),
            ),
        ]

        result = deduplicate(jobs)
        assert len(result) == 1  # Fuzzy match should catch the duplicate

    def test_different_jobs_not_deduped(self, temp_db):
        from datetime import datetime, timezone
        from storage.models import Job
        from pipeline.dedupe import deduplicate

        jobs = [
            Job(
                id="greenhouse:1",
                source="greenhouse",
                title="Senior Backend Engineer",
                company="stripe",
                location="Remote",
                url="https://a.com",
                description_raw="Python",
                fetched_at=datetime.now(timezone.utc),
            ),
            Job(
                id="greenhouse:2",
                source="greenhouse",
                title="Frontend Designer",
                company="figma",
                location="San Francisco",
                url="https://b.com",
                description_raw="React",
                fetched_at=datetime.now(timezone.utc),
            ),
        ]

        result = deduplicate(jobs)
        assert len(result) == 2


class TestMatch:
    @pytest.mark.asyncio
    async def test_keyword_scoring(self, sample_jobs, resume_text):
        os.environ["EMBEDDING_PROVIDER"] = "keyword"
        os.environ["RESUME_PATH"] = ""

        import config

        config._settings = None

        from pipeline.match import score_jobs

        scored = await score_jobs(sample_jobs[:3], resume_text=resume_text)

        # Backend/Data jobs should score higher than Frontend
        backend_score = next(j.match_score for j in scored if "Backend" in j.title)
        frontend_score = next(j.match_score for j in scored if "Frontend" in j.title)

        assert backend_score > frontend_score
        assert all(j.match_score is not None for j in scored)
        assert all(j.match_reasons is not None for j in scored)
