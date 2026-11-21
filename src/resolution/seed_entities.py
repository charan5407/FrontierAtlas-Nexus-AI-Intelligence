"""
Seed entities loader and canonical definitions.
Loads 50+ known AI startups and their aliases, domains, and core products.
"""

import json
from pathlib import Path
from typing import Dict, List, Any, Optional

SEED_PATH = Path(__file__).resolve().parent.parent.parent / "config" / "canonical_seed.json"


class CanonicalEntity:
    def __init__(self, canonical_name: str, aliases: List[str], domains: List[str],
                 primary_products: List[str], founded_year: Optional[int] = None, employee_count: Optional[int] = None):
        self.canonical_name = canonical_name
        self.aliases = aliases
        self.domains = [d.lower().strip() for d in domains]
        self.primary_products = primary_products
        self.founded_year = founded_year
        self.employee_count = employee_count

    def to_dict(self) -> Dict[str, Any]:
        return {
            "canonical_name": self.canonical_name,
            "aliases": self.aliases,
            "domains": self.domains,
            "primary_products": self.primary_products,
            "founded_year": self.founded_year,
            "employee_count": self.employee_count
        }


def load_seed_entities() -> List[CanonicalEntity]:
    if not SEED_PATH.exists():
        return []
    with open(SEED_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    entities = []
    for item in data.get("entities", []):
        entities.append(CanonicalEntity(
            canonical_name=item["canonical_name"],
            aliases=item.get("aliases", []),
            domains=item.get("domains", []),
            primary_products=item.get("primary_products", []),
            founded_year=item.get("founded_year"),
            employee_count=item.get("employee_count")
        ))
    return entities
