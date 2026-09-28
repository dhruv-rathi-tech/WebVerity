"""
Deterministic synthetic evaluation fixtures for Phase 9 End-to-End Evaluation.
Covers 18 distinct audit scenarios, including unseen archetypes, negative false-positive controls,
and cross-skill multi-fault scenarios.
"""

from typing import Dict, Any, List, Optional
from core.models import (
    CrawlContext, PageEvidence, SiteArchetype, PageArchetype,
    HeadingItem, LinkItem, ImageItem, JsonLdBlock, RobotsPolicy,
    SitemapSummary, BotRule
)


def get_all_eval_fixtures() -> Dict[str, Dict[str, Any]]:
    """
    Returns a dictionary of all 18 evaluation scenarios:
    scenario_id -> {
        "id": int,
        "name": str,
        "description": str,
        "archetype": SiteArchetype,
        "context": Optional[CrawlContext],
        "target_url": str,
        "external_records": Optional[List[Dict[str, Any]]],
        "expected_defects": int,
        "expected_categories": List[str],
        "expected_root_cause_keywords": List[str],
        "forbidden_findings": List[str],  # substrings that must NOT appear in titles
    }
    """
    fixtures = {}

    # -------------------------------------------------------------------------
    # 1. Healthy, Well-Structured Static Site
    # -------------------------------------------------------------------------
    p1 = PageEvidence(
        url="https://stellar-analytics.example/",
        normalized_url="https://stellar-analytics.example/",
        status_code=200,
        response_time_ms=25.0,
        content_type="text/html",
        page_archetype=PageArchetype.HOMEPAGE,
        is_primary_page=True,
        title="Stellar Analytics | Enterprise Telemetry Platform",
        meta_description="Real-time telemetry and distributed observability for cloud-native teams.",
        canonical_url="https://stellar-analytics.example/",
        meta_tags={},
        raw_html="""<!DOCTYPE html>
<html><head><title>Stellar Analytics</title></head>
<body>
  <h1>Stellar Analytics — Observability Platform</h1>
  <h2>Enterprise Metric Intelligence</h2>
  <p>Unified telemetry pipelines for microservices.</p>
  <a href="/pricing">View Pricing Plans</a>
  <a href="/contact">Schedule Architecture Review</a>
</body></html>""",
        raw_text="Stellar Analytics — Observability Platform. Enterprise Metric Intelligence. Unified telemetry pipelines for microservices. View Pricing Plans. Schedule Architecture Review.",
        raw_text_length=175,
        raw_word_count=22,
        heading_tree=[
            HeadingItem(tag="h1", level=1, text="Stellar Analytics — Observability Platform", dom_index=0),
            HeadingItem(tag="h2", level=2, text="Enterprise Metric Intelligence", dom_index=1),
        ],
        internal_links=[
            LinkItem(url="/pricing", anchor_text="View Pricing Plans", is_internal=True),
            LinkItem(url="/contact", anchor_text="Schedule Architecture Review", is_internal=True),
        ],
        json_ld=[
            JsonLdBlock(
                raw_json='{"@context": "https://schema.org", "@type": "Organization", "name": "Stellar Analytics Inc", "url": "https://stellar-analytics.example", "sameAs": ["https://www.wikidata.org/wiki/Q99999"]}',
                parsed_data={
                    "@context": "https://schema.org",
                    "@type": "Organization",
                    "name": "Stellar Analytics Inc",
                    "url": "https://stellar-analytics.example",
                    "sameAs": ["https://www.wikidata.org/wiki/Q99999"]
                },
                schema_types=["Organization"]
            )
        ],
        extracted_dates={"copyright_year": "2026"}
    )
    ctx1 = CrawlContext(
        root_url="https://stellar-analytics.example/",
        domain="stellar-analytics.example",
        audited_at="2026-09-03T12:00:00Z",
        site_archetype=SiteArchetype.B2B_SAAS,
        robots_policy=RobotsPolicy(
            exists=True,
            url="https://stellar-analytics.example/robots.txt",
            raw_content="User-agent: *\nAllow: /\nDisallow: /admin/\nSitemap: https://stellar-analytics.example/sitemap.xml",
            bot_rules={"*": BotRule(user_agent="*", allowed_paths=["/"], disallowed_paths=["/admin/"])}
        ),
        sitemap_summary=SitemapSummary(exists=True, total_urls_in_sitemaps=4),
        pages=[p1]
    )
    fixtures["1_healthy_static_site"] = {
        "id": 1,
        "name": "Healthy, Well-Structured Static Site",
        "description": "B2B SaaS homepage with complete semantic hierarchy, schema, valid robots, and clear pathways.",
        "archetype": SiteArchetype.B2B_SAAS,
        "context": ctx1,
        "target_url": "https://stellar-analytics.example/",
        "external_records": None,
        "expected_defects": 0,
        "expected_categories": [],
        "expected_root_cause_keywords": [],
        "forbidden_findings": ["contradiction", "missing", "defect", "dead-end", "severe"]
    }

    # -------------------------------------------------------------------------
    # 2. JavaScript-Heavy Site with Important Facts Missing from Initial HTML
    # -------------------------------------------------------------------------
    p2 = PageEvidence(
        url="https://hyper-audio.example/headphones/pro-anc",
        normalized_url="https://hyper-audio.example/headphones/pro-anc",
        status_code=200,
        response_time_ms=45.0,
        content_type="text/html",
        page_archetype=PageArchetype.PRODUCT_DETAIL,
        is_primary_page=True,
        title="Hyper Audio Pro Wireless ANC Headphones",
        meta_description="",
        canonical_url=None,
        meta_tags={},
        raw_html="""<!DOCTYPE html>
<html><head><title>Hyper Audio</title></head>
<body>
  <div id="root">Loading product experience...</div>
  <script src="/static/app.bundle.js"></script>
</body></html>""",
        raw_text="Loading product experience...",
        raw_text_length=28,
        raw_word_count=3,
        rendered_dom="""<!DOCTYPE html>
<html><head><title>Hyper Audio Pro Wireless ANC Headphones</title></head>
<body>
  <div id="root">
    <h1>Hyper Audio Pro Wireless ANC Headphones</h1>
    <p class="price">$349.00 USD</p>
    <p class="stock">In Stock — Ready to ship</p>
    <p class="specs">40mm Beryllium Drivers, 45hr Battery, Hybrid ANC</p>
    <button>Add to Cart</button>
    <a href="/accessories">Browse Replacement Pads</a>
  </div>
</body></html>""",
        rendered_text="Hyper Audio Pro Wireless ANC Headphones. $349.00 USD. In Stock — Ready to ship. 40mm Beryllium Drivers, 45hr Battery, Hybrid ANC. Add to Cart. Browse Replacement Pads.",
        missing_facts_in_raw=["$349.00 USD", "In Stock", "40mm Beryllium Drivers"],
        heading_tree=[HeadingItem(tag="h1", level=1, text="Hyper Audio Pro Wireless ANC Headphones", dom_index=0)],
        internal_links=[LinkItem(url="/accessories", anchor_text="Browse Replacement Pads", is_internal=True)],
        json_ld=[
            JsonLdBlock(
                raw_json='{"@context": "https://schema.org", "@type": "Product", "name": "Hyper Audio Pro Wireless ANC Headphones", "offers": {"@type": "Offer", "price": "349.00", "priceCurrency": "USD", "availability": "https://schema.org/InStock"}}',
                parsed_data={
                    "@context": "https://schema.org",
                    "@type": "Product",
                    "name": "Hyper Audio Pro Wireless ANC Headphones",
                    "offers": {
                        "@type": "Offer",
                        "price": "349.00",
                        "priceCurrency": "USD",
                        "availability": "https://schema.org/InStock"
                    }
                },
                schema_types=["Product", "Offer"]
            )
        ]
    )
    ctx2 = CrawlContext(
        root_url="https://hyper-audio.example/",
        domain="hyper-audio.example",
        audited_at="2026-09-03T12:00:00Z",
        site_archetype=SiteArchetype.ECOMMERCE,
        robots_policy=RobotsPolicy(exists=True, url="https://hyper-audio.example/robots.txt", raw_content="User-agent: *\nAllow: /"),
        sitemap_summary=SitemapSummary(exists=False),
        pages=[p2]
    )
    fixtures["2_javascript_heavy_csr_omissions"] = {
        "id": 2,
        "name": "JavaScript-Heavy Site with Important Facts Missing from Initial HTML",
        "description": "E-commerce product page whose pricing, availability, and specs exist solely in rendered DOM.",
        "archetype": SiteArchetype.ECOMMERCE,
        "context": ctx2,
        "target_url": "https://hyper-audio.example/",
        "external_records": None,
        "expected_defects": 1,
        "expected_categories": ["machine_readability"],
        "expected_root_cause_keywords": ["hydration", "server-side"],
        "forbidden_findings": ["GPTBot", "PerplexityBot"]
    }

    # -------------------------------------------------------------------------
    # 3. Invalid/Missing Structured Data
    # -------------------------------------------------------------------------
    p3 = PageEvidence(
        url="https://nordic-wear.example/about",
        normalized_url="https://nordic-wear.example/about",
        status_code=200,
        response_time_ms=30.0,
        content_type="text/html",
        page_archetype=PageArchetype.ABOUT,
        is_primary_page=False,
        title="About Nordic Expedition Wear",
        meta_description="Heritage polar expedition apparel craftsmanship.",
        canonical_url=None,
        meta_tags={},
        raw_html="""<!DOCTYPE html>
<html><head>
  <script type="application/ld+json">
  {"@context": "https://schema.org", "@type": "Organization", "name": "Nordic Wear", } // Syntax error trailing comma
  </script>
</head>
<body>
  <h1>About Nordic Expedition Wear</h1>
  <p>Founded in Oslo in 2018, Nordic Wear crafts specialized gear for arctic research expeditions.</p>
  <a href="/contact">Get in Touch</a>
</body></html>""",
        raw_text="About Nordic Expedition Wear. Founded in Oslo in 2018, Nordic Wear crafts specialized gear for arctic research expeditions. Get in Touch.",
        raw_text_length=146,
        raw_word_count=20,
        json_ld=[
            JsonLdBlock(
                raw_json='{"@context": "https://schema.org", "@type": "Organization", "name": "Nordic Wear", }',
                has_syntax_error=True,
                error_message="Trailing comma at line 1 column 87"
            )
        ],
        heading_tree=[HeadingItem(tag="h1", level=1, text="About Nordic Expedition Wear", dom_index=0)],
        internal_links=[LinkItem(url="/contact", anchor_text="Get in Touch", is_internal=True)]
    )
    ctx3 = CrawlContext(
        root_url="https://nordic-wear.example/",
        domain="nordic-wear.example",
        audited_at="2026-09-03T12:00:00Z",
        site_archetype=SiteArchetype.CORPORATE,
        robots_policy=RobotsPolicy(exists=False, url="", raw_content=""),
        sitemap_summary=SitemapSummary(exists=False),
        pages=[p3]
    )
    fixtures["3_invalid_missing_structured_data"] = {
        "id": 3,
        "name": "Invalid Structured Data Syntax",
        "description": "Page with malformed JSON-LD syntax preventing machine extraction.",
        "archetype": SiteArchetype.CORPORATE,
        "context": ctx3,
        "target_url": "https://nordic-wear.example/",
        "external_records": None,
        "expected_defects": 1,
        "expected_categories": ["structured_data"],
        "expected_root_cause_keywords": ["syntax", "unescaped", "trailing comma", "encoding"],
        "forbidden_findings": []
    }

    # -------------------------------------------------------------------------
    # 4. Product/E-commerce Site with Legitimate Sale and Variant Pricing (Negative Trap)
    # -------------------------------------------------------------------------
    p4 = PageEvidence(
        url="https://lumina-lighting.example/lamp/solaris",
        normalized_url="https://lumina-lighting.example/lamp/solaris",
        status_code=200,
        response_time_ms=28.0,
        content_type="text/html",
        page_archetype=PageArchetype.PRODUCT_DETAIL,
        is_primary_page=True,
        title="Solaris Ambient Floor Lamp",
        meta_description="Dimmable brass architectural floor lamp.",
        canonical_url=None,
        meta_tags={},
        raw_html="""<!DOCTYPE html>
<html><head>
  <script type="application/ld+json">
  {
    "@context": "https://schema.org",
    "@type": "Product",
    "name": "Solaris Ambient Floor Lamp",
    "offers": {
      "@type": "Offer",
      "price": "189.00",
      "priceCurrency": "USD",
      "availability": "https://schema.org/InStock"
    }
  }
  </script>
</head>
<body>
  <h1>Solaris Ambient Floor Lamp</h1>
  <p>Sale Price: $189.00 USD (Original Price: $249.00 MSRP — Save $60)</p>
  <p>Variants: Brass $189.00 | Matte Black $209.00</p>
  <p>Status: In Stock</p>
  <button>Add to Cart</button>
  <a href="/lamps">View All Lighting</a>
</body></html>""",
        raw_text="Solaris Ambient Floor Lamp. Sale Price: $189.00 USD (Original Price: $249.00 MSRP — Save $60). Variants: Brass $189.00 | Matte Black $209.00. Status: In Stock. Add to Cart. View All Lighting.",
        raw_text_length=196,
        raw_word_count=32,
        json_ld=[
            JsonLdBlock(
                raw_json='{"@context": "https://schema.org", "@type": "Product", "name": "Solaris Ambient Floor Lamp", "offers": {"@type": "Offer", "price": "189.00", "priceCurrency": "USD", "availability": "https://schema.org/InStock"}}',
                parsed_data={
                    "@context": "https://schema.org",
                    "@type": "Product",
                    "name": "Solaris Ambient Floor Lamp",
                    "offers": {
                        "@type": "Offer",
                        "price": "189.00",
                        "priceCurrency": "USD",
                        "availability": "https://schema.org/InStock"
                    }
                },
                schema_types=["Product", "Offer"]
            )
        ],
        heading_tree=[HeadingItem(tag="h1", level=1, text="Solaris Ambient Floor Lamp", dom_index=0)],
        internal_links=[LinkItem(url="/lamps", anchor_text="View All Lighting", is_internal=True)]
    )
    ctx4 = CrawlContext(
        root_url="https://lumina-lighting.example/",
        domain="lumina-lighting.example",
        audited_at="2026-09-03T12:00:00Z",
        site_archetype=SiteArchetype.ECOMMERCE,
        robots_policy=RobotsPolicy(exists=True, url="https://lumina-lighting.example/robots.txt", raw_content="User-agent: *\nAllow: /"),
        sitemap_summary=SitemapSummary(exists=True, total_urls_in_sitemaps=10),
        pages=[p4]
    )
    fixtures["4_product_ecommerce_sale_pricing"] = {
        "id": 4,
        "name": "E-Commerce Product Page with Sale & Variant Prices (Negative Control)",
        "description": "Product page with sale price ($189) vs MSRP ($249) and variants. Must NOT trigger contradiction.",
        "archetype": SiteArchetype.ECOMMERCE,
        "context": ctx4,
        "target_url": "https://lumina-lighting.example/",
        "external_records": None,
        "expected_defects": 0,
        "expected_categories": [],
        "expected_root_cause_keywords": [],
        "forbidden_findings": ["contradiction", "inconsistency"]
    }

    # -------------------------------------------------------------------------
    # 5. B2B SaaS Service Site with Dead-End Pricing (Weak Engagement)
    # -------------------------------------------------------------------------
    p5 = PageEvidence(
        url="https://cloudsync-matrix.example/pricing",
        normalized_url="https://cloudsync-matrix.example/pricing",
        status_code=200,
        response_time_ms=32.0,
        content_type="text/html",
        page_archetype=PageArchetype.PRICING,
        is_primary_page=False,
        title="Enterprise Data Sync Pricing Tiers",
        meta_description="",
        canonical_url=None,
        meta_tags={},
        raw_html="""<!DOCTYPE html>
<html><head><title>Pricing Tiers</title></head>
<body>
  <h1>Enterprise Data Sync Pricing Tiers</h1>
  <h2>Tier 1: Starter ($99/mo)</h2>
  <p>Up to 10 nodes and 100GB synchronization.</p>
  <h2>Tier 2: Scale ($499/mo)</h2>
  <p>Unlimited nodes and real-time streaming.</p>
</body></html>""",
        raw_text="Enterprise Data Sync Pricing Tiers. Tier 1: Starter ($99/mo). Up to 10 nodes and 100GB synchronization. Tier 2: Scale ($499/mo). Unlimited nodes and real-time streaming.",
        raw_text_length=174,
        raw_word_count=26,
        heading_tree=[
            HeadingItem(tag="h1", level=1, text="Enterprise Data Sync Pricing Tiers", dom_index=0),
            HeadingItem(tag="h2", level=2, text="Tier 1: Starter ($99/mo)", dom_index=1),
            HeadingItem(tag="h2", level=2, text="Tier 2: Scale ($499/mo)", dom_index=2),
        ],
        internal_links=[]  # Zero internal links, no contact or signup form
    )
    ctx5 = CrawlContext(
        root_url="https://cloudsync-matrix.example/",
        domain="cloudsync-matrix.example",
        audited_at="2026-09-03T12:00:00Z",
        site_archetype=SiteArchetype.B2B_SAAS,
        robots_policy=RobotsPolicy(exists=True, url="https://cloudsync-matrix.example/robots.txt", raw_content="User-agent: *\nAllow: /"),
        sitemap_summary=SitemapSummary(exists=True, total_urls_in_sitemaps=5),
        pages=[p5]
    )
    fixtures["5_b2b_saas_pricing_deadend"] = {
        "id": 5,
        "name": "B2B SaaS Pricing Page Lacking Next-Step Pathway",
        "description": "B2B pricing page displaying paid tiers without any call-to-action link, trial button, or contact form.",
        "archetype": SiteArchetype.B2B_SAAS,
        "context": ctx5,
        "target_url": "https://cloudsync-matrix.example/",
        "external_records": None,
        "expected_defects": 1,
        "expected_categories": ["on_site_engagement"],
        "expected_root_cause_keywords": ["statically without interactive inquiry"],
        "forbidden_findings": []
    }

    # -------------------------------------------------------------------------
    # 6. Local/Professional Site Missing LocalBusiness Schema
    # -------------------------------------------------------------------------
    p6 = PageEvidence(
        url="https://summit-dental.example/",
        normalized_url="https://summit-dental.example/",
        status_code=200,
        response_time_ms=22.0,
        content_type="text/html",
        page_archetype=PageArchetype.HOMEPAGE,
        is_primary_page=True,
        title="Summit Family Dental Practice",
        meta_description="Comprehensive family dental care in Boulder, Colorado.",
        canonical_url=None,
        meta_tags={},
        raw_html="""<!DOCTYPE html>
<html><head><title>Summit Family Dental Practice</title></head>
<body>
  <h1>Summit Family Dental Practice</h1>
  <p>Dr. Eleanor Vance, DDS. Phone: (303) 555-0144.</p>
  <p>Address: 450 Alpine Way, Boulder, CO 80302.</p>
  <p>Office Hours: Monday - Friday 8:00 AM - 5:00 PM.</p>
  <a href="/appointment">Schedule Your Visit</a>
</body></html>""",
        raw_text="Summit Family Dental Practice. Dr. Eleanor Vance, DDS. Phone: (303) 555-0144. Address: 450 Alpine Way, Boulder, CO 80302. Office Hours: Monday - Friday 8:00 AM - 5:00 PM. Schedule Your Visit.",
        raw_text_length=196,
        raw_word_count=29,
        heading_tree=[HeadingItem(tag="h1", level=1, text="Summit Family Dental Practice", dom_index=0)],
        internal_links=[LinkItem(url="/appointment", anchor_text="Schedule Your Visit", is_internal=True)],
        json_ld=[]  # No LocalBusiness schema declared
    )
    ctx6 = CrawlContext(
        root_url="https://summit-dental.example/",
        domain="summit-dental.example",
        audited_at="2026-09-03T12:00:00Z",
        site_archetype=SiteArchetype.LOCAL_SERVICE,
        robots_policy=RobotsPolicy(exists=True, url="https://summit-dental.example/robots.txt", raw_content="User-agent: *\nAllow: /"),
        sitemap_summary=SitemapSummary(exists=False),
        pages=[p6]
    )
    fixtures["6_local_service_missing_schema"] = {
        "id": 6,
        "name": "Local Service Business Missing LocalBusiness Schema",
        "description": "Dental clinic with phone, address, and hours visible on homepage but lacking LocalBusiness JSON-LD.",
        "archetype": SiteArchetype.LOCAL_SERVICE,
        "context": ctx6,
        "target_url": "https://summit-dental.example/",
        "external_records": None,
        "expected_defects": 1,
        "expected_categories": ["structured_data"],
        "expected_root_cause_keywords": ["telephone", "operating hours"],
        "forbidden_findings": []
    }

    # -------------------------------------------------------------------------
    # 7. Publisher/Article Site Missing Article Schema
    # -------------------------------------------------------------------------
    p7 = PageEvidence(
        url="https://quantum-daily.example/posts/photon-breakthrough",
        normalized_url="https://quantum-daily.example/posts/photon-breakthrough",
        status_code=200,
        response_time_ms=35.0,
        content_type="text/html",
        page_archetype=PageArchetype.ARTICLE,
        is_primary_page=False,
        title="Physicists Achieve Coherent Optical Entanglement at Room Temperature",
        meta_description="A breakthrough experiment demonstrates room-temperature quantum memory.",
        canonical_url="https://quantum-daily.example/posts/photon-breakthrough",
        meta_tags={},
        raw_html="""<!DOCTYPE html>
<html><head><title>Photon Breakthrough</title></head>
<body>
  <h1>Physicists Achieve Coherent Optical Entanglement at Room Temperature</h1>
  <h2>By Dr. Marcus Chen — September 2, 2026</h2>
  <p>Researchers at the National Optical Institute have successfully demonstrated stable photon qubit storage.</p>
  <a href="/topics/quantum">More Quantum Physics Articles</a>
</body></html>""",
        raw_text="Physicists Achieve Coherent Optical Entanglement at Room Temperature. By Dr. Marcus Chen — September 2, 2026. Researchers at the National Optical Institute have successfully demonstrated stable photon qubit storage. More Quantum Physics Articles.",
        raw_text_length=249,
        raw_word_count=33,
        heading_tree=[
            HeadingItem(tag="h1", level=1, text="Physicists Achieve Coherent Optical Entanglement at Room Temperature", dom_index=0),
            HeadingItem(tag="h2", level=2, text="By Dr. Marcus Chen — September 2, 2026", dom_index=1)
        ],
        internal_links=[LinkItem(url="/topics/quantum", anchor_text="More Quantum Physics Articles", is_internal=True)],
        json_ld=[]  # Missing schema.org/Article markup
    )
    ctx7 = CrawlContext(
        root_url="https://quantum-daily.example/",
        domain="quantum-daily.example",
        audited_at="2026-09-03T12:00:00Z",
        site_archetype=SiteArchetype.PUBLISHER,
        robots_policy=RobotsPolicy(exists=True, url="https://quantum-daily.example/robots.txt", raw_content="User-agent: *\nAllow: /"),
        sitemap_summary=SitemapSummary(exists=True, total_urls_in_sitemaps=200),
        pages=[p7]
    )
    fixtures["7_publisher_missing_article_schema"] = {
        "id": 7,
        "name": "Publisher Article Lacking Article Structured Data",
        "description": "Editorial publication article with author byline and publication date but missing schema.org/Article.",
        "archetype": SiteArchetype.PUBLISHER,
        "context": ctx7,
        "target_url": "https://quantum-daily.example/",
        "external_records": None,
        "expected_defects": 1,
        "expected_categories": ["structured_data"],
        "expected_root_cause_keywords": ["Article", "template"],
        "forbidden_findings": []
    }

    # -------------------------------------------------------------------------
    # 8. Corporate/Institutional Site (Fully Compliant)
    # -------------------------------------------------------------------------
    p8 = PageEvidence(
        url="https://pacific-energy-institute.example/",
        normalized_url="https://pacific-energy-institute.example/",
        status_code=200,
        response_time_ms=20.0,
        content_type="text/html",
        page_archetype=PageArchetype.HOMEPAGE,
        is_primary_page=True,
        title="Pacific Energy Research Institute | Sustainable Grid Systems",
        meta_description="Advancing clean energy transitions through applied grid architecture research.",
        canonical_url="https://pacific-energy-institute.example/",
        meta_tags={},
        raw_html="""<!DOCTYPE html>
<html><head>
  <script type="application/ld+json">
  {
    "@context": "https://schema.org",
    "@type": "Organization",
    "name": "Pacific Energy Research Institute",
    "url": "https://pacific-energy-institute.example",
    "sameAs": ["https://en.wikipedia.org/wiki/Pacific_Energy_Institute"]
  }
  </script>
</head>
<body>
  <h1>Pacific Energy Research Institute</h1>
  <h2>Grid Modernization Initiatives</h2>
  <p>Accelerating decarbonization via power electronics and high-capacity battery systems.</p>
  <a href="/research">Explore Research Publications</a>
  <a href="/contact">Inquire for Collaboration</a>
</body></html>""",
        raw_text="Pacific Energy Research Institute. Grid Modernization Initiatives. Accelerating decarbonization via power electronics and high-capacity battery systems. Explore Research Publications. Inquire for Collaboration.",
        raw_text_length=215,
        raw_word_count=25,
        heading_tree=[
            HeadingItem(tag="h1", level=1, text="Pacific Energy Research Institute", dom_index=0),
            HeadingItem(tag="h2", level=2, text="Grid Modernization Initiatives", dom_index=1)
        ],
        internal_links=[
            LinkItem(url="/research", anchor_text="Explore Research Publications", is_internal=True),
            LinkItem(url="/contact", anchor_text="Inquire for Collaboration", is_internal=True)
        ],
        json_ld=[
            JsonLdBlock(
                raw_json='{"@context": "https://schema.org", "@type": "Organization", "name": "Pacific Energy Research Institute", "url": "https://pacific-energy-institute.example", "sameAs": ["https://en.wikipedia.org/wiki/Pacific_Energy_Institute"]}',
                parsed_data={
                    "@context": "https://schema.org",
                    "@type": "Organization",
                    "name": "Pacific Energy Research Institute",
                    "url": "https://pacific-energy-institute.example",
                    "sameAs": ["https://en.wikipedia.org/wiki/Pacific_Energy_Institute"]
                },
                schema_types=["Organization"]
            )
        ],
        extracted_dates={"copyright_year": "2026"}
    )
    ctx8 = CrawlContext(
        root_url="https://pacific-energy-institute.example/",
        domain="pacific-energy-institute.example",
        audited_at="2026-09-03T12:00:00Z",
        site_archetype=SiteArchetype.CORPORATE,
        robots_policy=RobotsPolicy(exists=True, url="https://pacific-energy-institute.example/robots.txt", raw_content="User-agent: *\nAllow: /"),
        sitemap_summary=SitemapSummary(exists=True, total_urls_in_sitemaps=12),
        pages=[p8]
    )
    fixtures["8_corporate_institutional_compliant"] = {
        "id": 8,
        "name": "Corporate/Institutional Compliant Site",
        "description": "Energy institute with Organization schema, sameAs, clean hierarchy, and next-step links.",
        "archetype": SiteArchetype.CORPORATE,
        "context": ctx8,
        "target_url": "https://pacific-energy-institute.example/",
        "external_records": None,
        "expected_defects": 0,
        "expected_categories": [],
        "expected_root_cause_keywords": [],
        "forbidden_findings": ["defect", "contradiction", "missing"]
    }

    # -------------------------------------------------------------------------
    # 9. Stale Temporal Signals (Expired Promotion)
    # -------------------------------------------------------------------------
    p9 = PageEvidence(
        url="https://valkyrie-gear.example/deals",
        normalized_url="https://valkyrie-gear.example/deals",
        status_code=200,
        response_time_ms=24.0,
        content_type="text/html",
        page_archetype=PageArchetype.HOMEPAGE,
        is_primary_page=True,
        title="Valkyrie Tactical Apparel Deals",
        meta_description="",
        canonical_url=None,
        meta_tags={},
        raw_html="""<!DOCTYPE html>
<html><head><title>Valkyrie Deals</title></head>
<body>
  <h1>Valkyrie Tactical Apparel Deals</h1>
  <div class="banner">Black Friday Special: Offer valid through November 30, 2022. Save 40% on all cold-weather gear.</div>
  <a href="/catalog">Shop Collection</a>
</body></html>""",
        raw_text="Valkyrie Tactical Apparel Deals. Black Friday Special: Offer valid through November 30, 2022. Save 40% on all cold-weather gear. Shop Collection.",
        raw_text_length=151,
        raw_word_count=23,
        heading_tree=[HeadingItem(tag="h1", level=1, text="Valkyrie Tactical Apparel Deals", dom_index=0)],
        internal_links=[LinkItem(url="/catalog", anchor_text="Shop Collection", is_internal=True)],
        extracted_dates={"copyright_year": "2026"}
    )
    ctx9 = CrawlContext(
        root_url="https://valkyrie-gear.example/",
        domain="valkyrie-gear.example",
        audited_at="2026-09-03T12:00:00Z",
        site_archetype=SiteArchetype.ECOMMERCE,
        robots_policy=RobotsPolicy(exists=True, url="https://valkyrie-gear.example/robots.txt", raw_content="User-agent: *\nAllow: /"),
        sitemap_summary=SitemapSummary(exists=False),
        pages=[p9]
    )
    fixtures["9_stale_temporal_expired_promotion"] = {
        "id": 9,
        "name": "Stale Temporal Signals (Expired Promotional Dates)",
        "description": "Active page displaying promotional banner claiming 'Offer valid through November 30, 2022'.",
        "archetype": SiteArchetype.ECOMMERCE,
        "context": ctx9,
        "target_url": "https://valkyrie-gear.example/",
        "external_records": None,
        "expected_defects": 1,
        "expected_categories": ["freshness_corroboration"],
        "expected_root_cause_keywords": ["promotional", "campaign"],
        "forbidden_findings": []
    }

    # -------------------------------------------------------------------------
    # 10. Conflicting First-Party Facts Across Pages (Phone Mismatch)
    # -------------------------------------------------------------------------
    p10_home = PageEvidence(
        url="https://apex-legal.example/",
        normalized_url="https://apex-legal.example/",
        status_code=200,
        response_time_ms=18.0,
        content_type="text/html",
        page_archetype=PageArchetype.HOMEPAGE,
        is_primary_page=True,
        title="Apex Corporate Legal Advisory",
        meta_description="",
        canonical_url=None,
        meta_tags={},
        raw_html="<h1>Apex Corporate Legal Advisory</h1><p>Call our client hotline: 800-555-0100</p><a href='/contact'>Contact Us</a>",
        raw_text="Apex Corporate Legal Advisory. Call our client hotline: 800-555-0100. Contact Us.",
        raw_text_length=82,
        raw_word_count=12,
        heading_tree=[HeadingItem(tag="h1", level=1, text="Apex Corporate Legal Advisory", dom_index=0)],
        internal_links=[LinkItem(url="/contact", anchor_text="Contact Us", is_internal=True)],
        json_ld=[
            JsonLdBlock(
                raw_json='{"@context": "https://schema.org", "@type": "LocalBusiness", "name": "Apex Corporate Legal Advisory", "telephone": "800-555-0100"}',
                parsed_data={"@type": "LocalBusiness", "name": "Apex Corporate Legal Advisory", "telephone": "800-555-0100"},
                schema_types=["LocalBusiness"]
            )
        ]
    )
    p10_contact = PageEvidence(
        url="https://apex-legal.example/contact",
        normalized_url="https://apex-legal.example/contact",
        status_code=200,
        response_time_ms=20.0,
        content_type="text/html",
        page_archetype=PageArchetype.CONTACT,
        is_primary_page=False,
        title="Contact Apex Legal Advisory",
        meta_description="",
        canonical_url=None,
        meta_tags={},
        raw_html="<h1>Contact Apex Legal Advisory</h1><p>Main Intake Phone: 800-555-0999</p><a href='/'>Return Home</a>",
        raw_text="Contact Apex Legal Advisory. Main Intake Phone: 800-555-0999. Return Home.",
        raw_text_length=76,
        raw_word_count=11,
        heading_tree=[HeadingItem(tag="h1", level=1, text="Contact Apex Legal Advisory", dom_index=0)],
        internal_links=[LinkItem(url="/", anchor_text="Return Home", is_internal=True)]
    )
    ctx10 = CrawlContext(
        root_url="https://apex-legal.example/",
        domain="apex-legal.example",
        audited_at="2026-09-03T12:00:00Z",
        site_archetype=SiteArchetype.LOCAL_SERVICE,
        robots_policy=RobotsPolicy(exists=True, url="https://apex-legal.example/robots.txt", raw_content="User-agent: *\nAllow: /"),
        sitemap_summary=SitemapSummary(exists=False),
        pages=[p10_home, p10_contact]
    )
    fixtures["10_conflicting_first_party_facts"] = {
        "id": 10,
        "name": "Conflicting First-Party Facts Across Pages",
        "description": "Homepage displays phone '800-555-0100', whereas Contact page displays phone '800-555-0999'.",
        "archetype": SiteArchetype.LOCAL_SERVICE,
        "context": ctx10,
        "target_url": "https://apex-legal.example/",
        "external_records": None,
        "expected_defects": 1,
        "expected_categories": ["freshness_corroboration"],
        "expected_root_cause_keywords": ["disparate", "unsynchronized", "contact"],
        "forbidden_findings": []
    }

    # -------------------------------------------------------------------------
    # 11. Authoritative External Contradiction
    # -------------------------------------------------------------------------
    p11 = PageEvidence(
        url="https://veritas-robotics.example/",
        normalized_url="https://veritas-robotics.example/",
        status_code=200,
        response_time_ms=25.0,
        content_type="text/html",
        page_archetype=PageArchetype.HOMEPAGE,
        is_primary_page=True,
        title="Veritas Robotics Corp | Autonomous Factory Systems",
        meta_description="",
        canonical_url=None,
        meta_tags={},
        raw_html="<h1>Veritas Robotics Corp</h1><p>Engineering autonomous micro-factories.</p><a href='/systems'>View Systems</a>",
        raw_text="Veritas Robotics Corp. Engineering autonomous micro-factories. View Systems.",
        raw_text_length=76,
        raw_word_count=10,
        heading_tree=[HeadingItem(tag="h1", level=1, text="Veritas Robotics Corp", dom_index=0)],
        internal_links=[LinkItem(url="/systems", anchor_text="View Systems", is_internal=True)],
        json_ld=[
            JsonLdBlock(
                raw_json='{"@context": "https://schema.org", "@type": "Organization", "name": "Veritas Robotics Corp", "sameAs": ["https://registry.example/veritas"]}',
                parsed_data={"@type": "Organization", "name": "Veritas Robotics Corp", "sameAs": ["https://registry.example/veritas"]},
                schema_types=["Organization"]
            )
        ]
    )
    ctx11 = CrawlContext(
        root_url="https://veritas-robotics.example/",
        domain="veritas-robotics.example",
        audited_at="2026-09-03T12:00:00Z",
        site_archetype=SiteArchetype.CORPORATE,
        robots_policy=RobotsPolicy(exists=True, url="https://veritas-robotics.example/robots.txt", raw_content="User-agent: *\nAllow: /"),
        sitemap_summary=SitemapSummary(exists=False),
        pages=[p11]
    )
    ext11 = [
        {
            "attribute": "organization_name",
            "source_name": "Delaware Department of State Business Registry",
            "source_type": "official_registry",
            "is_entity_relevant": True,
            "is_direct_statement": True,
            "external_value": "Veritas Automation International Inc"
        }
    ]
    fixtures["11_authoritative_external_contradiction"] = {
        "id": 11,
        "name": "Authoritative External Registry Contradiction",
        "description": "First-party website claims 'Veritas Robotics Corp', but official State Registry reports legal entity is 'Veritas Automation International Inc'.",
        "archetype": SiteArchetype.CORPORATE,
        "context": ctx11,
        "target_url": "https://veritas-robotics.example/",
        "external_records": ext11,
        "expected_defects": 1,
        "expected_categories": ["freshness_corroboration"],
        "expected_root_cause_keywords": ["verified external registries"],
        "forbidden_findings": []
    }

    # -------------------------------------------------------------------------
    # 12. Weak/Irrelevant External Source (Negative Control)
    # -------------------------------------------------------------------------
    p12 = PageEvidence(
        url="https://zenith-cloud.example/",
        normalized_url="https://zenith-cloud.example/",
        status_code=200,
        response_time_ms=19.0,
        content_type="text/html",
        page_archetype=PageArchetype.HOMEPAGE,
        is_primary_page=True,
        title="Zenith Cloud Platforms",
        meta_description="",
        canonical_url=None,
        meta_tags={},
        raw_html="<h1>Zenith Cloud Platforms</h1><p>Next-gen serverless orchestration.</p><a href='/contact'>Contact Us</a>",
        raw_text="Zenith Cloud Platforms. Next-gen serverless orchestration. Contact Us.",
        raw_text_length=71,
        raw_word_count=9,
        heading_tree=[HeadingItem(tag="h1", level=1, text="Zenith Cloud Platforms", dom_index=0)],
        internal_links=[LinkItem(url="/contact", anchor_text="Contact Us", is_internal=True)],
        json_ld=[
            JsonLdBlock(
                raw_json='{"@type": "Organization", "name": "Zenith Cloud Platforms", "sameAs": ["https://wikidata.org/wiki/Q11111"]}',
                parsed_data={"@type": "Organization", "name": "Zenith Cloud Platforms", "sameAs": ["https://wikidata.org/wiki/Q11111"]},
                schema_types=["Organization"]
            )
        ]
    )
    ctx12 = CrawlContext(
        root_url="https://zenith-cloud.example/",
        domain="zenith-cloud.example",
        audited_at="2026-09-03T12:00:00Z",
        site_archetype=SiteArchetype.B2B_SAAS,
        robots_policy=RobotsPolicy(exists=True, url="https://zenith-cloud.example/robots.txt", raw_content="User-agent: *\nAllow: /"),
        sitemap_summary=SitemapSummary(exists=False),
        pages=[p12]
    )
    ext12 = [
        {
            "attribute": "organization_name",
            "source_name": "Random Tech Blogspot Comment",
            "source_type": "unverified_blog",
            "is_entity_relevant": False,
            "is_direct_statement": False,
            "external_value": "Zenith Cloud Corp Ltd"
        }
    ]
    fixtures["12_weak_irrelevant_external_source"] = {
        "id": 12,
        "name": "Weak / Irrelevant External Source (Must NOT Create Finding)",
        "description": "Unverified blog comment claiming different corporate name. The 5-factor corroboration gate must discard it.",
        "archetype": SiteArchetype.B2B_SAAS,
        "context": ctx12,
        "target_url": "https://zenith-cloud.example/",
        "external_records": ext12,
        "expected_defects": 0,
        "expected_categories": [],
        "expected_root_cause_keywords": [],
        "forbidden_findings": ["contradiction", "discrepancy"]
    }

    # -------------------------------------------------------------------------
    # 13. Strong Engagement / Clear Next Steps (Compliant Control)
    # -------------------------------------------------------------------------
    p13 = PageEvidence(
        url="https://aegis-gear.example/boots/tactical-9",
        normalized_url="https://aegis-gear.example/boots/tactical-9",
        status_code=200,
        response_time_ms=22.0,
        content_type="text/html",
        page_archetype=PageArchetype.PRODUCT_DETAIL,
        is_primary_page=True,
        title="Aegis Tactical Waterproof Combat Boots",
        meta_description="All-weather tactical boots with Vibram outsoles.",
        canonical_url=None,
        meta_tags={},
        raw_html="""<!DOCTYPE html>
<html><head>
  <script type="application/ld+json">
  {"@type": "Product", "name": "Aegis Tactical Waterproof Combat Boots", "offers": {"@type": "Offer", "price": "149.00", "priceCurrency": "USD", "availability": "https://schema.org/InStock"}}
  </script>
</head>
<body>
  <h1>Aegis Tactical Waterproof Combat Boots</h1>
  <h2>Rugged Field Performance</h2>
  <p>Price: $149.00 USD. In Stock.</p>
  <button type="submit">Add to Cart</button>
  <a href="/catalog/socks">Pair with Merino Tactical Socks</a>
  <a href="/warranty">View 2-Year Field Warranty</a>
</body></html>""",
        raw_text="Aegis Tactical Waterproof Combat Boots. Rugged Field Performance. Price: $149.00 USD. In Stock. Add to Cart. Pair with Merino Tactical Socks. View 2-Year Field Warranty.",
        raw_text_length=174,
        raw_word_count=28,
        heading_tree=[
            HeadingItem(tag="h1", level=1, text="Aegis Tactical Waterproof Combat Boots", dom_index=0),
            HeadingItem(tag="h2", level=2, text="Rugged Field Performance", dom_index=1)
        ],
        internal_links=[
            LinkItem(url="/catalog/socks", anchor_text="Pair with Merino Tactical Socks", is_internal=True),
            LinkItem(url="/warranty", anchor_text="View 2-Year Field Warranty", is_internal=True)
        ],
        json_ld=[
            JsonLdBlock(
                raw_json='{"@type": "Product", "name": "Aegis Tactical Waterproof Combat Boots", "offers": {"@type": "Offer", "price": "149.00", "priceCurrency": "USD", "availability": "https://schema.org/InStock"}}',
                parsed_data={"@type": "Product", "name": "Aegis Tactical Waterproof Combat Boots", "offers": {"@type": "Offer", "price": "149.00", "priceCurrency": "USD", "availability": "https://schema.org/InStock"}},
                schema_types=["Product", "Offer"]
            )
        ]
    )
    ctx13 = CrawlContext(
        root_url="https://aegis-gear.example/",
        domain="aegis-gear.example",
        audited_at="2026-09-03T12:00:00Z",
        site_archetype=SiteArchetype.ECOMMERCE,
        robots_policy=RobotsPolicy(exists=True, url="https://aegis-gear.example/robots.txt", raw_content="User-agent: *\nAllow: /"),
        sitemap_summary=SitemapSummary(exists=False),
        pages=[p13]
    )
    fixtures["13_strong_engagement_clear_pathways"] = {
        "id": 13,
        "name": "Strong Engagement with Clear Purchasing & Navigation Pathways",
        "description": "Product page with clear H1, H2, 'Add to Cart' button, related product links, and warranty navigation.",
        "archetype": SiteArchetype.ECOMMERCE,
        "context": ctx13,
        "target_url": "https://aegis-gear.example/",
        "external_records": None,
        "expected_defects": 0,
        "expected_categories": [],
        "expected_root_cause_keywords": [],
        "forbidden_findings": ["dead-end", "pathway", "defect"]
    }

    # -------------------------------------------------------------------------
    # 14. Weak Engagement / Genuine Dead-End on Product Page
    # -------------------------------------------------------------------------
    p14 = PageEvidence(
        url="https://solaris-solar.example/panels/500w",
        normalized_url="https://solaris-solar.example/panels/500w",
        status_code=200,
        response_time_ms=25.0,
        content_type="text/html",
        page_archetype=PageArchetype.PRODUCT_DETAIL,
        is_primary_page=True,
        title="Solaris 500W Monocrystalline PV Panel",
        meta_description="",
        canonical_url=None,
        meta_tags={},
        raw_html="""<!DOCTYPE html>
<html><head>
  <script type="application/ld+json">
  {"@type": "Product", "name": "Solaris 500W Panel", "offers": {"@type": "Offer", "price": "299.00", "priceCurrency": "USD", "availability": "https://schema.org/InStock"}}
  </script>
</head>
<body>
  <h1>Solaris 500W Monocrystalline PV Panel</h1>
  <p>Technical specifications: 21.4% module efficiency with bifacial glass design.</p>
</body></html>""",
        raw_text="Solaris 500W Monocrystalline PV Panel. Technical specifications: 21.4% module efficiency with bifacial glass design.",
        raw_text_length=118,
        raw_word_count=15,
        heading_tree=[HeadingItem(tag="h1", level=1, text="Solaris 500W Monocrystalline PV Panel", dom_index=0)],
        internal_links=[],  # Zero internal links
        json_ld=[
            JsonLdBlock(
                raw_json='{"@type": "Product", "name": "Solaris 500W Panel", "offers": {"@type": "Offer", "price": "299.00", "priceCurrency": "USD", "availability": "https://schema.org/InStock"}}',
                parsed_data={"@type": "Product", "name": "Solaris 500W Panel", "offers": {"@type": "Offer", "price": "299.00", "priceCurrency": "USD", "availability": "https://schema.org/InStock"}},
                schema_types=["Product", "Offer"]
            )
        ]
    )
    ctx14 = CrawlContext(
        root_url="https://solaris-solar.example/",
        domain="solaris-solar.example",
        audited_at="2026-09-03T12:00:00Z",
        site_archetype=SiteArchetype.ECOMMERCE,
        robots_policy=RobotsPolicy(exists=True, url="https://solaris-solar.example/robots.txt", raw_content="User-agent: *\nAllow: /"),
        sitemap_summary=SitemapSummary(exists=False),
        pages=[p14]
    )
    fixtures["14_weak_engagement_product_deadend"] = {
        "id": 14,
        "name": "Weak Engagement / Genuine Dead-End on Product Page",
        "description": "Product page presenting description but terminating without any purchase CTA or internal catalog links.",
        "archetype": SiteArchetype.ECOMMERCE,
        "context": ctx14,
        "target_url": "https://solaris-solar.example/",
        "external_records": None,
        "expected_defects": 1,
        "expected_categories": ["on_site_engagement"],
        "expected_root_cause_keywords": ["terminates after product description", "purchasing controls"],
        "forbidden_findings": []
    }

    # -------------------------------------------------------------------------
    # 15. Same URL with Multiple Genuinely Distinct Problems
    # -------------------------------------------------------------------------
    p15 = PageEvidence(
        url="https://multi-fault-store.example/drone/x1",
        normalized_url="https://multi-fault-store.example/drone/x1",
        status_code=200,
        response_time_ms=40.0,
        content_type="text/html",
        page_archetype=PageArchetype.PRODUCT_DETAIL,
        is_primary_page=True,
        title="Stealth 4K Surveillance Drone",
        meta_description="",
        canonical_url=None,
        meta_tags={},
        raw_html="<div id='app'>Loading Drone Specifications...</div>",
        raw_text="Loading Drone Specifications...",
        raw_text_length=31,
        raw_word_count=3,
        rendered_dom="""<h1>Stealth 4K Surveillance Drone</h1>
<p>Price: $1,299.00 USD. Availability: In Stock.</p>
<p>Endurance: 42 minutes flight time.</p>""",
        rendered_text="Stealth 4K Surveillance Drone. Price: $1,299.00 USD. Availability: In Stock. Endurance: 42 minutes flight time.",
        missing_facts_in_raw=["$1,299.00 USD", "In Stock", "42 minutes flight time"],
        heading_tree=[HeadingItem(tag="h1", level=1, text="Stealth 4K Surveillance Drone", dom_index=0)],
        internal_links=[],  # Dead-end (Engagement defect)
        json_ld=[]  # Missing Product/Offer schema with commercial facts present (Structured data defect)
    )
    ctx15 = CrawlContext(
        root_url="https://multi-fault-store.example/",
        domain="multi-fault-store.example",
        audited_at="2026-09-03T12:00:00Z",
        site_archetype=SiteArchetype.ECOMMERCE,
        robots_policy=RobotsPolicy(exists=True, url="https://multi-fault-store.example/robots.txt", raw_content="User-agent: *\nAllow: /"),
        sitemap_summary=SitemapSummary(exists=False),
        pages=[p15]
    )
    fixtures["15_same_url_multiple_distinct_problems"] = {
        "id": 15,
        "name": "Same URL with Multiple Genuinely Distinct Problems",
        "description": "Single URL having CSR missing facts, missing Product/Offer schema, and dead-end navigation. All 3 must be preserved.",
        "archetype": SiteArchetype.ECOMMERCE,
        "context": ctx15,
        "target_url": "https://multi-fault-store.example/",
        "external_records": None,
        "expected_defects": 3,
        "expected_categories": ["machine_readability", "structured_data", "on_site_engagement"],
        "expected_root_cause_keywords": ["hydration", "Commercial attributes are embedded only", "terminates after product description"],
        "forbidden_findings": []
    }

    # -------------------------------------------------------------------------
    # 16. Same Underlying Problem Reported by Multiple Passes (Deduplication Test)
    # -------------------------------------------------------------------------
    fixtures["16_same_problem_cross_skill_dedup"] = {
        "id": 16,
        "name": "Same Underlying Problem Reported Repeatedly (Cross-Skill Deduplication)",
        "description": "Identical issue reported across skills/passes with different wording. Must merge to 1 and combine evidence.",
        "archetype": SiteArchetype.CORPORATE,
        "context": None,
        "target_url": "https://dedup-test.example/",
        "external_records": None,
        "expected_defects": 1,
        "expected_categories": ["structured_data"],
        "expected_root_cause_keywords": ["syntax"],
        "forbidden_findings": []
    }

    # -------------------------------------------------------------------------
    # 17. Invalid / Unreachable Target URL (Graceful Degradation)
    # -------------------------------------------------------------------------
    fixtures["17_invalid_unreachable_target"] = {
        "id": 17,
        "name": "Invalid / Unreachable Target URL",
        "description": "Malformed URL string ('not_a_valid_url_scheme'). Must degrade gracefully without raising unhandled exceptions.",
        "archetype": SiteArchetype.UNKNOWN,
        "context": None,
        "target_url": "invalid://not-a-valid-http-domain-string-$$$",
        "external_records": None,
        "expected_defects": 0,
        "expected_categories": [],
        "expected_root_cause_keywords": [],
        "forbidden_findings": []
    }

    # -------------------------------------------------------------------------
    # 18. No-Findings Healthy Target with Complete Negative Controls (Unseen Archetype)
    # -------------------------------------------------------------------------
    p18_home = PageEvidence(
        url="https://vanguard-studios.example/",
        normalized_url="https://vanguard-studios.example/",
        status_code=200,
        response_time_ms=21.0,
        content_type="text/html",
        page_archetype=PageArchetype.HOMEPAGE,
        is_primary_page=True,
        title="Vanguard Studios | Architectural Visualization & Motion Design",
        meta_description="Award-winning 3D spatial design and architectural rendering.",
        canonical_url="https://vanguard-studios.example/",
        meta_tags={},
        raw_html="""<!DOCTYPE html>
<html><head>
  <script type="application/ld+json">
  {
    "@context": "https://schema.org",
    "@type": "Organization",
    "name": "Vanguard Studios",
    "url": "https://vanguard-studios.example",
    "sameAs": ["https://www.behance.net/vanguardstudios"]
  }
  </script>
</head>
<body>
  <h1>Vanguard Studios — Spatial CGI</h1>
  <h3>Recent Architectural Commissions</h3>
  <p>Crafting photorealistic environments for international design firms.</p>
  <a href="/work">View Selected Works</a>
  <a href="/legal/privacy">Privacy Policy</a>
</body></html>""",
        raw_text="Vanguard Studios — Spatial CGI. Recent Architectural Commissions. Crafting photorealistic environments for international design firms. View Selected Works. Privacy Policy.",
        raw_text_length=174,
        raw_word_count=21,
        heading_tree=[
            HeadingItem(tag="h1", level=1, text="Vanguard Studios — Spatial CGI", dom_index=0),
            HeadingItem(tag="h3", level=3, text="Recent Architectural Commissions", dom_index=1),
        ],
        internal_links=[
            LinkItem(url="/work", anchor_text="View Selected Works", is_internal=True),
            LinkItem(url="/legal/privacy", anchor_text="Privacy Policy", is_internal=True),
        ],
        json_ld=[
            JsonLdBlock(
                raw_json='{"@context": "https://schema.org", "@type": "Organization", "name": "Vanguard Studios", "url": "https://vanguard-studios.example", "sameAs": ["https://www.behance.net/vanguardstudios"]}',
                parsed_data={
                    "@context": "https://schema.org",
                    "@type": "Organization",
                    "name": "Vanguard Studios",
                    "url": "https://vanguard-studios.example",
                    "sameAs": ["https://www.behance.net/vanguardstudios"]
                },
                schema_types=["Organization"]
            )
        ],
        extracted_dates={"copyright_year": "2026"}
    )
    p18_legal = PageEvidence(
        url="https://vanguard-studios.example/legal/privacy",
        normalized_url="https://vanguard-studios.example/legal/privacy",
        status_code=200,
        response_time_ms=18.0,
        content_type="text/html",
        page_archetype=PageArchetype.LEGAL,
        is_primary_page=False,
        title="Privacy Policy | Vanguard Studios",
        meta_description="Data protection and privacy notice.",
        canonical_url=None,
        meta_tags={},
        raw_html="<h1>Privacy Policy</h1><p>We do not track visitors or sell personal data. Effective September 2026.</p>",
        raw_text="Privacy Policy. We do not track visitors or sell personal data. Effective September 2026.",
        raw_text_length=89,
        raw_word_count=13,
        heading_tree=[HeadingItem(tag="h1", level=1, text="Privacy Policy", dom_index=0)],
        internal_links=[]  # Legal page with zero CTAs -> Must NOT flag dead-end!
    )
    ctx18 = CrawlContext(
        root_url="https://vanguard-studios.example/",
        domain="vanguard-studios.example",
        audited_at="2026-09-03T12:00:00Z",
        site_archetype=SiteArchetype.PORTFOLIO,
        robots_policy=RobotsPolicy(
            exists=True,
            url="https://vanguard-studios.example/robots.txt",
            raw_content="User-agent: *\nAllow: /\nDisallow: /internal/",
            bot_rules={"*": BotRule(user_agent="*", allowed_paths=["/"], disallowed_paths=["/internal/"])}
        ),
        sitemap_summary=SitemapSummary(exists=False, error="Sitemap not found"),  # Missing sitemap is NOT a defect
        pages=[p18_home, p18_legal]
    )
    fixtures["18_no_findings_healthy_negative_controls"] = {
        "id": 18,
        "name": "Healthy Unseen Portfolio with Complete Negative Controls",
        "description": "Portfolio site with missing sitemap, minor heading gap, legal page without CTA, and harmless JS. Must produce 0 defects.",
        "archetype": SiteArchetype.PORTFOLIO,
        "context": ctx18,
        "target_url": "https://vanguard-studios.example/",
        "external_records": None,
        "expected_defects": 0,
        "expected_categories": [],
        "expected_root_cause_keywords": [],
        "forbidden_findings": ["defect", "contradiction", "missing", "dead-end"]
    }

    return fixtures
