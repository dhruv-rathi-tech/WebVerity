"""
Archetype classification engine for sites and individual pages.
Uses deterministic, observable signals (URL paths, schema types, keyword patterns, link topologies).
"""

import urllib.parse
from typing import List
from core.models import SiteArchetype, PageArchetype, PageEvidence


def classify_page_archetype(page: PageEvidence, is_root: bool = False) -> PageArchetype:
    """
    Classifies an individual page based on URL structure, schemas, and content signals.
    """
    if is_root or page.url.rstrip("/").endswith(urllib.parse.urlparse(page.url).netloc):
        return PageArchetype.HOMEPAGE

    parsed = urllib.parse.urlparse(page.url)
    path = parsed.path.lower()

    # Check legal first
    if any(k in path for k in ("/privacy", "/terms", "/legal", "/cookie", "/disclaimer", "/tos")):
        return PageArchetype.LEGAL

    # Check pricing
    if any(k in path for k in ("/pricing", "/plans", "/cost", "/tiers", "/subscription")):
        return PageArchetype.PRICING

    # Check contact / support
    if any(k in path for k in ("/contact", "/support", "/get-in-touch", "/reach-us")):
        return PageArchetype.CONTACT

    # Check about / company
    if any(k in path for k in ("/about", "/team", "/company", "/our-story", "/leadership")):
        return PageArchetype.ABOUT

    # Check FAQ
    if any(k in path for k in ("/faq", "/help", "/questions")) or any("FAQPage" in b.schema_types for b in page.json_ld):
        return PageArchetype.FAQ

    # Check product detail
    has_product_schema = any("Product" in b.schema_types or "Offer" in b.schema_types for b in page.json_ld)
    if has_product_schema or any(k in path for k in ("/product/", "/item/", "/p/", "/dp/", "/goods/")):
        return PageArchetype.PRODUCT_DETAIL

    # Check category catalog
    if any(k in path for k in ("/category/", "/categories/", "/catalog/", "/collection/", "/collections/", "/shop/", "/store/")):
        return PageArchetype.CATEGORY_CATALOG

    # Check article / blog
    has_article_schema = any("Article" in b.schema_types or "NewsArticle" in b.schema_types or "BlogPosting" in b.schema_types for b in page.json_ld)
    if has_article_schema or any(k in path for k in ("/blog/", "/news/", "/article/", "/posts/", "/insights/")):
        return PageArchetype.ARTICLE

    return PageArchetype.OTHER


def classify_site_archetype(pages: List[PageEvidence]) -> SiteArchetype:
    """
    Aggregates signals across all crawled pages to determine the overarching site archetype.
    """
    if not pages:
        return SiteArchetype.UNKNOWN

    scores = {
        SiteArchetype.ECOMMERCE: 0,
        SiteArchetype.B2B_SAAS: 0,
        SiteArchetype.LOCAL_SERVICE: 0,
        SiteArchetype.PUBLISHER: 0,
        SiteArchetype.CORPORATE: 0,
        SiteArchetype.PORTFOLIO: 0,
    }

    for p in pages:
        path = urllib.parse.urlparse(p.url).path.lower()
        all_schemas = [t for b in p.json_ld for t in b.schema_types]
        text_lower = p.raw_text.lower()

        # E-Commerce Signals (Requires concrete transactional/commercial evidence)
        if "Product" in all_schemas or "Offer" in all_schemas:
            scores[SiteArchetype.ECOMMERCE] += 5
        if any(k in path for k in ("/cart", "/checkout", "/basket", "/shop/", "/store/", "/orders", "/buy/")):
            scores[SiteArchetype.ECOMMERCE] += 4
        if any(k in text_lower for k in ("add to cart", "buy now", "shopping cart", "in stock", "free shipping", "view cart", "order online")):
            scores[SiteArchetype.ECOMMERCE] += 3

        # SaaS Signals
        if "SoftwareApplication" in all_schemas:
            scores[SiteArchetype.B2B_SAAS] += 5
        if any(k in path for k in ("/pricing", "/features", "/docs", "/integrations", "/api")):
            scores[SiteArchetype.B2B_SAAS] += 3
        if any(k in text_lower for k in ("free trial", "request demo", "book a demo", "get started for free", "api reference")):
            scores[SiteArchetype.B2B_SAAS] += 2

        # Local Service Signals
        if "LocalBusiness" in all_schemas or "PostalAddress" in all_schemas:
            scores[SiteArchetype.LOCAL_SERVICE] += 5
        if any(k in text_lower for k in ("opening hours", "call now", "service area", "schedule appointment")):
            scores[SiteArchetype.LOCAL_SERVICE] += 3

        # Publisher Signals
        if any(s in all_schemas for s in ("Article", "NewsArticle", "BlogPosting")):
            scores[SiteArchetype.PUBLISHER] += 4
        if any(k in path for k in ("/news", "/blog", "/author", "/articles", "/wiki", "/encyclopedia")):
            scores[SiteArchetype.PUBLISHER] += 3
        if any(k in text_lower for k in ("encyclopedia", "free encyclopedia", "editorial team", "journalism")):
            scores[SiteArchetype.PUBLISHER] += 2

        # Portfolio Signals
        if any(k in path for k in ("/portfolio", "/works", "/case-studies")):
            scores[SiteArchetype.PORTFOLIO] += 4
        if any(k in text_lower for k in ("selected works", "art director", "case studies", "freelance designer", "my portfolio")):
            scores[SiteArchetype.PORTFOLIO] += 3

        # Corporate / Organization Signals
        if any(s in all_schemas for s in ("Organization", "Corporation", "NGO")):
            scores[SiteArchetype.CORPORATE] += 4
        if any(k in path for k in ("/about", "/careers", "/investors", "/press", "/team", "/company", "/products")):
            scores[SiteArchetype.CORPORATE] += 2
        if any(k in text_lower for k in ("mission", "leadership", "board of directors", "press release", "non-profit", "foundation", "open source", "privacy policy")):
            scores[SiteArchetype.CORPORATE] += 2

    # Find highest score with threshold
    sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    best_archetype, top_score = sorted_scores[0]

    if top_score >= 2:
        return best_archetype
    elif any(p.page_archetype == PageArchetype.HOMEPAGE for p in pages):
        return SiteArchetype.CORPORATE
    else:
        return SiteArchetype.UNKNOWN
