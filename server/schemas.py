"""
Pydantic schemas for the WebVerity AI Readiness & Website Intelligence API.
Strictly conforms to the canonical report schema while providing rich UI metadata.
"""

from __future__ import annotations
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class AuditRequest(BaseModel):
    url: str = Field(..., description="Target website URL to audit (e.g., https://example.com)")
    max_pages: Optional[int] = Field(default=10, ge=1, le=20, description="Maximum pages to crawl")
    max_depth: Optional[int] = Field(default=2, ge=1, le=3, description="Maximum crawl depth")
    timeout: Optional[float] = Field(default=15.0, ge=1.0, le=60.0, description="Overall timeout in seconds")
    external_records: Optional[List[Dict[str, Any]]] = Field(default=None, description="Optional third-party corroboration records")


class SuggestedAction(BaseModel):
    summary: str
    priority: str
    implementation_details: Optional[str] = None


class Finding(BaseModel):
    id: str
    title: str
    category: str
    severity: str
    confidence: str
    observation: str
    evidence: str
    root_cause: str
    impact: str
    detection_method: str = "deterministic"
    affected_urls: List[str]
    suggested_action: SuggestedAction


class ProactiveRecommendation(BaseModel):
    id: str
    title: str
    opportunity: str
    suggested_action: SuggestedAction


class AuditSummary(BaseModel):
    total_findings: int = 0
    critical: int = 0
    high: int = 0
    medium: int = 0
    low: int = 0
    info: int = 0


class HeadingDto(BaseModel):
    tag: str
    level: int
    text: str
    dom_index: int


class PageDto(BaseModel):
    url: str
    normalized_url: str
    status_code: int
    response_time_ms: float
    page_archetype: str
    is_primary_page: bool
    title: str
    meta_description: str
    canonical_url: Optional[str] = None
    headings_count: int = 0
    headings: List[HeadingDto] = []
    schema_types: List[str] = []
    internal_links_count: int = 0
    external_links_count: int = 0
    extracted_facts: Dict[str, Any] = {}
    error_message: Optional[str] = None


class AuditResponse(BaseModel):
    id: str
    site: str
    audited_at: str
    site_archetype: str = "unknown"
    pages_audited: int = 0
    pages_discovered: int = 0
    crawl_duration_seconds: float = 0.0
    summary: AuditSummary
    findings: List[Finding] = []
    proactive_recommendations: List[ProactiveRecommendation] = []
    pages: List[PageDto] = []
    markdown_report: Optional[str] = None


class HealthResponse(BaseModel):
    status: str = "healthy"
    version: str = "1.0.0"
    timestamp: str
    services: Dict[str, str] = {
        "crawler": "ready",
        "orchestrator": "ready",
        "skills": "ready"
    }
