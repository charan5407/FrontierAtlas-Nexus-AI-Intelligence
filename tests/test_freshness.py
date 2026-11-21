"""
Unit tests for Date Normalization & 24-Hour Freshness Engine (Phase II).
"""

from datetime import datetime, timezone, timedelta
from src.crawler.freshness import FreshnessEngine


def test_relative_date_parsing():
    engine = FreshnessEngine(max_hours_fresh=24)
    now = datetime.now(timezone.utc)

    # 2 hours ago
    dt2 = engine.parse_relative_date("2 hours ago")
    assert dt2 is not None
    assert abs((now - dt2).total_seconds() - 7200) < 60

    # 45 mins ago
    dt_min = engine.parse_relative_date("45 mins ago")
    assert dt_min is not None
    assert abs((now - dt_min).total_seconds() - 2700) < 60

    # Just now
    dt_now = engine.parse_relative_date("just now")
    assert dt_now is not None
    assert abs((now - dt_now).total_seconds()) < 10


def test_freshness_window_filter():
    engine = FreshnessEngine(max_hours_fresh=24)
    now = datetime.now(timezone.utc)

    # 5 hours ago -> Fresh
    dt_fresh = now - timedelta(hours=5)
    is_fresh, hours_old = engine.is_within_freshness_window(dt_fresh)
    assert is_fresh is True
    assert 4.9 <= hours_old <= 5.1

    # 36 hours ago -> Not fresh
    dt_stale = now - timedelta(hours=36)
    is_fresh, hours_old = engine.is_within_freshness_window(dt_stale)
    assert is_fresh is False
    assert hours_old >= 35.9


def test_html_meta_date_extraction():
    engine = FreshnessEngine(max_hours_fresh=24)
    sample_html = """
    <html>
      <head>
        <meta property="article:published_time" content="2026-11-21T08:30:00Z" />
      </head>
      <body><h1>AI Model Release</h1></body>
    </html>
    """
    dt, method = engine.extract_date_from_html(sample_html)
    assert dt is not None
    assert "article:published_time" in method
