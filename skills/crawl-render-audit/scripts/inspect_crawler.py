"""
Crawl & Render Audit Domain Skill Implementation.
Audits crawler barriers, granular robots.txt AI bot exclusions,
confirmed client-side rendering (CSR) fact omissions, and non-text image content traps.
"""

from typing import List, Dict, Any, Optional
from core.models import CrawlContext, PageEvidence, PageArchetype


def inspect_crawl_and_render(crawl_context: CrawlContext) -> List[Dict[str, Any]]:
    """
    Executes the crawl & render audit over the shared CrawlContext.
    Returns a list of standardized Finding dictionaries.
    """
    findings: List[Dict[str, Any]] = []
    finding_counter = 1

    # -------------------------------------------------------------------------
    # 1. GRANULAR ROBOTS.TXT AI CRAWLER DIRECTIVE AUDIT
    # -------------------------------------------------------------------------
    if crawl_context.robots_policy.exists:
        policy = crawl_context.robots_policy
        safe_private_paths = (
            "/admin", "/checkout", "/cart", "/login", "/account", "/internal",
            "/private", "/api", "/staging", "/wp-admin", "/wp-includes",
            "/cgi-bin", "/search", "/tmp", "/temp", "/auth", "/user", "/orders"
        )
        crucial_public_prefixes = (
            "/product", "/pricing", "/services", "/catalog", "/shop",
            "/store", "/items", "/posts", "/articles", "/about", "/contact", "/docs"
        )

        for bot_name, rule in policy.bot_rules.items():
            if not rule.disallowed_paths and not rule.is_fully_blocked:
                continue

            # Filter out standard safe private paths
            problematic_disallows = [
                p for p in rule.disallowed_paths 
                if not any(p.startswith(sp) for sp in safe_private_paths)
            ]

            if rule.is_fully_blocked or "/" in rule.disallowed_paths:
                # Site-wide block
                if bot_name == "*":
                    findings.append({
                        "id": f"F-{finding_counter:03d}",
                        "title": "Site-wide crawler disallow in robots.txt blocks all automated agents",
                        "category": "crawlability",
                        "severity": "critical",
                        "confidence": "high",
                        "observation": "robots.txt contains 'User-agent: * Disallow: /', blocking all compliant crawlers.",
                        "evidence": f"URL: {policy.url}\nDirectives:\nUser-agent: *\nDisallow: /",
                        "root_cause": "Wildcard disallow rule at root directory level prevents automated indexing.",
                        "impact": "Both conventional search engines and all AI retrieval bots are completely restricted from crawling and indexing any page on this domain.",
                        "detection_method": "deterministic",
                        "affected_urls": [policy.url],
                        "suggested_action": {
                            "summary": "Update robots.txt to permit public route crawling while restricting only private/administrative paths.",
                            "implementation_details": "Change 'Disallow: /' to targeted paths like 'Disallow: /admin/' and 'Disallow: /cart/'.",
                            "priority": "critical"
                        }
                    })
                    finding_counter += 1

                elif bot_name in ("PerplexityBot", "ChatGPT-User", "Bingbot"):
                    # Real-time retrieval bot block
                    findings.append({
                        "id": f"F-{finding_counter:03d}",
                        "title": f"robots.txt blocks real-time AI citation bot ({bot_name})",
                        "category": "crawlability",
                        "severity": "high",
                        "confidence": "high",
                        "observation": f"robots.txt explicitly disallows '{bot_name}' from crawling public routes.",
                        "evidence": f"URL: {policy.url}\nDirectives:\nUser-agent: {bot_name}\nDisallow: /",
                        "root_cause": f"Explicit User-agent rule targeting {bot_name} with root disallow.",
                        "impact": f"Real-time conversational search queries on platforms powered by {bot_name} cannot browse or cite this website during live user inquiries.",
                        "detection_method": "deterministic",
                        "affected_urls": [policy.url],
                        "suggested_action": {
                            "summary": f"Permit {bot_name} to crawl public catalog and informational pages for live citation.",
                            "implementation_details": f"Add 'User-agent: {bot_name}\\nAllow: /' in {policy.url}.",
                            "priority": "high"
                        }
                    })
                    finding_counter += 1

                elif bot_name in ("GPTBot", "ClaudeBot", "Google-Extended"):
                    # Training ingestion bot block
                    findings.append({
                        "id": f"F-{finding_counter:03d}",
                        "title": f"robots.txt excludes brand content from AI model training ({bot_name})",
                        "category": "crawlability",
                        "severity": "medium",
                        "confidence": "high",
                        "observation": f"robots.txt explicitly disallows {bot_name}.",
                        "evidence": f"URL: {policy.url}\nDirectives:\nUser-agent: {bot_name}\nDisallow: /",
                        "root_cause": f"Explicit disallow rule restricting {bot_name} from reading public web corpus.",
                        "impact": f"Brand facts and knowledge will be omitted from future foundational model pre-training corpora generated by the operator of {bot_name}.",
                        "detection_method": "deterministic",
                        "affected_urls": [policy.url],
                        "suggested_action": {
                            "summary": f"Review whether blocking {bot_name} aligns with brand discovery goals.",
                            "implementation_details": f"If broader AI awareness is desired, remove 'Disallow: /' under 'User-agent: {bot_name}'.",
                            "priority": "medium"
                        }
                    })
                    finding_counter += 1

            else:
                # Targeted path block: only flag if it genuinely restricts public content/commercial paths
                crucial_blocked = [
                    p for p in problematic_disallows 
                    if any(p.startswith(cp) for cp in crucial_public_prefixes)
                ]
                if crucial_blocked:
                    paths_str = ", ".join(crucial_blocked)
                    findings.append({
                        "id": f"F-{finding_counter:03d}",
                        "title": f"robots.txt blocks crucial public paths for {bot_name}",
                        "category": "crawlability",
                        "severity": "high" if any(p in paths_str for p in ("/product", "/pricing", "/services", "/catalog")) else "medium",
                        "confidence": "high",
                        "observation": f"robots.txt restricts {bot_name} from accessing public routes: {paths_str}",
                        "evidence": f"URL: {policy.url}\nUser-agent: {bot_name}\nDisallowed paths: {paths_str}",
                        "root_cause": f"Disallow directives applied to key commercial/informational URL paths.",
                        "impact": f"Automated readers for {bot_name} cannot access or ground answers using the content within {paths_str}.",
                        "detection_method": "deterministic",
                        "affected_urls": [policy.url],
                        "suggested_action": {
                            "summary": f"Remove disallow restrictions on public commercial routes ({paths_str}) for {bot_name}.",
                            "implementation_details": f"Update robots.txt rules to ensure public catalog paths remain crawlable.",
                            "priority": "high"
                        }
                    })
                    finding_counter += 1

    # -------------------------------------------------------------------------
    # 2. CONFIRMED CLIENT-SIDE RENDERING (CSR) FACT OMISSIONS
    # -------------------------------------------------------------------------
    for page in crawl_context.pages:
        if page.status_code != 200:
            continue

        # Only emit finding if substantive missing facts were proven missing from raw HTML
        if page.missing_facts_in_raw:
            missing_preview = ", ".join(page.missing_facts_in_raw[:4])
            if len(page.missing_facts_in_raw) > 4:
                missing_preview += f" (+{len(page.missing_facts_in_raw) - 4} more)"

            is_primary = page.is_primary_page or page.page_archetype in (PageArchetype.HOMEPAGE, PageArchetype.PRODUCT_DETAIL, PageArchetype.PRICING)
            severity = "high" if is_primary else "medium"

            findings.append({
                "id": f"F-{finding_counter:03d}",
                "title": f"Key factual content missing from initial HTML response ({page.page_archetype.value})",
                "category": "machine_readability",
                "severity": severity,
                "confidence": "high",
                "observation": f"Crucial factual data is rendered via client-side JavaScript but is absent from the server's initial HTML payload.",
                "evidence": f"URL: {page.url}\nPage Archetype: {page.page_archetype.value}\nVerified missing facts in raw HTML: [{missing_preview}]\nRaw Text Length: {page.raw_text_length} chars vs Rendered: {len(page.rendered_text or '')} chars.",
                "root_cause": "Product attributes, pricing, or core body copy are injected purely via client-side JavaScript hydration without server-side rendering (SSR).",
                "impact": "Automated extractors and retrieval pipelines that inspect only the initial HTTP response without full JavaScript execution will not observe these factual attributes, creating machine discoverability and grounding blind spots.",
                "detection_method": "hybrid",
                "affected_urls": [page.url],
                "suggested_action": {
                    "summary": "Implement Server-Side Rendering (SSR) or Static Site Generation (SSG) for core factual attributes.",
                    "implementation_details": "Ensure prices, availability, specifications, and primary copy are rendered directly inside the server HTML response before client hydration.",
                    "priority": severity
                }
            })
            finding_counter += 1

        elif page.required_rendering_trigger and not getattr(crawl_context, "rendering_available", True):
            # SPA container detected but headless browser rendering was not available
            findings.append({
                "id": f"F-{finding_counter:03d}",
                "title": f"Client-side framework container detected (rendering unverified in environment)",
                "category": "machine_readability",
                "severity": "info",
                "confidence": "low",
                "observation": "Page contains an empty client-side application container, but headless rendering verification was unavailable in the current environment.",
                "evidence": f"URL: {page.url}\nRaw text length: {page.raw_text_length} chars\nHeadless browser available: False",
                "root_cause": "Headless browser binaries are not installed or active in the execution environment.",
                "impact": "Unable to verify whether factual content hydrates into the DOM on client execution.",
                "detection_method": "deterministic",
                "affected_urls": [page.url],
                "suggested_action": {
                    "summary": "Verify that critical product and business facts are server-rendered in the initial HTML.",
                    "priority": "low"
                }
            })
            finding_counter += 1

    # -------------------------------------------------------------------------
    # 3. NON-TEXT LOCKED FACTUAL CONTENT (Images lacking alt on commercial pages)
    # -------------------------------------------------------------------------
    for page in crawl_context.pages:
        if page.status_code != 200:
            continue

        trapped_images = [
            img for img in page.images 
            if img.is_content_relevant and not img.has_alt
        ]

        if trapped_images:
            img_srcs = ", ".join([img.src for img in trapped_images[:3]])
            keywords = ", ".join(list(set([img.context_keyword for img in trapped_images if img.context_keyword])))

            findings.append({
                "id": f"F-{finding_counter:03d}",
                "title": "Technical data or chart locked in image without descriptive alternative text",
                "category": "machine_readability",
                "severity": "medium",
                "confidence": "high" if any(k in keywords for k in ("chart", "diagram", "table", "specs", "flowchart")) else "medium",
                "observation": f"Images presenting technical or structured information ({keywords}) lack descriptive alternative text.",
                "evidence": f"URL: {page.url}\nImages without alt: [{img_srcs}]\nContext Cue: {keywords}",
                "root_cause": "Technical diagrams, comparison charts, or specification sheets are embedded inside raster graphics without machine-readable alt text or HTML representation.",
                "impact": "Automated text parsers, screen readers, and AI discovery agents cannot extract structured figures, dimensions, or technical workflows locked inside bitmap images.",
                "detection_method": "deterministic",
                "affected_urls": [page.url],
                "suggested_action": {
                    "summary": "Provide descriptive alt text or render complex tables and workflows using accessible HTML markup.",
                    "implementation_details": "Add detailed alt='...' attributes describing the exact diagram workflow or data points, or convert raster tables into semantic HTML <table> elements.",
                    "priority": "medium"
                }
            })
            finding_counter += 1

    # -------------------------------------------------------------------------
    # 4. CANONICAL INTEGRITY & MULTI-HOP CHAINS
    # -------------------------------------------------------------------------
    pages_map = {}
    for p in crawl_context.pages:
        pages_map[p.url] = p
        if p.normalized_url:
            pages_map[p.normalized_url] = p

    for page in crawl_context.pages:
        if page.status_code != 200 or not page.canonical_url:
            continue

        # Standard self-referential canonicals are best practice; ignore them
        norm_canonical = page.canonical_url.rstrip("/")
        norm_page_url = page.url.rstrip("/")
        if norm_canonical == norm_page_url:
            continue

        chain = [page.url]
        curr_canonical = page.canonical_url
        is_cycle = False

        while curr_canonical and len(chain) <= 5:
            # Check if canonical delegates to a previously visited URL in chain
            if curr_canonical.rstrip("/") in [u.rstrip("/") for u in chain]:
                # True cycle: A -> B -> A
                if len(chain) >= 2:
                    is_cycle = True
                    chain.append(curr_canonical)
                break

            target_page = pages_map.get(curr_canonical) or pages_map.get(curr_canonical.rstrip("/"))
            if target_page and target_page.canonical_url:
                target_canon_norm = target_page.canonical_url.rstrip("/")
                target_url_norm = target_page.url.rstrip("/")
                if target_canon_norm != target_url_norm:
                    chain.append(curr_canonical)
                    curr_canonical = target_page.canonical_url
                    continue

            # Terminal URL reached
            chain.append(curr_canonical)
            break

        if is_cycle:
            chain_str = " -> ".join(chain)
            findings.append({
                "id": f"F-{finding_counter:03d}",
                "title": "Circular canonical reference loop detected",
                "category": "crawlability",
                "severity": "high",
                "confidence": "high",
                "observation": f"The page participates in a circular canonical loop: {chain_str}",
                "evidence": f"URL: {page.url}\nCanonical Loop: {chain_str}",
                "root_cause": "Canonical link elements form a closed loop, conflicting over the authoritative URL representation.",
                "impact": "Search crawlers and AI retrieval indexers drop or oscillate indexing signals when encountering circular canonical declarations.",
                "detection_method": "deterministic",
                "affected_urls": list(set(chain)),
                "suggested_action": {
                    "summary": "Break the canonical loop by pointing all variant pages directly to a single authoritative canonical URL.",
                    "priority": "high"
                }
            })
            finding_counter += 1
        elif len(chain) >= 3:
            chain_str = " -> ".join(chain)
            findings.append({
                "id": f"F-{finding_counter:03d}",
                "title": "Multi-hop canonical chain detected",
                "category": "crawlability",
                "severity": "medium",
                "confidence": "high",
                "observation": f"The page canonical declaration involves multiple intermediate hops: {chain_str}",
                "evidence": f"URL: {page.url}\nCanonical Chain: {chain_str}",
                "root_cause": "Canonical target delegates to another canonical URL rather than pointing directly to the final canonical destination.",
                "impact": "Multi-hop canonical chains introduce ambiguity and delay signal consolidation during crawl indexing.",
                "suggested_action": {
                    "summary": f"Update the canonical link to point directly to the terminal URL ('{chain[-1]}').",
                    "priority": "medium"
                }
            })
            finding_counter += 1

    return findings


if __name__ == "__main__":
    import json
    # Standalone verification
    sample_context = CrawlContext(
        root_url="https://example.com",
        domain="example.com",
        audited_at="2026-09-02T12:00:00Z",
        site_archetype="ecommerce",
        robots_policy=None,
        sitemap_summary=None,
        pages=[]
    )
    print(json.dumps(inspect_crawl_and_render(sample_context), indent=2))
