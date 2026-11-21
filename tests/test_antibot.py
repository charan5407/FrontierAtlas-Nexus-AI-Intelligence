"""
Unit tests for Anti-Bot & Network Telemetry Engine (Phase V).
"""

import pytest
from src.crawler.antibot import AntiBotSession


def test_antibot_header_generation():
    session = AntiBotSession()
    headers = session._get_random_headers(referer="https://google.com")
    assert "User-Agent" in headers
    assert "Chrome" in headers["User-Agent"]
    assert headers["Sec-Ch-Ua-Platform"] == '"Windows"'
    assert headers["Referer"] == "https://google.com"


def test_antibot_backoff_timing():
    import time
    import asyncio
    session = AntiBotSession()
    t0 = time.time()
    asyncio.run(session._backoff_sleep(0))
    elapsed = time.time() - t0
    # Base backoff 1.5s + jitter (0.1 - 1.0s) -> between 1.4s and 3.0s
    assert 1.4 <= elapsed <= 3.0
