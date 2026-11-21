"""
Canonical Schemas for FrontierAtlas Nexus Ingestion Pipeline.
Defines Pydantic models strictly conforming to the evaluation specification
matching the exact fields and types from the expected schema tables.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional, Any, Dict
from pydantic import BaseModel, Field


class PricingModelEnum(str, Enum):
    FREE = "FREE"
    FREEMIUM = "FREEMIUM"
    PAID = "PAID"
    ENTERPRISE = "ENTERPRISE"


class SourceMeta(BaseModel):
    name: str = Field(..., description="Name of the source site")
    url: str = Field(..., description="Original source URL")


# ==========================================
# 1. STARTUP ENTITY SCHEMA (Exact Match to PDF Page 4-5)
# ==========================================
class StartupDataContent(BaseModel):
    employeeCount: Optional[int] = Field(None, description="Number of employees (if available)")


class StartupContent(BaseModel):
    entityName: str = Field(..., description="Canonical startup name")
    data: StartupDataContent = Field(default_factory=StartupDataContent)


class StartupEntity(BaseModel):
    schemaVersion: str = Field(default="1.0", description="Versioning for the schema (e.g., '1.0')")
    recordType: str = Field(default="STARTUP", description="Fixed to 'STARTUP'")
    source: SourceMeta
    content: StartupContent
    collectedAt: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO-8601 format"
    )

    def to_flat_dict(self) -> Dict[str, Any]:
        """Matches the exact 7 columns from Startup Entity table."""
        return {
            "schemaVersion": self.schemaVersion,
            "recordType": self.recordType,
            "source.name": self.source.name,
            "source.url": self.source.url,
            "content.entityName": self.content.entityName,
            "content.data.employeeCount": self.content.data.employeeCount if self.content.data.employeeCount is not None else "",
            "collectedAt": self.collectedAt,
        }


# ==========================================
# 2. PRODUCT ENTITY SCHEMA (Exact Match to PDF Page 5)
# ==========================================
class ProductContent(BaseModel):
    startupName: str = Field(..., description="Canonical startup name")
    pricingModel: PricingModelEnum = Field(..., description="FREE, FREEMIUM, PAID, ENTERPRISE")


class ProductEntity(BaseModel):
    schemaVersion: str = Field(default="1.0", description="Versioning for the schema (e.g., '1.0')")
    recordType: str = Field(default="PRODUCT", description="Fixed to 'PRODUCT'")
    source: SourceMeta
    content: ProductContent
    collectedAt: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO-8601 format"
    )

    def to_flat_dict(self) -> Dict[str, Any]:
        """Matches the exact 7 columns from Product Entity table."""
        return {
            "schemaVersion": self.schemaVersion,
            "recordType": self.recordType,
            "source.name": self.source.name,
            "source.url": self.source.url,
            "content.startupName": self.content.startupName,
            "content.pricingModel": self.content.pricingModel.value,
            "collectedAt": self.collectedAt,
        }


# ==========================================
# 3. RESEARCH PAPER ENTITY SCHEMA (Exact Match to PDF Page 6)
# ==========================================
class ResearchPaperContent(BaseModel):
    title: str = Field(..., description="Title of the research paper")
    authors: List[str] = Field(default_factory=list, description="List of author names")
    paper_url: str = Field(..., description="Link to the Arxiv/PDF page")
    github_url: str = Field(..., description="Link to the associated code repository (if any)")
    github_stars: int = Field(0, description="Current number of stars on the GitHub repository")
    published_date: str = Field(..., description="ISO-8601 publication date")


class ResearchPaperEntity(BaseModel):
    schemaVersion: str = Field(default="1.0", description="Versioning for the schema")
    recordType: str = Field(default="RESEARCH_PAPER", description="Fixed to 'RESEARCH_PAPER'")
    content: ResearchPaperContent

    def to_flat_dict(self) -> Dict[str, Any]:
        """Matches the exact 8 columns from Research Paper Entity table."""
        return {
            "schemaVersion": self.schemaVersion,
            "recordType": self.recordType,
            "content.title": self.content.title,
            "content.authors": ", ".join(self.content.authors) if isinstance(self.content.authors, list) else str(self.content.authors),
            "content.paper_url": self.content.paper_url,
            "content.github_url": self.content.github_url,
            "content.github_stars": self.content.github_stars,
            "content.published_date": self.content.published_date,
        }


# ==========================================
# 4. JOB ENTITY SCHEMA (Exact Match to PDF Page 6-7)
# ==========================================
class JobContent(BaseModel):
    company: str = Field(..., description="Canonical company name")
    date: str = Field(..., description="ISO-8601 publication date")
    is_remote: bool = Field(False, description="Remote eligibility")
    role_family: str = Field("Engineering", description="Functional category (e.g., 'Engineering')")


class JobEntity(BaseModel):
    schemaVersion: str = Field(default="1.0", description="Versioning for the schema")
    recordType: str = Field(default="JOB", description="Fixed to 'JOB'")
    content: JobContent

    def to_flat_dict(self) -> Dict[str, Any]:
        """Matches the exact 6 columns from Job Entity table."""
        return {
            "schemaVersion": self.schemaVersion,
            "recordType": self.recordType,
            "content.company": self.content.company,
            "content.date": self.content.date,
            "content.is_remote": self.content.is_remote,
            "content.role_family": self.content.role_family,
        }


# ==========================================
# 5. NEWS ENTITY SCHEMA (Deliverable Tab 5)
# ==========================================
class NewsContent(BaseModel):
    title: str = Field(..., description="Headline of the news article")
    published_date: str = Field(..., description="ISO-8601 publication date")
    full_text: str = Field(..., description="Extracted full-text body")


class NewsEntity(BaseModel):
    schemaVersion: str = Field(default="1.0", description="Versioning for the schema")
    recordType: str = Field(default="NEWS", description="Fixed to 'NEWS'")
    source: SourceMeta
    content: NewsContent

    def to_flat_dict(self) -> Dict[str, Any]:
        return {
            "schemaVersion": self.schemaVersion,
            "recordType": self.recordType,
            "source.name": self.source.name,
            "source.url": self.source.url,
            "content.title": self.content.title,
            "content.published_date": self.content.published_date,
            "content.full_text": (self.content.full_text[:300] + "...") if len(self.content.full_text) > 300 else self.content.full_text,
        }


# ==========================================
# 6. ENTITY MAPPING LOG SCHEMA (Deliverable Tab 6)
# ==========================================
class EntityMappingLogEntry(BaseModel):
    raw_name: str = Field(..., description="Raw extracted name")
    canonical_name: str = Field(..., description="Resolved canonical entity name")
    resolution_method: str = Field(..., description="Resolution strategy applied")
    confidence_score: float = Field(..., description="Similarity confidence between 0.0 and 1.0")
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="Resolution ISO timestamp"
    )

    def to_flat_dict(self) -> Dict[str, Any]:
        return {
            "raw_name": self.raw_name,
            "canonical_name": self.canonical_name,
            "resolution_method": self.resolution_method,
            "confidence_score": round(self.confidence_score, 4),
            "timestamp": self.timestamp,
        }
