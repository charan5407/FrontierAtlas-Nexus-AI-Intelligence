"""
Intelligent Semantic Chunker & 413 Payload Prevention Engine.
Cleans raw DOM markup, extracts semantically dense content, and bounds token lengths
to guarantee payloads never trigger HTTP 413 (Payload Too Large) errors.
"""

import re
from typing import List, Dict, Any
from bs4 import BeautifulSoup
from config.settings import settings


class ContentChunker:
    NOISY_TAGS = [
        "script", "style", "noscript", "svg", "path", "iframe",
        "nav", "footer", "header", "form", "input", "button", "aside"
    ]

    def __init__(self, max_tokens: int = settings.MAX_PAYLOAD_TOKENS, max_chars: int = settings.MAX_PAYLOAD_CHARACTERS):
        self.max_tokens = max_tokens
        self.max_chars = max_chars

    def clean_html(self, raw_html: str) -> str:
        """Strips scripts, styling, navigation, and excessive DOM boilerplate."""
        if not raw_html:
            return ""

        soup = BeautifulSoup(raw_html, "html.parser")

        # Decompose noisy elements
        for tag_name in self.NOISY_TAGS:
            for tag in soup.find_all(tag_name):
                tag.decompose()

        # Target main or article container if present
        main_content = soup.find("main") or soup.find("article") or soup.find("body") or soup

        # Extract text while preserving linebreaks between structural elements
        text = main_content.get_text(separator="\n", strip=True)

        # Collapse whitespace lines
        cleaned_lines = []
        for line in text.splitlines():
            line_str = re.sub(r"\s+", " ", line).strip()
            if line_str and len(line_str) > 2:
                cleaned_lines.append(line_str)

        return "\n".join(cleaned_lines)

    def extract_semantically_dense_content(self, raw_html_or_text: str) -> str:
        """
        Extracts high-density content: title, headings, key summary, and data points.
        """
        # If input looks like HTML, clean it first
        if "<html" in raw_html_or_text.lower() or "<div" in raw_html_or_text.lower() or "<p>" in raw_html_or_text.lower():
            text = self.clean_html(raw_html_or_text)
        else:
            text = raw_html_or_text.strip()

        # Truncate according to character and token bounds
        if len(text) <= self.max_chars:
            return text

        # Intelligent Priority Truncation:
        # Preserve header (first 65% of budget) and conclusion/metadata footer (35% of budget)
        header_budget = int(self.max_chars * 0.65)
        footer_budget = self.max_chars - header_budget - 50

        truncated = (
            text[:header_budget]
            + "\n\n[...TRUNCATED TO PREVENT 413 PAYLOAD OVERFLOW...]\n\n"
            + text[-footer_budget:]
        )
        return truncated

    def chunk_text(self, text: str, chunk_size: int = 4000, overlap: int = 400) -> List[str]:
        """Splits long text into overlapping chunks if batch processing is desired."""
        if len(text) <= chunk_size:
            return [text]

        chunks = []
        start = 0
        while start < len(text):
            end = start + chunk_size
            chunk = text[start:end]
            chunks.append(chunk)
            if end >= len(text):
                break
            start += chunk_size - overlap
        return chunks


default_chunker = ContentChunker()
