"""
Deterministic Entity Resolution Engine for FrontierAtlas Nexus.
Normalizes, deduplicates, and canonicalizes startup and product names
against a high-fidelity seed database and algorithmic rules.
"""

import re
import difflib
from typing import Tuple, Optional, List, Dict, Any
from datetime import datetime, timezone
from src.resolution.seed_entities import load_seed_entities, CanonicalEntity
from src.llm.schemas import EntityMappingLogEntry


class EntityResolver:
    LEGAL_PATTERNS = [
        r"\b(inc|incorporated|corporation|corp)\b",
        r"\b(llc|limited liability company)\b",
        r"\b(ltd|limited)\b",
        r"\b(pbc|public benefit corporation)\b",
        r"\b(sas|s\.a\.s|sa|s\.a)\b",
        r"\b(gmbh|g\.m\.b\.h)\b",
        r"\b(b\.v\.|bv)\b",
        r"\b(se|s\.e)\b",
        r"\b(pte|pte\. ltd\.|pvt|pvt\.)\b",
        r"\b(co|company)\b",
    ]

    GENERIC_AI_SUFFIXES = [
        r"\bai\b",
        r"\blabs\b",
        r"\btechnologies\b",
        r"\bsystems\b",
        r"\bresearch\b",
        r"\bintelligence\b",
        r"\bsoftware\b",
    ]

    def __init__(self, fuzzy_threshold: float = 0.85):
        self.fuzzy_threshold = fuzzy_threshold
        self.entities = load_seed_entities()
        self.canonical_map: Dict[str, str] = {}
        self.domain_map: Dict[str, str] = {}
        self.product_to_startup_map: Dict[str, str] = {}
        self.mapping_logs: List[EntityMappingLogEntry] = []

        self._build_indexes()

    def _build_indexes(self):
        for ent in self.entities:
            cname = ent.canonical_name
            # Self canonical mapping
            self.canonical_map[self.normalize_string(cname)] = cname
            self.canonical_map[self.clean_legal_and_suffixes(cname)] = cname

            # Alias mappings
            for alias in ent.aliases:
                self.canonical_map[self.normalize_string(alias)] = cname
                self.canonical_map[self.clean_legal_and_suffixes(alias)] = cname

            # Domain mappings
            for domain in ent.domains:
                clean_dom = domain.lower().replace("https://", "").replace("http://", "").split("/")[0]
                self.domain_map[clean_dom] = cname

            # Product to startup mappings
            for prod in ent.primary_products:
                self.product_to_startup_map[self.normalize_string(prod)] = cname

    @staticmethod
    def normalize_string(text: str) -> str:
        """Strip punctuation, excessive whitespace, and lower-case."""
        if not text:
            return ""
        text = text.lower().strip()
        # Remove common punctuation but preserve alphanumeric
        text = re.sub(r"[^\w\s]", "", text)
        text = re.sub(r"\s+", " ", text).strip()
        return text

    def clean_legal_and_suffixes(self, text: str) -> str:
        """Remove corporate suffixes (Inc, LLC, PBC, etc.)."""
        norm = self.normalize_string(text)
        for pattern in self.LEGAL_PATTERNS:
            norm = re.sub(pattern, "", norm, flags=re.IGNORECASE)
        norm = re.sub(r"\s+", " ", norm).strip()
        return norm

    def resolve(self, raw_name: str, source_url: Optional[str] = None) -> Tuple[str, str, float]:
        """
        Resolves a raw entity string to its canonical name.
        Returns: (canonical_name, resolution_method, confidence_score)
        """
        if not raw_name or not raw_name.strip():
            return "Unknown", "EMPTY_INPUT", 0.0

        raw_clean = raw_name.strip()
        norm = self.normalize_string(raw_clean)
        clean_no_legal = self.clean_legal_and_suffixes(raw_clean)

        # Stage 1: Exact canonical name match
        for ent in self.entities:
            if ent.canonical_name.lower() == raw_clean.lower():
                self._log_mapping(raw_clean, ent.canonical_name, "EXACT_CANONICAL_MATCH", 1.0)
                return ent.canonical_name, "EXACT_CANONICAL_MATCH", 1.0

        # Stage 2: Direct Alias Lookup
        if norm in self.canonical_map:
            cname = self.canonical_map[norm]
            self._log_mapping(raw_clean, cname, "ALIAS_LOOKUP_TABLE", 1.0)
            return cname, "ALIAS_LOOKUP_TABLE", 1.0

        # Stage 3: Legal / Corporate Suffix Stripping
        if clean_no_legal in self.canonical_map:
            cname = self.canonical_map[clean_no_legal]
            self._log_mapping(raw_clean, cname, "LEGAL_SUFFIX_STRIP", 0.98)
            return cname, "LEGAL_SUFFIX_STRIP", 0.98

        # Stage 4: Domain matching if source URL provided
        if source_url:
            for domain, cname in self.domain_map.items():
                if domain in source_url.lower():
                    self._log_mapping(raw_clean, cname, "SOURCE_DOMAIN_CORRELATION", 0.95)
                    return cname, "SOURCE_DOMAIN_CORRELATION", 0.95

        # Stage 5: Product-to-Startup attribution
        if norm in self.product_to_startup_map:
            cname = self.product_to_startup_map[norm]
            self._log_mapping(raw_clean, cname, "PRODUCT_ATTRIBUTION", 0.92)
            return cname, "PRODUCT_ATTRIBUTION", 0.92

        # Stage 6: High-Fidelity Fuzzy Matching against known entities
        # Fast-prune: only test entities that share at least one word token or starting letter
        input_words = set(clean_no_legal.split())
        best_match = None
        best_ratio = 0.0
        best_method = "FUZZY_STRING_SIMILARITY"

        for ent in self.entities:
            c_clean = self.clean_legal_and_suffixes(ent.canonical_name)
            ent_words = set(c_clean.split())
            # Fast check: skip if zero shared words and starting letters differ
            if not (input_words & ent_words) and (c_clean and clean_no_legal and c_clean[0] != clean_no_legal[0]):
                continue

            # SequenceMatcher ratio
            ratio1 = difflib.SequenceMatcher(None, clean_no_legal, c_clean).ratio()
            words_a = sorted(clean_no_legal.split())
            words_b = sorted(c_clean.split())
            ratio2 = difflib.SequenceMatcher(None, " ".join(words_a), " ".join(words_b)).ratio()

            max_r = max(ratio1, ratio2)

            # Check aliases as well
            for alias in ent.aliases:
                alias_clean = self.clean_legal_and_suffixes(alias)
                r_alias = difflib.SequenceMatcher(None, clean_no_legal, alias_clean).ratio()
                if r_alias > max_r:
                    max_r = r_alias

            if max_r > best_ratio:
                best_ratio = max_r
                best_match = ent.canonical_name

        if best_match and best_ratio >= self.fuzzy_threshold:
            self._log_mapping(raw_clean, best_match, best_method, best_ratio)
            return best_match, best_method, best_ratio

        # Stage 7: Deterministic Title-Case Canonicalization for new/unseeded entities
        # Cleans out corporate suffixes and standardizes casing
        derived_name = self._standardize_unseeded_name(raw_clean)
        method = "DETERMINISTIC_FORMATTER" if derived_name != raw_clean else "RAW_PRESERVED"
        score = 0.85 if derived_name != raw_clean else 0.80
        self._log_mapping(raw_clean, derived_name, method, score)
        return derived_name, method, score

    def _standardize_unseeded_name(self, text: str) -> str:
        """Standardizes capitalization, strips trailing corporate tags and punctuation."""
        t = re.sub(r"[,;]$", "", text.strip())
        for pattern in self.LEGAL_PATTERNS:
            t = re.sub(pattern, "", t, flags=re.IGNORECASE)
        t = re.sub(r"\s+", " ", t).strip()
        # Clean leading/trailing symbols
        t = t.strip(" -_.,'")
        # Preserve CamelCase or acronyms if already styled, else title case
        if t.isupper() and len(t) <= 5:
            return t
        words = t.split()
        capitalized = []
        for w in words:
            if w.lower() in ["ai", "ml", "api", "sdk", "ui", "ux", "db", "llm"]:
                capitalized.append(w.upper())
            elif w.lower() in ["and", "of", "the", "for", "in"]:
                capitalized.append(w.lower())
            else:
                capitalized.append(w.capitalize())
        return " ".join(capitalized) if capitalized else text

    def _log_mapping(self, raw_name: str, canonical_name: str, method: str, score: float):
        entry = EntityMappingLogEntry(
            raw_name=raw_name,
            canonical_name=canonical_name,
            resolution_method=method,
            confidence_score=score,
            timestamp=datetime.now(timezone.utc).isoformat()
        )
        self.mapping_logs.append(entry)

    def get_audit_logs(self) -> List[EntityMappingLogEntry]:
        return self.mapping_logs

    def export_audit_logs_dicts(self) -> List[Dict[str, Any]]:
        return [entry.to_flat_dict() for entry in self.mapping_logs]


# Singleton instance
default_resolver = EntityResolver()
