"""Tests for source plugin base and utilities."""

from __future__ import annotations

from sources.base import (
    clean_html,
    extract_remote_type,
    extract_salary_range,
    safe_parse_date,
)


class TestExtractRemoteType:
    def test_remote_in_title(self):
        assert extract_remote_type("Senior Backend Engineer (Remote)", None) == "remote"

    def test_remote_in_location(self):
        assert extract_remote_type("Backend Engineer", "Remote, USA") == "remote"

    def test_hybrid(self):
        assert extract_remote_type("Backend Engineer (Hybrid)", "NYC") == "hybrid"

    def test_onsite(self):
        assert extract_remote_type("Backend Engineer (On-site)", "NYC") == "onsite"

    def test_no_match(self):
        assert extract_remote_type("Backend Engineer", "New York") is None

    def test_remote_hybrid_prefers_hybrid(self):
        assert extract_remote_type("Remote/Hybrid Engineer", None) == "hybrid"


class TestExtractSalaryRange:
    def test_usd_range(self):
        low, high = extract_salary_range("Salary: $150,000 - $200,000 per year")
        assert low == 150000
        assert high == 200000

    def test_no_salary(self):
        low, high = extract_salary_range("No salary info here")
        assert low is None
        assert high is None

    def test_euro_range(self):
        low, high = extract_salary_range("€80,000 – €120,000")
        assert low == 80000
        assert high == 120000


class TestCleanHtml:
    def test_strips_tags(self):
        result = clean_html("<p>Hello <strong>World</strong></p>")
        assert "Hello" in result
        assert "World" in result
        assert "<" not in result

    def test_plain_text_passthrough(self):
        assert clean_html("just plain text") == "just plain text"


class TestSafeParseDate:
    def test_iso_format(self):
        dt = safe_parse_date("2024-06-15T10:30:00Z")
        assert dt is not None
        assert dt.year == 2024
        assert dt.month == 6

    def test_none_input(self):
        assert safe_parse_date(None) is None

    def test_invalid_string(self):
        assert safe_parse_date("not a date") is None
