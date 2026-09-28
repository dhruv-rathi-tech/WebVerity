"""
Structured Data & Entity Audit Domain Skill Implementation.
Audits schema.org JSON-LD syntax, archetype-specific schema expectations,
entity disambiguation (sameAs), and factual contradictions between structured data and visible text.
"""

from typing import List, Dict, Any, Optional
from core.models import CrawlContext, PageEvidence, PageArchetype, SiteArchetype
from core.schema_analyzer import extract_entities_from_json_ld, reconcile_schema_against_visible_text


def validate_structured_data(crawl_context: CrawlContext) -> List[Dict[str, Any]]:
    """
    Executes structured data and entity graph audit over the shared CrawlContext.
    Returns a list of standardized Finding dictionaries.
    """
    findings: List[Dict[str, Any]] = []
    finding_counter = 1

    site_arch = crawl_context.site_archetype

    for page in crawl_context.pages:
        if page.status_code != 200:
            continue

        page_arch = page.page_archetype
        entities = extract_entities_from_json_ld(page.json_ld)
        visible_text = page.rendered_text or page.raw_text

        # ---------------------------------------------------------------------
        # 1. JSON-LD SYNTAX AND MALFORMED AST AUDIT (Check C-02)
        # ---------------------------------------------------------------------
        for syntax_err in entities["syntax_errors"]:
            findings.append({
                "id": f"F-{finding_counter:03d}",
                "title": "Invalid JSON-LD syntax prevents machine-readable parsing",
                "category": "structured_data",
                "severity": "high",
                "confidence": "high",
                "observation": f"A <script type='application/ld+json'> tag contains malformed JSON syntax: '{syntax_err}'.",
                "evidence": f"URL: {page.url}\nSyntax Error: {syntax_err}",
                "root_cause": "The embedded JSON-LD script contains syntax errors such as unescaped characters, trailing commas, or invalid JSON encoding.",
                "impact": "Automated parsers fail to decode the structured data block, leaving declared entities inaccessible for machine extraction and grounding.",
                "detection_method": "deterministic",
                "affected_urls": [page.url],
                "suggested_action": {
                    "summary": "Fix JSON-LD formatting and validate syntax against standard JSON specification.",
                    "implementation_details": "Ensure valid JSON syntax (no trailing commas, double-quoted keys and strings). Validate with json.loads().",
                    "priority": "high"
                }
            })
            finding_counter += 1

        # ---------------------------------------------------------------------
        # 2. STRUCTURED-TO-VISIBLE FACT CONTRADICTION AUDIT (Check C-03)
        # ---------------------------------------------------------------------
        discrepancies = reconcile_schema_against_visible_text(entities, visible_text)
        for disc in discrepancies:
            findings.append({
                "id": f"F-{finding_counter:03d}",
                "title": f"Factual inconsistency between structured metadata and visible copy ({disc['field']})",
                "category": "structured_data",
                "severity": "high",
                "confidence": "high",
                "observation": disc["description"],
                "evidence": f"URL: {page.url}\nDeclared Schema Value: {disc['schema_val']}\nObserved Visible Copy Value: {disc['visible_val']}",
                "root_cause": "Structured metadata is maintained out-of-sync with the primary visible content source.",
                "impact": "Creates conflicting machine signals; automated systems encountering mismatched values face entity ambiguity and degraded grounding reliability.",
                "detection_method": "deterministic",
                "affected_urls": [page.url],
                "suggested_action": {
                    "summary": f"Synchronize the {disc['field']} property in JSON-LD with the live rendered page value.",
                    "implementation_details": f"Derive JSON-LD attributes dynamically from the exact same backend database/model feeding the visible UI component.",
                    "priority": "high"
                }
            })
            finding_counter += 1

        # ---------------------------------------------------------------------
        # 3. ARCHETYPE-SENSITIVE MISSING FOUNDATIONAL SCHEMA (Check C-01)
        # ---------------------------------------------------------------------
        # A. E-Commerce Product Detail Page with concrete commercial facts missing Product/Offer schema
        if page_arch == PageArchetype.PRODUCT_DETAIL or (site_arch == SiteArchetype.ECOMMERCE and "/product/" in page.url):
            has_product = "Product" in entities["types"]
            has_offer = "Offer" in entities["types"] or entities["has_nested_offers"]
            
            # Gating check: does the page actually present observable commercial attributes (price, cart, availability)?
            has_commercial_signals = any(k in visible_text.lower() for k in ("$", "₹", "€", "£", "usd", "in stock", "add to cart", "buy now", "sku"))
            
            if not has_product and not has_offer and has_commercial_signals:
                findings.append({
                    "id": f"F-{finding_counter:03d}",
                    "title": "Visible commercial product facts lack structured Product/Offer representation",
                    "category": "structured_data",
                    "severity": "high",
                    "confidence": "high",
                    "observation": "Page presents visible commercial attributes (pricing, purchase actions, stock status) but provides no schema.org/Product or Offer markup.",
                    "evidence": f"URL: {page.url}\nPage Archetype: {page_arch.value}\nVisible commercial signals present: True\nExisting Schemas: {list(entities['types']) if entities['types'] else 'None'}",
                    "root_cause": "Commercial attributes are embedded only in visual markup without corresponding machine-readable JSON-LD metadata.",
                    "impact": "Automated assistants and search agents must rely on heuristic text scraping rather than direct structured entity extraction for price, brand, and availability.",
                    "detection_method": "deterministic",
                    "affected_urls": [page.url],
                    "suggested_action": {
                        "summary": "Represent the visible product commercial attributes using schema.org/Product and Offer JSON-LD.",
                        "implementation_details": 'Embed <script type="application/ld+json">{"@context":"https://schema.org","@type":"Product","name":"...","offers":{"@type":"Offer","price":"...","priceCurrency":"USD","availability":"https://schema.org/InStock"}}</script>.',
                        "priority": "high"
                    }
                })
                finding_counter += 1

        # B. Local Service missing LocalBusiness schema with observable business contact facts
        elif site_arch == SiteArchetype.LOCAL_SERVICE and page.is_primary_page:
            has_contact_signals = any(k in visible_text.lower() for k in ("phone", "call", "address", "hours", "contact", "@"))
            if "LocalBusiness" not in entities["types"] and has_contact_signals:
                findings.append({
                    "id": f"F-{finding_counter:03d}",
                    "title": "Local service business identity lacks LocalBusiness structured data",
                    "category": "structured_data",
                    "severity": "medium",
                    "confidence": "high",
                    "observation": "Local service website presents physical contact and operational information without schema.org/LocalBusiness markup.",
                    "evidence": f"URL: {page.url}\nSite Archetype: {site_arch.value}\nSchemas Detected: {list(entities['types']) if entities['types'] else 'None'}",
                    "root_cause": "The site does not declare structured address, telephone, or operating hours schemas.",
                    "impact": "Automated systems answering location-sensitive inquiries face ambiguity resolving operating hours, geographic service radius, and official contact channels.",
                    "detection_method": "deterministic",
                    "affected_urls": [page.url],
                    "suggested_action": {
                        "summary": "Implement schema.org/LocalBusiness structured data with address, telephone, and openingHoursSpecification.",
                        "implementation_details": "Add JSON-LD containing '@type': 'LocalBusiness', 'telephone', 'address': {'@type': 'PostalAddress'}, 'openingHoursSpecification'.",
                        "priority": "medium"
                    }
                })
                finding_counter += 1

        # C. Article / Blog with editorial content missing Article schema
        elif page_arch == PageArchetype.ARTICLE:
            if not any(t in entities["types"] for t in ("Article", "NewsArticle", "BlogPosting")):
                findings.append({
                    "id": f"F-{finding_counter:03d}",
                    "title": "Editorial article content lacks structured Article metadata",
                    "category": "structured_data",
                    "severity": "medium",
                    "confidence": "high",
                    "observation": "Editorial article page lacks schema.org/Article markup.",
                    "evidence": f"URL: {page.url}\nPage Archetype: {page_arch.value}\nSchemas Detected: {list(entities['types']) if entities['types'] else 'None'}",
                    "root_cause": "The article template does not output standard schema.org/Article markup.",
                    "impact": "Automated retrieval engines cannot unambiguously identify author bylines, publication timestamps, and headline entities for citation grounding.",
                    "detection_method": "deterministic",
                    "affected_urls": [page.url],
                    "suggested_action": {
                        "summary": "Add schema.org/Article JSON-LD with headline, author, and datePublished properties.",
                        "implementation_details": "Add '@type': 'Article', 'headline', 'author': {'@type': 'Person', 'name': '...'}, 'datePublished'.",
                        "priority": "medium"
                    }
                })
                finding_counter += 1

        # ---------------------------------------------------------------------
        # 4. ENTITY DISAMBIGUATION (sameAs) & RELATIONSHIPS (Check C-04 & C-05)
        # ---------------------------------------------------------------------
        # Check Organization sameAs on Primary Homepage only when Organization is explicitly declared
        if page.is_primary_page and ("Organization" in entities["types"] or "Brand" in entities["types"]):
            if not entities["same_as"]:
                findings.append({
                    "id": f"F-{finding_counter:03d}",
                    "title": "Organization entity schema lacks external authority disambiguation (sameAs)",
                    "category": "entity_clarity",
                    "severity": "low",
                    "confidence": "high",
                    "observation": "The Organization/Brand schema defines the primary identity but does not include 'sameAs' URIs to authoritative external registry or corporate identity entries.",
                    "evidence": f"URL: {page.url}\nDeclared Schemas: {list(entities['types'])}\nsameAs property: Empty / Absent",
                    "root_cause": "The Organization JSON-LD markup does not link to external canonical entity identifiers.",
                    "impact": "Automated entity resolution engines may encounter ambiguity linking this brand to established canonical corporate records or knowledge graph nodes.",
                    "detection_method": "deterministic",
                    "affected_urls": [page.url],
                    "suggested_action": {
                        "summary": "Add relevant authoritative 'sameAs' identifiers (such as official business registries or verified corporate profiles) to the Organization schema.",
                        "implementation_details": 'Include "sameAs": ["https://..."] linking to official registry or verified identity records.',
                        "priority": "low"
                    }
                })
                finding_counter += 1

        # Check Product missing nested Offer relationship
        if "Product" in entities["types"] and not entities["has_nested_offers"] and not entities["prices"]:
            findings.append({
                "id": f"F-{finding_counter:03d}",
                "title": "Product schema lacks nested Offer entity relationship",
                "category": "structured_data",
                "severity": "medium",
                "confidence": "high",
                "observation": "Product schema is declared but lacks nested offers (schema.org/Offer) for price and stock availability.",
                "evidence": f"URL: {page.url}\nDeclared: Product\nMissing: offers property with price and priceCurrency",
                "root_cause": "Product entity is defined in isolation without commercial Offer transaction node.",
                "impact": "Commercial attributes remain machine-inaccessible despite having top-level Product schema.",
                "detection_method": "deterministic",
                "affected_urls": [page.url],
                "suggested_action": {
                    "summary": "Nest an Offer entity within the Product schema containing price, currency, and availability.",
                    "implementation_details": '"offers": {"@type": "Offer", "price": "...", "priceCurrency": "USD", "availability": "https://schema.org/InStock"}',
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
        site_archetype=SiteArchetype.ECOMMERCE,
        robots_policy=None,
        sitemap_summary=None,
        pages=[]
    )
    print(json.dumps(validate_structured_data(sample_ctx), indent=2))
