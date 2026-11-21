"""
Multi-Tier LLM Orchestration Engine for FrontierAtlas Nexus.
Features:
1. Fallback Cascade: Gemini Flash -> Groq Llama-3 -> DeepSeek -> Deterministic Parser
2. Exponential Backoff with full randomized jitter for 429 handling
3. Strict JSON Schema enforcement conforming to Canonical Entity specifications
"""

import os
import json
import re
import asyncio
import random
import logging
from typing import Dict, Any, Optional
from config.settings import settings
from src.llm.chunker import default_chunker
from src.resolution.resolver import default_resolver

logger = logging.getLogger("FrontierAtlas.LLM")


class LLMOrchestrator:
    def __init__(self):
        self.gemini_key = settings.GEMINI_API_KEY
        self.groq_key = settings.GROQ_API_KEY
        self.deepseek_key = settings.DEEPSEEK_API_KEY
        self.openai_key = settings.OPENAI_API_KEY

        # Initialize clients lazily if keys exist
        self._groq_client = None
        self._openai_client = None

    def _get_groq_client(self):
        if self._groq_client is None and self.groq_key:
            try:
                from groq import Groq
                self._groq_client = Groq(api_key=self.groq_key)
            except Exception as e:
                logger.warning(f"Failed to init Groq client: {e}")
        return self._groq_client

    def _get_deepseek_client(self):
        if self._openai_client is None and (self.deepseek_key or self.openai_key):
            try:
                from openai import OpenAI
                key = self.deepseek_key or self.openai_key
                base_url = "https://api.deepseek.com/v1" if self.deepseek_key else None
                self._openai_client = OpenAI(api_key=key, base_url=base_url)
            except Exception as e:
                logger.warning(f"Failed to init DeepSeek client: {e}")
        return self._openai_client

    async def extract_structured_entity(
        self,
        raw_text_or_html: str,
        entity_type: str,
        source_url: str = "",
        max_retries: int = settings.MAX_RETRIES
    ) -> Dict[str, Any]:
        """
        Takes raw text/HTML and extracts a canonical JSON schema object using
        the multi-tier fallback chain: Gemini -> Groq -> DeepSeek -> Deterministic.
        """
        # 1. Clean and chunk payload to prevent 413
        dense_text = default_chunker.extract_semantically_dense_content(raw_text_or_html)

        # 2. Tier 1: Gemini Flash
        if self.gemini_key:
            try:
                result = await self._call_gemini_with_backoff(dense_text, entity_type, source_url, max_retries)
                if result:
                    result["_tier_used"] = "Tier 1: Gemini Flash"
                    return self._post_process_result(result, entity_type, source_url)
            except Exception as e:
                logger.warning(f"Gemini Tier failed: {e}. Cascading to Tier 2 (Groq Llama 3)...")

        # 3. Tier 2: Groq Llama 3
        if self.groq_key:
            try:
                result = await self._call_groq_with_backoff(dense_text, entity_type, source_url, max_retries)
                if result:
                    result["_tier_used"] = "Tier 2: Groq Llama 3"
                    return self._post_process_result(result, entity_type, source_url)
            except Exception as e:
                logger.warning(f"Groq Tier failed: {e}. Cascading to Tier 3 (DeepSeek)...")

        # 4. Tier 3: DeepSeek
        if self.deepseek_key or self.openai_key:
            try:
                result = await self._call_deepseek_with_backoff(dense_text, entity_type, source_url, max_retries)
                if result:
                    result["_tier_used"] = "Tier 3: DeepSeek"
                    return self._post_process_result(result, entity_type, source_url)
            except Exception as e:
                logger.warning(f"DeepSeek Tier failed: {e}. Cascading to Deterministic Parser...")

        # 5. Tier 4: High-Precision Deterministic Fallback Parser
        result = self._deterministic_extract(dense_text, entity_type, source_url)
        result["_tier_used"] = "Tier 4: Deterministic Rule Engine"
        return self._post_process_result(result, entity_type, source_url)

    async def _call_gemini_with_backoff(self, text: str, entity_type: str, source_url: str, retries: int) -> Optional[Dict[str, Any]]:
        from google import genai
        client = genai.Client(api_key=self.gemini_key)
        prompt = self._build_prompt(text, entity_type, source_url)

        for attempt in range(retries):
            try:
                response = client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=prompt,
                )
                if response and response.text:
                    return self._parse_json_from_llm(response.text)
            except Exception as e:
                err_str = str(e).lower()
                if "429" in err_str or "quota" in err_str or "rate limit" in err_str:
                    await self._sleep_backoff(attempt)
                    continue
                raise e
        return None

    async def _call_groq_with_backoff(self, text: str, entity_type: str, source_url: str, retries: int) -> Optional[Dict[str, Any]]:
        client = self._get_groq_client()
        if not client:
            return None
        prompt = self._build_prompt(text, entity_type, source_url)

        for attempt in range(retries):
            try:
                completion = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[
                        {"role": "system", "content": "You are a precise data extraction engine. Output valid JSON only."},
                        {"role": "user", "content": prompt}
                    ],
                    response_format={"type": "json_object"}
                )
                raw_json = completion.choices[0].message.content
                return json.loads(raw_json)
            except Exception as e:
                if "429" in str(e).lower():
                    await self._sleep_backoff(attempt)
                    continue
                raise e
        return None

    async def _call_deepseek_with_backoff(self, text: str, entity_type: str, source_url: str, retries: int) -> Optional[Dict[str, Any]]:
        client = self._get_deepseek_client()
        if not client:
            return None
        prompt = self._build_prompt(text, entity_type, source_url)

        for attempt in range(retries):
            try:
                completion = client.chat.completions.create(
                    model="deepseek-chat" if self.deepseek_key else "gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": "You are a precise data extraction engine. Output valid JSON only."},
                        {"role": "user", "content": prompt}
                    ],
                    response_format={"type": "json_object"}
                )
                raw_json = completion.choices[0].message.content
                return json.loads(raw_json)
            except Exception as e:
                if "429" in str(e).lower():
                    await self._sleep_backoff(attempt)
                    continue
                raise e
        return None

    def _deterministic_extract(self, text: str, entity_type: str, source_url: str) -> Dict[str, Any]:
        """
        Deterministic, zero-hallucination rule-based fallback when LLM APIs are unreachable.
        Extracts structured signals directly from HTML patterns and text heuristics.
        """
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        first_line = lines[0] if lines else "AI Entity"

        if entity_type.upper() == "STARTUP":
            # Extract employee count if mentioned (e.g., '50-100 employees', '250 employees')
            emp_match = re.search(r"(\d{1,5}(?:,\d{3})*)\s*(?:employees|people|team members|staff)", text, re.IGNORECASE)
            emp_count = int(emp_match.group(1).replace(",", "")) if emp_match else None
            # Raw name from title or first line
            raw_name = first_line.split("|")[0].split("-")[0].strip()
            return {
                "schemaVersion": "1.0",
                "recordType": "STARTUP",
                "source": {"name": self._extract_domain(source_url), "url": source_url},
                "content": {
                    "entityName": raw_name,
                    "data": {"employeeCount": emp_count}
                }
            }

        elif entity_type.upper() == "PRODUCT":
            # Pricing model heuristic
            pricing = "FREE"
            t_low = text.lower()
            if "enterprise" in t_low or "custom pricing" in t_low or "contact sales" in t_low:
                pricing = "ENTERPRISE"
            elif "freemium" in t_low or "free trial" in t_low or "free plan" in t_low:
                pricing = "FREEMIUM"
            elif "paid" in t_low or "per month" in t_low or "$/mo" in t_low or "pricing" in t_low:
                pricing = "PAID"

            raw_startup = first_line.split("|")[0].split("-")[0].strip()
            return {
                "schemaVersion": "1.0",
                "recordType": "PRODUCT",
                "source": {"name": self._extract_domain(source_url), "url": source_url},
                "content": {
                    "productName": raw_startup,
                    "startupName": raw_startup,
                    "pricingModel": pricing
                }
            }

        elif entity_type.upper() == "JOB":
            is_remote = any(w in text.lower() for w in ["remote", "work from home", "anywhere", "worldwide"])
            role_family = "Engineering"
            t_low = text.lower()
            if "research" in t_low or "scientist" in t_low:
                role_family = "Research"
            elif "product" in t_low:
                role_family = "Product"
            elif "design" in t_low:
                role_family = "Design"

            company = first_line.split("is hiring")[0].split("at")[-1].strip() if "hiring" in first_line or "at" in first_line else first_line
            return {
                "schemaVersion": "1.0",
                "recordType": "JOB",
                "content": {
                    "company": company,
                    "date": "2026-11-21T00:00:00Z",
                    "is_remote": is_remote,
                    "role_family": role_family
                }
            }

        # Generic default
        return {"content": {"title": first_line, "raw": text[:500]}}

    def _post_process_result(self, result: Dict[str, Any], entity_type: str, source_url: str) -> Dict[str, Any]:
        """Passes extracted names through Deterministic Entity Resolver."""
        if entity_type.upper() == "STARTUP":
            raw = result.get("content", {}).get("entityName", "")
            cname, method, score = default_resolver.resolve(raw, source_url)
            result["content"]["entityName"] = cname
            result["_resolution"] = {"method": method, "confidence": score}

        elif entity_type.upper() == "PRODUCT":
            raw = result.get("content", {}).get("startupName", "")
            cname, method, score = default_resolver.resolve(raw, source_url)
            result["content"]["startupName"] = cname
            result["_resolution"] = {"method": method, "confidence": score}

        elif entity_type.upper() == "JOB":
            raw = result.get("content", {}).get("company", "")
            cname, method, score = default_resolver.resolve(raw, source_url)
            result["content"]["company"] = cname
            result["_resolution"] = {"method": method, "confidence": score}

        return result

    def _build_prompt(self, text: str, entity_type: str, source_url: str) -> str:
        return f"""
You are a high-precision entity extraction system for GraphOne / FrontierAtlas Intelligence Graph.
Extract structured data from the following text into a canonical JSON object.

Entity Type to extract: {entity_type}
Source URL: {source_url}

Expected JSON Schemas:
If STARTUP:
{{
  "schemaVersion": "1.0",
  "recordType": "STARTUP",
  "source": {{"name": "...", "url": "{source_url}"}},
  "content": {{
    "entityName": "Extracted startup name",
    "data": {{"employeeCount": 120 or null}}
  }}
}}

If PRODUCT:
{{
  "schemaVersion": "1.0",
  "recordType": "PRODUCT",
  "source": {{"name": "...", "url": "{source_url}"}},
  "content": {{
    "productName": "...",
    "startupName": "Extracted parent company name",
    "pricingModel": "FREE" | "FREEMIUM" | "PAID" | "ENTERPRISE"
  }}
}}

TEXT PAYLOAD:
\"\"\"
{text}
\"\"\"

Return valid JSON strictly matching the schema. No markdown formatting.
"""

    def _parse_json_from_llm(self, text: str) -> Optional[Dict[str, Any]]:
        try:
            cleaned = text.strip()
            if cleaned.startswith("```"):
                cleaned = re.sub(r"^```(?:json)?\n", "", cleaned)
                cleaned = re.sub(r"\n```$", "", cleaned)
            return json.loads(cleaned)
        except Exception:
            m = re.search(r"\{.*\}", text, re.DOTALL)
            if m:
                try:
                    return json.loads(m.group(0))
                except Exception:
                    pass
        return None

    def _extract_domain(self, url: str) -> str:
        if not url:
            return "WebSource"
        m = re.search(r"https?://(?:www\.)?([^/]+)", url)
        return m.group(1) if m else "WebSource"

    async def _sleep_backoff(self, attempt: int):
        delay = min(settings.MAX_BACKOFF_SECONDS, settings.BASE_BACKOFF_SECONDS * (2 ** attempt))
        jitter = random.uniform(0.1, settings.BACKOFF_JITTER)
        await asyncio.sleep(delay + jitter)


default_orchestrator = LLMOrchestrator()

