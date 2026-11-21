"""
Anti-Bot & Resilient Network Adapter for FrontierAtlas Nexus.
Implements TLS fingerprint spoofing (JA3/JA4 via curl_cffi), rotating browser headers,
anti-cloudflare heuristics, and exponential backoff with jitter.
"""

import asyncio
import random
import logging
from typing import Optional, Dict, Any
from curl_cffi.requests import AsyncSession
from config.settings import settings

logger = logging.getLogger("FrontierAtlas.AntiBot")


class AntiBotSession:
    """
    High-fidelity asynchronous session wrapper providing:
    1. TLS Fingerprinting (Chrome 120/124 impersonation avoiding Cloudflare/Datadome triggers)
    2. Header randomization & Sec-Ch-Ua client hints
    3. Exponential backoff with full jitter on 429 / 403 / 503
    4. Concurrency throttle via asyncio.Semaphore
    """

    DESKTOP_USER_AGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    ]

    def __init__(self, concurrency: int = 15, timeout: int = 30):
        self.semaphore = asyncio.Semaphore(concurrency)
        self.timeout = timeout
        self.session: Optional[AsyncSession] = None

    async def __aenter__(self):
        self.session = AsyncSession(
            impersonate=settings.IMPERSONATE_TARGET,
            timeout=self.timeout
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    def _get_random_headers(self, referer: Optional[str] = None) -> Dict[str, str]:
        ua = random.choice(self.DESKTOP_USER_AGENTS)
        headers = {
            "User-Agent": ua,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br, zstd",
            "Sec-Ch-Ua": '"Chromium";v="124", "Google Chrome";v="124", "Not-A.Brand";v="99"',
            "Sec-Ch-Ua-Mobile": "?0",
            "Sec-Ch-Ua-Platform": '"Windows"',
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Upgrade-Insecure-Requests": "1",
            "Cache-Control": "max-age=0",
        }
        if referer:
            headers["Referer"] = referer
            headers["Sec-Fetch-Site"] = "same-origin"
        return headers

    async def fetch(
        self,
        url: str,
        method: str = "GET",
        headers: Optional[Dict[str, str]] = None,
        params: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        referer: Optional[str] = None,
        max_retries: int = settings.MAX_RETRIES,
    ) -> Optional[str]:
        """
        Executes HTTP request with automated anti-bot headers, TLS impersonation,
        and jittered exponential backoff.
        """
        async with self.semaphore:
            if not self.session:
                self.session = AsyncSession(
                    impersonate=settings.IMPERSONATE_TARGET,
                    timeout=self.timeout
                )

            req_headers = self._get_random_headers(referer)
            if headers:
                req_headers.update(headers)

            for attempt in range(max_retries):
                try:
                    if method.upper() == "GET":
                        response = await self.session.get(url, headers=req_headers, params=params)
                    else:
                        response = await self.session.post(url, headers=req_headers, json=json_data, params=params)

                    status = response.status_code

                    # Success
                    if 200 <= status < 300:
                        # Check for Cloudflare Turnstile / Challenge Captcha in HTML
                        text = response.text
                        if "cf-browser-verification" in text or "Just a moment..." in text and "<title>Just a moment...</title>" in text:
                            logger.warning(f"Cloudflare Turnstile challenge intercepted on {url} (Attempt {attempt+1}/{max_retries})")
                            await self._backoff_sleep(attempt)
                            continue
                        return text

                    # Rate Limited (429) or Cloudflare Blocked (403 / 503)
                    if status in [429, 403, 503, 502]:
                        logger.warning(f"HTTP {status} on {url} (Attempt {attempt+1}/{max_retries})")
                        await self._backoff_sleep(attempt)
                        continue

                    # Client Error 404
                    if status == 404:
                        logger.debug(f"HTTP 404 Not Found: {url}")
                        return None

                    # Other status codes
                    logger.warning(f"Unexpected HTTP {status} on {url}")
                    await self._backoff_sleep(attempt)

                except Exception as e:
                    logger.warning(f"Network error requesting {url}: {e} (Attempt {attempt+1}/{max_retries})")
                    await self._backoff_sleep(attempt)

            logger.error(f"Failed to fetch {url} after {max_retries} attempts.")
            return None

    async def fetch_json(self, url: str, **kwargs) -> Optional[Any]:
        import json
        text = await self.fetch(url, **kwargs)
        if text:
            try:
                return json.loads(text)
            except Exception as e:
                logger.error(f"JSON decode error on {url}: {e}")
        return None

    async def _backoff_sleep(self, attempt: int):
        # Exponential backoff with full randomized jitter
        backoff = min(
            settings.MAX_BACKOFF_SECONDS,
            settings.BASE_BACKOFF_SECONDS * (2 ** attempt)
        )
        jitter = random.uniform(0.1, settings.BACKOFF_JITTER)
        sleep_duration = backoff + jitter
        await asyncio.sleep(sleep_duration)
