"""
Freshness & Corroboration Audit Domain Skill Implementation.
Audits temporal signals, cross-page factual consistency across internal URLs,
and reconciles first-party claims against authoritative external corroboration.
"""

from typing import List, Dict, Any, Optional
from core.models import CrawlContext, PageEvidence, PageArchetype, SiteArchetype
from core.freshness_analyzer import (
    analyze_cross_page_consistency,
    analyze_temporal_freshness,
    evaluate_external_corroboration
)


def check_freshness_and_corroboration(
    crawl_context: CrawlContext,
    external_records: Optional[List[Dict[str, Any]]] = None
) -> List[Dict[str, Any]]:
    """
    Executes freshness and cross-page factual consistency audit over the shared CrawlContext.
    Returns a list of standardized Finding dictionaries.
    """
    findings: List[Dict[str, Any]] = []
    finding_counter = 1

    # -------------------------------------------------------------------------
    # 1. INTERNAL CROSS-PAGE FACTUAL CONTRADICTIONS (Check D-02)
    # -------------------------------------------------------------------------
    internal_conflicts = analyze_cross_page_consistency(crawl_context)
    for conflict in internal_conflicts:
        evidence_content = conflict.get("evidence_text") or (
            "Affected URLs and conflicting values:\n" + "\n".join(f"- URL: {url} -> '{val}'" for url, val in conflict["values"].items())
        )
        title_str = conflict.get("title") or f"Internal cross-page factual contradiction ({conflict['entity_type'].replace('_', ' ')})"
        root_cause_str = conflict.get("root_cause") or "Independent website subpages maintain disparate, unsynchronized copies of core business contact or commercial attributes."
        impact_str = conflict.get("impact") or "Creates conflicting machine signals; automated systems encountering mismatched values face entity ambiguity and degraded grounding reliability."
        summary_str = conflict.get("suggested_action_summary") or f"Unify and synchronize the {conflict['entity_type'].replace('_', ' ')} across all site landing pages."
        details_str = conflict.get("suggested_action_details") or "Centralize business contact and pricing data in a single shared repository or global header/footer component."

        findings.append({
            "id": f"F-{finding_counter:03d}",
            "title": title_str,
            "category": "freshness_corroboration",
            "severity": conflict.get("severity", "high"),
            "confidence": "high",
            "observation": conflict["description"],
            "evidence": evidence_content,
            "root_cause": root_cause_str,
            "impact": impact_str,
            "detection_method": "deterministic",
            "affected_urls": conflict["urls"],
            "suggested_action": {
                "summary": summary_str,
                "implementation_details": details_str,
                "priority": "high"
            }
        })
        finding_counter += 1

    # -------------------------------------------------------------------------
    # 2. TEMPORAL FRESHNESS: GENUINELY STALE OFFERINGS (Check D-01)
    # -------------------------------------------------------------------------
    temporal_data = analyze_temporal_freshness(crawl_context)

    if temporal_data["has_expired_promotions"]:
        for stale_item in temporal_data["stale_offering_urls"]:
            findings.append({
                "id": f"F-{finding_counter:03d}",
                "title": "Active webpage displays expired promotional or temporal dates",
                "category": "freshness_corroboration",
                "severity": "medium",
                "confidence": "high",
                "observation": f"Active webpage contains temporal copy referencing an expired date: '{stale_item['snippet']}'.",
                "evidence": f"URL: {stale_item['url']}\nObserved Expired Snippet: \"{stale_item['snippet']}\"\nExpired Reference Year: {stale_item['expired_year']}",
                "root_cause": "Promotional campaign dates or time-sensitive terms were not retired or updated following campaign conclusion.",
                "impact": "Automated extractors may misinterpret expired terms as current offerings or downweight page timeliness during retrieval.",
                "detection_method": "deterministic",
                "affected_urls": [stale_item["url"]],
                "suggested_action": {
                    "summary": "Update or archive expired promotional notices and temporal terms.",
                    "implementation_details": "Remove expired campaign banners or redirect outdated promotion URLs to current active offerings.",
                    "priority": "medium"
                }
            })
            finding_counter += 1

    # -------------------------------------------------------------------------
    # 3. TEMPORAL FRESHNESS: OUTDATED COPYRIGHT YEAR OBSERVATION (Check D-03)
    # -------------------------------------------------------------------------
    if temporal_data["old_copyright_signal"]:
        old_year = temporal_data["oldest_copyright_year"]
        # Treat as an informational / low observation rather than an automatic defect
        findings.append({
            "id": f"F-{finding_counter:03d}",
            "title": f"Outdated footer copyright year ({old_year}) observed on active web assets",
            "category": "freshness_corroboration",
            "severity": "low",
            "confidence": "high",
            "observation": f"Footer copyright declaration references year '{old_year}', which is outdated relative to the current calendar year.",
            "evidence": f"Domain: {crawl_context.domain}\nObserved Copyright Year: {old_year}",
            "root_cause": "Footer template uses a static hardcoded copyright string rather than a dynamic server date.",
            "impact": "Presents a potential recency ambiguity signal for automated crawlers evaluating temporal maintenance indicators.",
            "detection_method": "deterministic",
            "affected_urls": [crawl_context.root_url],
            "suggested_action": {
                "summary": "Implement dynamic current-year copyright rendering in global footer templates.",
                "implementation_details": "Replace static copyright strings with dynamic date rendering (e.g. '&copy; ' + new Date().getFullYear()).",
                "priority": "low"
            }
        })
        finding_counter += 1

    # -------------------------------------------------------------------------
    # 4. EXTERNAL CORROBORATION EVALUATION (Check D-05)
    # -------------------------------------------------------------------------
    if external_records:
        first_party_claims = {
            "domain": crawl_context.domain,
        }
        # Gather primary phone and company name from homepage
        for p in crawl_context.pages:
            if p.is_primary_page:
                if p.title:
                    first_party_claims["company_name"] = p.title.split("|")[0].split("-")[0].strip()
                for b in p.json_ld:
                    if "Organization" in b.schema_types and b.parsed_data:
                        if "name" in b.parsed_data:
                            first_party_claims["organization_name"] = str(b.parsed_data["name"])

        corroboration_discrepancies = evaluate_external_corroboration(first_party_claims, external_records)
        for c_disc in corroboration_discrepancies:
            if c_disc.get("is_disputed"):
                findings.append({
                    "id": f"F-{finding_counter:03d}",
                    "title": f"External authoritative registries report conflicting records for {c_disc['attribute']}",
                    "category": "freshness_corroboration",
                    "severity": "low",
                    "confidence": "medium",
                    "observation": c_disc["description"],
                    "evidence": f"Attribute: {c_disc['attribute']}\nFirst-Party Claim: '{c_disc['first_party_value']}'\nConflicting External Values: {c_disc['external_value']}",
                    "root_cause": "Multiple third-party registries maintain discordant factual records for this entity.",
                    "impact": "Creates external grounding ambiguity where automated knowledge graphs receive contradictory signals from independent third-party sources.",
                    "detection_method": "hybrid",
                    "affected_urls": [crawl_context.root_url],
                    "suggested_action": {
                        "summary": f"Audit external directory profiles to establish consistent public record across third-party authorities.",
                        "implementation_details": f"Submit corrections to third-party databases to ensure unified {c_disc['attribute']} values.",
                        "priority": "low"
                    }
                })
            else:
                findings.append({
                    "id": f"F-{finding_counter:03d}",
                    "title": f"Discrepancy between first-party claim and authoritative external record ({c_disc['attribute']})",
                    "category": "freshness_corroboration",
                    "severity": "medium",
                    "confidence": "high",
                    "observation": c_disc["description"],
                    "evidence": f"External Source: {c_disc['source']} ({c_disc.get('source_type', 'registry')})\nFirst-Party Claim: '{c_disc['first_party_value']}'\nExternal Authority Value: '{c_disc['external_value']}'",
                    "root_cause": "First-party website attributes do not match verified external registries or business authority records.",
                    "impact": "Automated knowledge reconciliation systems encountering contradictory authority records face identity and attribute uncertainty.",
                    "detection_method": "hybrid",
                    "affected_urls": [crawl_context.root_url],
                    "suggested_action": {
                        "summary": f"Reconcile first-party website {c_disc['attribute']} with official external directory listings.",
                        "implementation_details": f"Ensure business registration profiles and website identity data are synchronized.",
                        "priority": "medium"
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
        site_archetype=SiteArchetype.CORPORATE,
        robots_policy=None,
        sitemap_summary=None,
        pages=[]
    )
    print(json.dumps(check_freshness_and_corroboration(sample_ctx), indent=2))
