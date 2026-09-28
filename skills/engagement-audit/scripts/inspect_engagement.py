"""
On-Site Engagement Audit Domain Skill Implementation.
Audits visitor orientation, semantic heading hierarchy integrity,
intent continuity, and context-sensitive next-step pathways across pages.
"""

from typing import List, Dict, Any, Optional
from core.models import CrawlContext, PageEvidence, PageArchetype, SiteArchetype
from core.engagement_analyzer import analyze_page_engagement


def inspect_engagement(crawl_context: CrawlContext) -> List[Dict[str, Any]]:
    """
    Executes the on-site engagement audit over the shared CrawlContext.
    Returns a list of standardized Finding dictionaries.
    """
    findings: List[Dict[str, Any]] = []
    finding_counter = 1

    site_arch = crawl_context.site_archetype

    for page in crawl_context.pages:
        if page.status_code != 200:
            continue

        raw_issues = analyze_page_engagement(page, site_arch)
        for issue in raw_issues:
            findings.append({
                "id": f"F-{finding_counter:03d}",
                "title": issue["title"],
                "category": "on_site_engagement",
                "severity": issue["severity"],
                "confidence": "high",
                "observation": issue["observation"],
                "evidence": issue["evidence"],
                "root_cause": issue["root_cause"],
                "impact": issue["impact"],
                "detection_method": "deterministic",
                "affected_urls": [page.url],
                "suggested_action": {
                    "summary": issue["suggested_action"],
                    "implementation_details": f"Review template structure on {page.page_archetype.value} layout.",
                    "priority": issue["priority"]
                }
            })
            finding_counter += 1

    return findings


if __name__ == "__main__":
    import json
    sample_ctx = CrawlContext(
        root_url="https://example.com",
        domain="example.com",
        audited_at="2026-09-02T12:00:00Z",
        site_archetype=SiteArchetype.ECOMMERCE,
        robots_policy=None,
        sitemap_summary=None,
        pages=[]
    )
    print(json.dumps(inspect_engagement(sample_ctx), indent=2))
