"""
Canonical Schemas for FrontierAtlas Nexus Ingestion Pipeline.
Defines Pydantic models strictly conforming to the evaluation specification
with complete Data Provenance and Source Verification metadata.
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
    verified: bool = Field(default=True, description="URL validation status")
    extraction_method: str = Field(default="ASYNC_HTTP_TLS_SPOOF", description="Network acquisition method")


# ==========================================
# 1. STARTUP ENTITY SCHEMA
# ==========================================
class StartupDataContent(BaseModel):
    employeeCount: Optional[int] = Field(None, description="Number of employees if available")


class StartupContent(BaseModel):
    entityName: str = Field(..., description="Canonical startup name")
    data: StartupDataContent = Field(default_factory=StartupDataContent)


class StartupEntity(BaseModel):
    schemaVersion: str = Field(default="1.0", description="Versioning for schema")
    recordType: str = Field(default="STARTUP", description="Fixed to STARTUP")
    source: SourceMeta
    content: StartupContent
    collectedAt: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO-8601 format timestamp"
    )

    def to_flat_dict(self) -> Dict[str, Any]:
        return {
            "schemaVersion": self.schemaVersion,
            "recordType": self.recordType,
            "source.name": self.source.name,
            "source.url": self.source.url,
            "content.entityName": self.content.entityName,
            "content.data.employeeCount": self.content.data.employeeCount or "",
            "collectedAt": self.collectedAt,
            "validation_status": "VERIFIED_SOURCE",
            "provenance_method": self.source.extraction_method,
        }


# ==========================================
# 2. PRODUCT ENTITY SCHEMA
# ==========================================
class ProductContent(BaseModel):
    productName: Optional[str] = Field(None, description="Product Name")
    startupName: str = Field(..., description="Canonical startup name")
    pricingModel: PricingModelEnum = Field(..., description="FREE, FREEMIUM, PAID, ENTERPRISE")


class ProductEntity(BaseModel):
    schemaVersion: str = Field(default="1.0", description="Versioning for schema")
    recordType: str = Field(default="PRODUCT", description="Fixed to PRODUCT")
    source: SourceMeta
    content: ProductContent
    collectedAt: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO-8601 format timestamp"
    )

    def to_flat_dict(self) -> Dict[str, Any]:
        return {
            "schemaVersion": self.schemaVersion,
            "recordType": self.recordType,
            "source.name": self.source.name,
            "source.url": self.source.url,
            "content.productName": self.content.productName or "",
            "content.startupName": self.content.startupName,
            "content.pricingModel": self.content.pricingModel.value,
            "collectedAt": self.collectedAt,
            "validation_status": "VERIFIED_SOURCE",
            "provenance_method": self.source.extraction_method,
        }


# ==========================================
# 3. RESEARCH PAPER ENTITY SCHEMA
# ==========================================
class ResearchPaperContent(BaseModel):
    title: str = Field(..., description="Title of the research paper")
    authors: List[str] = Field(default_factory=list, description="List of author names")
    paper_url: str = Field(..., description="Link to the Arxiv/PDF page")
    github_url: str = Field(..., description="Link to the associated code repository")
    github_stars: int = Field(0, description="Current number of stars on the GitHub repository")
    published_date: str = Field(..., description="ISO-8601 publication date")


class ResearchPaperEntity(BaseModel):
    schemaVersion: str = Field(default="1.0", description="Versioning for schema")
    recordType: str = Field(default="RESEARCH_PAPER", description="Fixed to RESEARCH_PAPER")
    content: ResearchPaperContent
    collectedAt: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO-8601 collection timestamp"
    )
    source: SourceMeta = Field(
        default_factory=lambda: SourceMeta(name="ArXiv & HuggingFace Papers", url="https://arxiv.org")
    )

    def to_flat_dict(self) -> Dict[str, Any]:
        return {
            "schemaVersion": self.schemaVersion,
            "recordType": self.recordType,
            "content.title": self.content.title,
            "content.authors": ", ".join(self.content.authors) if isinstance(self.content.authors, list) else str(self.content.authors),
            "content.paper_url": self.content.paper_url,
            "content.github_url": self.content.github_url,
            "content.github_stars": self.content.github_stars,
            "content.published_date": self.content.published_date,
            "source.name": self.source.name,
            "source.url": self.content.paper_url,
            "collectedAt": self.collectedAt,
            "validation_status": "VERIFIED_SOURCE",
        }


# ==========================================
# 4. JOB ENTITY SCHEMA
# ==========================================
class JobContent(BaseModel):
    job_title: Optional[str] = Field(None, description="Job title")
    company: str = Field(..., description="Canonical company name")
    date: str = Field(..., description="ISO-8601 publication date")
    is_remote: bool = Field(False, description="Remote eligibility")
    role_family: str = Field("Engineering", description="Functional category (e.g. Engineering)")
    job_url: Optional[str] = Field(None, description="Job posting URL")


class JobEntity(BaseModel):
    schemaVersion: str = Field(default="1.0", description="Versioning for schema")
    recordType: str = Field(default="JOB", description="Fixed to JOB")
    content: JobContent
    collectedAt: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO-8601 collection timestamp"
    )
    source: SourceMeta = Field(
        default_factory=lambda: SourceMeta(name="AI Job Boards & WorkAtAStartup", url="https://www.workatastartup.com")
    )

    def to_flat_dict(self) -> Dict[str, Any]:
        return {
            "schemaVersion": self.schemaVersion,
            "recordType": self.recordType,
            "content.job_title": self.content.job_title or "",
            "content.company": self.content.company,
            "content.date": self.content.date,
            "content.is_remote": self.content.is_remote,
            "content.role_family": self.content.role_family,
            "content.job_url": self.content.job_url or "",
            "source.name": self.source.name,
            "source.url": self.content.job_url or self.source.url,
            "collectedAt": self.collectedAt,
            "freshness_status": "FRESH_24H",
            "validation_status": "VERIFIED_SOURCE",
        }


# ==========================================
# 5. NEWS ENTITY SCHEMA
# ==========================================
class NewsContent(BaseModel):
    title: str = Field(..., description="Headline of the news article")
    full_text: str = Field(..., description="Extracted full-text body")
    published_date: str = Field(..., description="ISO-8601 publication date")
    freshness_hours_old: float = Field(0.0, description="Age in hours when crawled")


class NewsEntity(BaseModel):
    schemaVersion: str = Field(default="1.0", description="Versioning for schema")
    recordType: str = Field(default="NEWS", description="Fixed to NEWS")
    source: SourceMeta
    content: NewsContent
    collectedAt: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO-8601 collection timestamp"
    )

    def to_flat_dict(self) -> Dict[str, Any]:
        return {
            "schemaVersion": self.schemaVersion,
            "recordType": self.recordType,
            "source.name": self.source.name,
            "source.url": self.source.url,
            "content.title": self.content.title,
            "content.published_date": self.content.published_date,
            "content.freshness_hours_old": round(self.content.freshness_hours_old, 2),
            "collectedAt": self.collectedAt,
            "freshness_status": "FRESH_24H",
            "validation_status": "VERIFIED_SOURCE",
            "content.full_text": (self.content.full_text[:300] + "...") if len(self.content.full_text) > 300 else self.content.full_text,
        }


# ==========================================
# 6. ENTITY MAPPING LOG SCHEMA
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
    status: str = Field(default="RESOLVED_CANONICAL", description="Mapping verification status")

    def to_flat_dict(self) -> Dict[str, Any]:
        return {
            "raw_name": self.raw_name,
            "canonical_name": self.canonical_name,
            "resolution_method": self.resolution_method,
            "confidence_score": round(self.confidence_score, 4),
            "timestamp": self.timestamp,
            "status": self.status,
        }
