"""Tests for the FastAPI server endpoints."""

import io
from unittest.mock import patch

from fastapi.testclient import TestClient

from server import app
from storage.db import bulk_upsert_jobs
from news.models import NewsItem

client = TestClient(app)


def test_read_root():
    """Test the root API endpoint."""
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_api_jobs_empty(temp_db):
    """Test getting jobs when the database is empty."""
    response = client.get("/api/jobs")
    assert response.status_code == 200
    data = response.json()
    assert data["jobs"] == []
    assert data["total"] == 0


def test_api_jobs_with_data(temp_db, sample_jobs):
    """Test getting jobs when the database has data."""
    # Score one of the jobs so it shows up in default queries
    sample_jobs[0].match_score = 0.9
    bulk_upsert_jobs(sample_jobs)

    response = client.get("/api/jobs")
    assert response.status_code == 200
    data = response.json()
    # It should return at least the scored job
    assert len(data["jobs"]) > 0
    assert data["jobs"][0]["company"] == "stripe"


@patch("server.get_news")
def test_api_news(mock_get_news, temp_db):
    """Test the news aggregator endpoint."""
    mock_get_news.return_value = [
        NewsItem(
            id="test-news-id",
            title="Test News",
            url="https://example.com/news",
            published_parsed=None,
            summary="A test summary",
            source="Test Source",
            tags=["tech"],
        )
    ]
    response = client.get("/api/news")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["title"] == "Test News"


def test_api_ats_score_txt(temp_db):
    """Test the ATS score endpoint with a TXT file."""
    test_txt = io.BytesIO(b"Senior Engineer with python and AWS experience.")
    response = client.post(
        "/api/ats-score",
        files={"resume_file": ("resume.txt", test_txt, "text/plain")},
        data={
            "job_description": "We need python and aws. Good communication skills required."
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert "overall_score" in data
    assert "hard_skills_score" in data
    assert "soft_skills_score" in data
    assert isinstance(data["overall_score"], float)


def test_api_ats_score_file_too_large(temp_db):
    """Test the ATS score endpoint blocks >5MB files."""
    test_txt = io.BytesIO(b"a" * (5 * 1024 * 1024 + 10))  # Just over 5MB
    response = client.post(
        "/api/ats-score",
        files={"resume_file": ("resume.txt", test_txt, "text/plain")},
        data={"job_description": "test"},
    )
    assert response.status_code == 400
    assert "too large" in response.text


def test_api_ats_score_text_too_large(temp_db):
    """Test the ATS score endpoint blocks >100k char descriptions."""
    test_txt = io.BytesIO(b"resume")
    large_desc = "a" * 100001
    response = client.post(
        "/api/ats-score",
        files={"resume_file": ("resume.txt", test_txt, "text/plain")},
        data={"job_description": large_desc},
    )
    assert response.status_code == 400
    assert "too long" in response.text
