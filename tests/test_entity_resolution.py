"""
Unit tests for Deterministic Entity Resolution Engine (Phase IV).
Verifies canonicalization of variations like 'OpenAI', 'OpenAI, Inc.', 'Open AI'.
"""

import pytest
from src.resolution.resolver import EntityResolver


def test_openai_canonicalization():
    resolver = EntityResolver()
    variations = ["OpenAI", "OpenAI, Inc.", "Open AI", "OpenAI LLC"]
    for v in variations:
        cname, method, score = resolver.resolve(v)
        assert cname == "OpenAI", f"Failed for {v}: got {cname}"
        assert score >= 0.90


def test_anthropic_canonicalization():
    resolver = EntityResolver()
    variations = ["Anthropic", "Anthropic, PBC", "Anthropic AI", "Anthropic Inc."]
    for v in variations:
        cname, method, score = resolver.resolve(v)
        assert cname == "Anthropic", f"Failed for {v}: got {cname}"


def test_mistral_canonicalization():
    resolver = EntityResolver()
    variations = ["Mistral AI", "Mistral AI SAS", "Mistral", "Mistral.ai"]
    for v in variations:
        cname, method, score = resolver.resolve(v)
        assert cname == "Mistral AI", f"Failed for {v}: got {cname}"


def test_cursor_anysphere_attribution():
    resolver = EntityResolver()
    cname, method, score = resolver.resolve("Anysphere, Inc.")
    assert cname == "Cursor"
    assert method == "ALIAS_LOOKUP_TABLE"


def test_audit_log_tracking():
    resolver = EntityResolver()
    resolver.resolve("Scale AI, Inc.")
    logs = resolver.get_audit_logs()
    assert len(logs) > 0
    last_log = logs[-1]
    assert last_log.raw_name == "Scale AI, Inc."
    assert last_log.canonical_name == "Scale AI"
    assert last_log.confidence_score >= 0.95

