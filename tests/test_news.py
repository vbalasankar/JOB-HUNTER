"""Tests for the news aggregator."""

import pytest
from unittest.mock import patch, MagicMock

from news.aggregator import get_news


from news.models import NewsItem


@patch("news.aggregator._fetch_all_news")
@pytest.mark.asyncio
async def test_get_news_caching(mock_fetch_all):
    """Test that get_news caches its results."""
    mock_entry = NewsItem(
        id="test-1",
        title="Test Post",
        url="https://test.com",
        summary="Test Summary",
        source="Test Source",
        tags=["tech"],
        published_parsed=None,
    )
    mock_fetch_all.return_value = [mock_entry]

    # Force clear cache if populated
    from news.aggregator import _cache

    _cache["items"] = []
    _cache["fetched_at"] = 0.0

    # First call
    news1 = await get_news()
    # It calls _fetch_all_news once
    assert mock_fetch_all.call_count == 1
    assert len(news1) == 1

    # Second call, should use cache
    mock_fetch_all.reset_mock()
    news2 = await get_news()
    assert len(news1) == len(news2)
    assert mock_fetch_all.call_count == 0


@patch("news.aggregator._fetch_all_news")
@pytest.mark.asyncio
async def test_get_news_filtering(mock_fetch_all):
    """Test that get_news filters by skill."""
    mock_entry1 = NewsItem(
        id="test-1",
        title="Python is great",
        url="https://test.com/1",
        summary="python!",
        source="Test",
        tags=[],
    )
    mock_entry2 = NewsItem(
        id="test-2",
        title="Rust is fast",
        url="https://test.com/2",
        summary="rust!",
        source="Test",
        tags=[],
    )

    mock_fetch_all.return_value = [mock_entry1, mock_entry2]

    from news.aggregator import _cache

    _cache["items"] = []
    _cache["fetched_at"] = 0.0

    # Filter for python
    news = await get_news(skills=["python"])
    # get_news doesn't remove non-matching items, it just sorts them to the top
    assert len(news) == 2
    assert "Python" in news[0].title
    assert "Rust" in news[1].title
