"""Tests for notification dedup and DB operations."""

from __future__ import annotations


class TestNotificationDedup:
    """Verify that re-running never re-notifies for the same job."""

    def test_mark_notified_prevents_renotify(self, temp_db, sample_job):
        from storage.db import bulk_upsert_jobs, get_unnotified_matches, mark_notified

        # Set score above threshold
        sample_job.match_score = 0.85
        bulk_upsert_jobs([sample_job])

        # First check: should find the job
        matches = get_unnotified_matches(0.7)
        assert len(matches) == 1
        assert matches[0].id == sample_job.id

        # Mark as notified
        mark_notified([sample_job.id])

        # Second check: should NOT find it again
        matches = get_unnotified_matches(0.7)
        assert len(matches) == 0

    def test_below_threshold_not_notified(self, temp_db, sample_job):
        from storage.db import bulk_upsert_jobs, get_unnotified_matches

        sample_job.match_score = 0.5  # Below threshold
        bulk_upsert_jobs([sample_job])

        matches = get_unnotified_matches(0.7)
        assert len(matches) == 0


class TestDBOperations:
    def test_upsert_new(self, temp_db, sample_job):
        from storage.db import bulk_upsert_jobs

        new, updated = bulk_upsert_jobs([sample_job])
        assert new == 1
        assert updated == 0

    def test_upsert_existing_updates_score(self, temp_db, sample_job):
        from storage.db import bulk_upsert_jobs, get_session
        from storage.models import Job

        sample_job.match_score = 0.7
        bulk_upsert_jobs([sample_job])

        # Update with new score
        sample_job.match_score = 0.9
        new, updated = bulk_upsert_jobs([sample_job])
        assert new == 0
        assert updated == 1

        # Verify score was updated
        with get_session() as session:
            job = session.get(Job, sample_job.id)
            assert job is not None
            assert job.match_score == 0.9

    def test_upsert_preserves_notification_state(self, temp_db, sample_job):
        from storage.db import bulk_upsert_jobs, mark_notified, get_session
        from storage.models import Job

        sample_job.match_score = 0.85
        bulk_upsert_jobs([sample_job])
        mark_notified([sample_job.id])

        # Re-upsert with different score
        sample_job.match_score = 0.95
        bulk_upsert_jobs([sample_job])

        # Verify notified_at is preserved
        with get_session() as session:
            job = session.get(Job, sample_job.id)
            assert job is not None
            assert job.notified_at is not None  # Still marked as notified
