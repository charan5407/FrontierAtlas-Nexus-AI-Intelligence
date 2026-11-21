"""
Unit tests for Multi-Tier LLM Orchestrator & Chunker (Phase III).
"""

import pytest
from src.llm.chunker import ContentChunker
from src.llm.orchestrator import LLMOrchestrator


def test_chunker_boilerplate_stripping():
    chunker = ContentChunker(max_chars=5000)
    dirty_html = """
    <html>
      <head>
        <script>var tracker = 123;</script>
        <style>.ads { display: none; }</style>
      </head>
      <body>
        <nav><a href="/">Home</a></nav>
        <main>
          <h1>Frontier Foundation Model</h1>
          <p>We introduce a revolutionary sparse mixture of experts model.</p>
        </main>
        <footer>Copyright 2026</footer>
      </body>
    </html>
    """
    cleaned = chunker.clean_html(dirty_html)
    assert "var tracker" not in cleaned
    assert "display: none" not in cleaned
    assert "Frontier Foundation Model" in cleaned
    assert "sparse mixture of experts" in cleaned


def test_413_payload_budget_prevention():
    chunker = ContentChunker(max_chars=500)
    long_content = "Extremely long text payload that would overflow context windows. " * 50
    bounded = chunker.extract_semantically_dense_content(long_content)
    assert len(bounded) <= 520
    assert "TRUNCATED TO PREVENT 413" in bounded


def test_deterministic_fallback_schema():
    import asyncio
    orchestrator = LLMOrchestrator()
    sample_text = "Anthropic is an AI safety startup. Team size: 550 employees. Website: anthropic.com"
    result = asyncio.run(orchestrator.extract_structured_entity(sample_text, "STARTUP", "https://anthropic.com"))
    assert result["schemaVersion"] == "1.0"
    assert result["recordType"] == "STARTUP"
    assert result["content"]["entityName"] == "Anthropic"
    assert result["content"]["data"]["employeeCount"] == 550
    assert "_tier_used" in result
