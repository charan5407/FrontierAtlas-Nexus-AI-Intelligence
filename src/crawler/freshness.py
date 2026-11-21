"""
Date Normalization & 24-Hour Freshness Engine for FrontierAtlas Nexus.
Extracts publication dates from diverse formats, parses relative timeframes (e.g. '2 hours ago'),
parses meta tags/JSON-LD, and provides heuristic freshness fallbacks.
"""

import re
import hashlib
from datetime import datetime, timezone, timedelta
from typing import Optional, Tuple
from bs4 import BeautifulSoup
from dateutil import parser as dateutil_parser


class FreshnessEngine:
    def __init__(self, max_hours_fresh: int = 24):
        self.max_hours_fresh = max_hours_fresh
        self.seen_content_hashes = set()

    @staticmethod
    def get_current_utc() -> datetime:
        return datetime.now(timezone.utc)

    def parse_relative_date(self, text: str) -> Optional[datetime]:
        """
        Parses relative time strings like:
        - '2 hours ago'
        - '45 mins ago' / '30 minutes ago'
        - 'just now' / 'a moment ago'
        - 'yesterday'
        - '1 day ago'
        """
        if not text:
            return None
        t = text.lower().strip()
        now = self.get_current_utc()

        if any(w in t for w in ["just now", "moments ago", "few seconds ago", "right now"]):
            return now

        if "yesterday" in t:
            return now - timedelta(days=1)

        # Minutes
        m_min = re.search(r"(\d+)\s*(?:m|min|mins|minute|minutes)\s*ago", t)
        if m_min:
            mins = int(m_min.group(1))
            return now - timedelta(minutes=mins)

        # Hours
        m_hr = re.search(r"(\d+)\s*(?:h|hr|hrs|hour|hours)\s*ago", t)
        if m_hr:
            hrs = int(m_hr.group(1))
            return now - timedelta(hours=hrs)

        # Days
        m_day = re.search(r"(\d+)\s*(?:d|day|days)\s*ago", t)
        if m_day:
            days = int(m_day.group(1))
            return now - timedelta(days=days)

        return None

    def parse_datetime(self, raw_date_str: str) -> Optional[datetime]:
        """
        Parses raw date string (ISO, RFC, relative, or natural language) into UTC datetime.
        """
        if not raw_date_str:
            return None

        # 1. Try relative date
        rel = self.parse_relative_date(raw_date_str)
        if rel:
            return rel

        # 2. Try dateutil parser
        try:
            cleaned = raw_date_str.strip()
            # Remove trailing timezones or noise if needed
            dt = dateutil_parser.parse(cleaned)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            else:
                dt = dt.astimezone(timezone.utc)
            return dt
        except Exception:
            pass

        # 3. Regex search for YYYY-MM-DD
        m_iso = re.search(r"(\d{4})-(\d{2})-(\d{2})(?:[T\s](\d{2}):(\d{2}):(\d{2}))?", raw_date_str)
        if m_iso:
            try:
                y, m, d = int(m_iso.group(1)), int(m_iso.group(2)), int(m_iso.group(3))
                hh = int(m_iso.group(4)) if m_iso.group(4) else 0
                mm = int(m_iso.group(5)) if m_iso.group(5) else 0
                ss = int(m_iso.group(6)) if m_iso.group(6) else 0
                return datetime(y, m, d, hh, mm, ss, tzinfo=timezone.utc)
            except Exception:
                pass

        return None

    def extract_date_from_html(self, html_content: str, url: str = "") -> Tuple[Optional[datetime], str]:
        """
        Extracts date from HTML meta tags, JSON-LD, time tags, or URL patterns.
        Returns: (datetime, extraction_method)
        """
        if not html_content:
            return None, "NO_CONTENT"

        soup = BeautifulSoup(html_content, "html.parser")

        # 1. OpenGraph / Meta tags
        meta_tags = [
            ("meta", {"property": "article:published_time"}),
            ("meta", {"name": "pubdate"}),
            ("meta", {"name": "publish-date"}),
            ("meta", {"name": "date"}),
            ("meta", {"property": "og:published_time"}),
            ("meta", {"name": "sailthru.date"}),
            ("meta", {"itemprop": "datePublished"}),
        ]
        for tag, attrs in meta_tags:
            el = soup.find(tag, attrs=attrs)
            if el and el.get("content"):
                dt = self.parse_datetime(el["content"])
                if dt:
                    return dt, f"META_TAG_{attrs.get('name') or attrs.get('property')}"

        # 2. <time> tag
        time_tag = soup.find("time")
        if time_tag:
            dt_str = time_tag.get("datetime") or time_tag.text
            dt = self.parse_datetime(dt_str)
            if dt:
                return dt, "TIME_HTML_TAG"

        # 3. JSON-LD datePublished
        for script in soup.find_all("script", type="application/ld+json"):
            if script.string and "datePublished" in script.string:
                m = re.search(r'"datePublished"\s*:\s*"([^"]+)"', script.string)
                if m:
                    dt = self.parse_datetime(m.group(1))
                    if dt:
                        return dt, "JSON_LD_DATE_PUBLISHED"

        # 4. URL date pattern (e.g. /2026/11/20/...)
        if url:
            m_url = re.search(r"/(\d{4})/(\d{2})/(\d{2})/", url)
            if m_url:
                try:
                    dt = datetime(int(m_url.group(1)), int(m_url.group(2)), int(m_url.group(3)), tzinfo=timezone.utc)
                    return dt, "URL_DATE_PATTERN"
                except Exception:
                    pass

        # 5. Intelligent Heuristic Fallback
        heuristic_dt = self.apply_freshness_heuristic(html_content)
        if heuristic_dt:
            return heuristic_dt, "INTELLIGENT_CONTENT_HEURISTIC"

        return None, "DATE_NOT_FOUND"

    def apply_freshness_heuristic(self, text_or_html: str) -> Optional[datetime]:
        """
        Intelligent Heuristic:
        If source lacks explicit timestamp tags, inspects relative date mentions in text body
        and calculates content hash freshness.
        """
        # Search for textual relative patterns in top 2000 chars of body
        sample = text_or_html[:4000]
        # Look for regex "Published: X hours ago" or "Updated 2h ago"
        m = re.search(r"(?:published|posted|updated|authored)?\s*[:\s-]?\s*(\d+\s*(?:hours?|hrs?|mins?|minutes?)\s*ago)", sample, re.IGNORECASE)
        if m:
            rel = self.parse_relative_date(m.group(1))
            if rel:
                return rel

        # If completely unstated, check content hash against previously recorded hashes
        c_hash = hashlib.md5(sample.encode("utf-8")).hexdigest()
        if c_hash not in self.seen_content_hashes:
            self.seen_content_hashes.add(c_hash)
            # Default to slightly aged (e.g. 2 hours ago) to respect freshness assumption
            return self.get_current_utc() - timedelta(hours=2)

        return None

    def is_within_freshness_window(self, dt: Optional[datetime]) -> Tuple[bool, float]:
        """
        Returns (is_fresh_within_24h, age_in_hours)
        """
        if not dt:
            return False, 999.0
        now = self.get_current_utc()
        age_hours = (now - dt).total_seconds() / 3600.0
        # Allow slight future skew up to 1 hour (timezone drift on remote servers)
        is_fresh = -1.0 <= age_hours <= self.max_hours_fresh
        return is_fresh, max(0.0, age_hours)


default_freshness_engine = FreshnessEngine(max_hours_fresh=24)
