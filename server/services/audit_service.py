"""
Audit Service Layer.
Integrates the existing Crawl engine, Agent Skills, and Audit Orchestrator
into a unified asynchronous API service with in-memory persistence.
"""

from __future__ import annotations
import os
import sys
import uuid
import datetime
from typing import Dict, Optional, List, Any

# Ensure workspace root in path
_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from core.models import CrawlContext, PageEvidence
from core.crawler import crawl_site
from core.url_utils import normalize_url
from audit import AuditOrchestrator, render_markdown_report
from server.schemas import (
    AuditRequest,
    AuditResponse,
    AuditSummary,
    Finding,
    SuggestedAction,
    ProactiveRecommendation,
    PageDto,
    HeadingDto
)


class AuditService:
    """
    Coordinates API-level audit runs, maintains in-memory report cache,
    and constructs enriched DTOs for the investigation workbench UI.
    """

    def __init__(self):
        self._orchestrator = AuditOrchestrator()
        # In-memory store for audit results
        self._audit_store: Dict[str, AuditResponse] = {}

    async def execute_audit(self, request: AuditRequest) -> AuditResponse:
        """
        Executes end-to-end audit for the requested URL using the existing audit engine.
        """
        audit_id = f"aud_{uuid.uuid4().hex[:12]}"
        now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
        
        normalized_url = normalize_url(request.url)
        if not normalized_url or not normalized_url.startswith("http"):
            response = AuditResponse(
                id=audit_id,
                site=request.url or "invalid-url",
                audited_at=now_iso,
                site_archetype="unknown",
                pages_audited=0,
                pages_discovered=0,
                crawl_duration_seconds=0.0,
                summary=AuditSummary(),
                findings=[],
                proactive_recommendations=[],
                pages=[],
                markdown_report="# Invalid URL\nPlease provide a valid HTTP/HTTPS URL."
            )
            self._audit_store[audit_id] = response
            return response

        # 1. Bounded Asynchronous Crawl
        max_pages = min(max(1, request.max_pages or 10), 20)
        max_depth = min(max(1, request.max_depth or 2), 3)
        timeout = max(1.0, float(request.timeout or 15.0))

        try:
            crawl_context = await crawl_site(
                root_url=normalized_url,
                max_pages=max_pages,
                max_depth=max_depth,
                timeout_seconds=timeout
            )
        except Exception as e:
            # Handle transport failure gracefully
            raw_report = self._orchestrator.run(
                target_url=normalized_url,
                crawl_options={"max_pages": max_pages, "max_depth": max_depth, "timeout": timeout},
                external_records=request.external_records
            )
            md_content = render_markdown_report(raw_report)
            response = self._build_audit_response(
                audit_id=audit_id,
                raw_report=raw_report,
                crawl_context=None,
                markdown_report=md_content
            )
            self._audit_store[audit_id] = response
            return response

        # 2. Multi-Skill Execution & Synthesis via Existing Orchestrator
        raw_report = self._orchestrator.run(
            target_url=normalized_url,
            existing_context=crawl_context,
            external_records=request.external_records
        )

        md_content = render_markdown_report(raw_report)

        response = self._build_audit_response(
            audit_id=audit_id,
            raw_report=raw_report,
            crawl_context=crawl_context,
            markdown_report=md_content
        )

        self._audit_store[audit_id] = response
        return response

    def get_audit(self, audit_id: str) -> Optional[AuditResponse]:
        """Retrieves cached audit report by ID."""
        return self._audit_store.get(audit_id)

    def _build_audit_response(
        self,
        audit_id: str,
        raw_report: Dict[str, Any],
        crawl_context: Optional[CrawlContext],
        markdown_report: str
    ) -> AuditResponse:
        """Converts raw orchestrator dictionary and crawl context into validated AuditResponse DTO."""
        summary_raw = raw_report.get("summary", {})
        summary = AuditSummary(
            total_findings=summary_raw.get("total_findings", 0),
            critical=summary_raw.get("critical", 0),
            high=summary_raw.get("high", 0),
            medium=summary_raw.get("medium", 0),
            low=summary_raw.get("low", 0),
            info=summary_raw.get("info", 0)
        )

        findings: List[Finding] = []
        for f in raw_report.get("findings", []):
            act_raw = f.get("suggested_action", {})
            action = SuggestedAction(
                summary=act_raw.get("summary", "Remediate issue."),
                priority=act_raw.get("priority", f.get("severity", "medium")),
                implementation_details=act_raw.get("implementation_details")
            )
            findings.append(
                Finding(
                    id=f.get("id", "F-000"),
                    title=f.get("title", ""),
                    category=f.get("category", "crawlability"),
                    severity=f.get("severity", "info"),
                    confidence=f.get("confidence", "high"),
                    observation=f.get("observation", ""),
                    evidence=f.get("evidence", ""),
                    root_cause=f.get("root_cause", ""),
                    impact=f.get("impact", ""),
                    detection_method=f.get("detection_method", "deterministic"),
                    affected_urls=f.get("affected_urls", []),
                    suggested_action=action
                )
            )

        proactive: List[ProactiveRecommendation] = []
        for r in raw_report.get("proactive_recommendations", []):
            act_raw = r.get("suggested_action", {})
            action = SuggestedAction(
                summary=act_raw.get("summary", ""),
                priority=act_raw.get("priority", "low"),
                implementation_details=act_raw.get("implementation_details")
            )
            proactive.append(
                ProactiveRecommendation(
                    id=r.get("id", "REC-000"),
                    title=r.get("title", ""),
                    opportunity=r.get("opportunity", ""),
                    suggested_action=action
                )
            )

        pages: List[PageDto] = []
        site_archetype = "unknown"
        pages_audited = 0
        pages_discovered = 0
        crawl_duration = 0.0

        if crawl_context:
            site_archetype = crawl_context.site_archetype.value if hasattr(crawl_context.site_archetype, "value") else str(crawl_context.site_archetype)
            pages_audited = len(crawl_context.pages)
            pages_discovered = crawl_context.total_discovered_urls
            crawl_duration = crawl_context.crawl_duration_seconds

            for p in crawl_context.pages:
                heading_dtos = [
                    HeadingDto(
                        tag=h.tag,
                        level=h.level,
                        text=h.text,
                        dom_index=h.dom_index
                    )
                    for h in p.heading_tree[:20]  # bounded headings
                ]
                
                # Extract unique schema types from json_ld blocks
                schema_types = []
                for jb in p.json_ld:
                    for st in jb.schema_types:
                        if st not in schema_types:
                            schema_types.append(st)

                page_archetype_str = p.page_archetype.value if hasattr(p.page_archetype, "value") else str(p.page_archetype)

                pages.append(
                    PageDto(
                        url=p.url,
                        normalized_url=p.normalized_url,
                        status_code=p.status_code,
                        response_time_ms=p.response_time_ms,
                        page_archetype=page_archetype_str,
                        is_primary_page=p.is_primary_page,
                        title=p.title or "",
                        meta_description=p.meta_description or "",
                        canonical_url=p.canonical_url,
                        headings_count=len(p.heading_tree),
                        headings=heading_dtos,
                        schema_types=schema_types,
                        internal_links_count=len(p.internal_links),
                        external_links_count=len(p.external_links),
                        extracted_facts=p.extracted_facts,
                        error_message=p.error_message
                    )
                )

        return AuditResponse(
            id=audit_id,
            site=raw_report.get("site", ""),
            audited_at=raw_report.get("audited_at", datetime.datetime.now(datetime.timezone.utc).isoformat()),
            site_archetype=site_archetype,
            pages_audited=pages_audited,
            pages_discovered=pages_discovered,
            crawl_duration_seconds=crawl_duration,
            summary=summary,
            findings=findings,
            proactive_recommendations=proactive,
            pages=pages,
            markdown_report=markdown_report
        )


# Global singleton instance for the server
audit_service = AuditService()
