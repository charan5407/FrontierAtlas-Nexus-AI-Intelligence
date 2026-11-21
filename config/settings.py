"""
FrontierAtlas Nexus - Configuration Settings
Defines environment variables, scraping rate limits, LLM fallback tiers, and thresholds.
"""

import os
from pathlib import Path
from pydantic import BaseModel, Field

# Base Paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
PROCESSED_DATA_DIR = DATA_DIR / "processed"
EXPORTS_DIR = DATA_DIR / "exports"

for d in [DATA_DIR, RAW_DATA_DIR, PROCESSED_DATA_DIR, EXPORTS_DIR]:
    d.mkdir(parents=True, exist_ok=True)


class Settings(BaseModel):
    # Project Identity
    PROJECT_NAME: str = "FrontierAtlas Nexus"
    PROJECT_VERSION: str = "1.0.0"
    SCHEMA_VERSION: str = "1.0"

    # Concurrency & Networking
    MAX_CONCURRENT_REQUESTS: int = 25
    REQUEST_TIMEOUT_SECONDS: int = 10
    DEFAULT_USER_AGENT: str = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    )

    # Anti-Bot & Retries
    MAX_RETRIES: int = 4
    BASE_BACKOFF_SECONDS: float = 1.5
    MAX_BACKOFF_SECONDS: float = 30.0
    BACKOFF_JITTER: float = 1.0
    IMPERSONATE_TARGET: str = "chrome124"

    # Freshness Challenge
    FRESHNESS_WINDOW_HOURS: int = 24

    # LLM Providers & API Keys
    GEMINI_API_KEY: str = Field(default_factory=lambda: os.getenv("GEMINI_API_KEY", ""))
    GROQ_API_KEY: str = Field(default_factory=lambda: os.getenv("GROQ_API_KEY", ""))
    DEEPSEEK_API_KEY: str = Field(default_factory=lambda: os.getenv("DEEPSEEK_API_KEY", ""))
    OPENAI_API_KEY: str = Field(default_factory=lambda: os.getenv("OPENAI_API_KEY", ""))
    GITHUB_TOKEN: str = Field(default_factory=lambda: os.getenv("GITHUB_TOKEN", ""))

    # Chunking & 413 Prevention
    MAX_PAYLOAD_TOKENS: int = 6000
    MAX_PAYLOAD_CHARACTERS: int = 24000

    # Entity Resolution
    FUZZY_SIMILARITY_THRESHOLD: float = 0.86


settings = Settings()
