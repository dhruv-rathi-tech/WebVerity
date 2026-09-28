"""
Test Suite: Cross-Page & Cross-Representation Factual Contradiction Detection.
Validates deterministic extraction, cross-page factual consistency reconciliation,
and false-positive control across all required test cases and fixtures.
"""

import os
import sys
import unittest
from typing import Optional, List
from urllib.parse import urlparse

# Ensure workspace root in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.models import (
    CrawlContext,
    PageEvidence,
    RobotsPolicy,
    SitemapSummary,
    SiteArchetype,
    PageArchetype,
    JsonLdBlock
)
from core.freshness_analyzer import analyze_cross_page_consistency
import importlib.util

_orchestrator_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "skills", "audit-orchestrator", "scripts", "orchestrate.py"))
_spec = importlib.util.spec_from_file_location("orchestrate", _orchestrator_path)
_orchestrate_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_orchestrate_mod)
AuditOrchestrator = _orchestrate_mod.AuditOrchestrator


def make_page(
    url: str,
    raw_text: str,
    title: str = "Test Page",
    page_archetype: PageArchetype = PageArchetype.OTHER,
    is_primary_page: bool = False,
    json_ld: Optional[List[JsonLdBlock]] = None
) -> PageEvidence:
    return PageEvidence(
        url=url,
        normalized_url=url,
        status_code=200,
        response_time_ms=25.0,
        content_type="text/html",
        page_archetype=page_archetype,
        is_primary_page=is_primary_page,
        title=title,
        meta_description="",
        canonical_url=None,
        meta_tags={},
        raw_html=f"<html><head><title>{title}</title></head><body>{raw_text}</body></html>",
        raw_text=raw_text,
        raw_text_length=len(raw_text),
        raw_word_count=len(raw_text.split()),
        json_ld=json_ld or []
    )


def make_context(
    root_url: str,
    pages: List[PageEvidence],
    site_archetype: SiteArchetype = SiteArchetype.B2B_SAAS,
    domain: Optional[str] = None
) -> CrawlContext:
    parsed = urlparse(root_url)
    dom = domain or parsed.netloc or "example.com"
    return CrawlContext(
        root_url=root_url,
        domain=dom,
        audited_at="2026-09-06T12:00:00Z",
        site_archetype=site_archetype,
        robots_policy=RobotsPolicy(
            exists=True,
            url=f"{root_url.rstrip('/')}/robots.txt",
            raw_content="User-agent: *\nAllow: /"
        ),
        sitemap_summary=SitemapSummary(exists=True, total_urls_in_sitemaps=len(pages)),
        pages=pages
    )


class TestCrossPageFactualContradictions(unittest.TestCase):

    def setUp(self):
        self.orchestrator = AuditOrchestrator()

    # -------------------------------------------------------------------------
    # Test 1: Same price across homepage/pricing/FAQ -> no finding
    # -------------------------------------------------------------------------
    def test_01_same_price_across_pages_no_finding(self):
        p_home = make_page(
            url="https://saas-example.com/",
            raw_text="Welcome to TaskFlow. Pro Plan is only $39/mo with full collaboration features.",
            title="TaskFlow - Modern Project Management",
            is_primary_page=True,
            page_archetype=PageArchetype.HOMEPAGE
        )
        p_pricing = make_page(
            url="https://saas-example.com/pricing",
            raw_text="Pricing Tiers: Pro Plan is $39/month. Includes unlimited projects and users.",
            title="TaskFlow Pricing",
            page_archetype=PageArchetype.PRICING
        )
        p_faq = make_page(
            url="https://saas-example.com/faq",
            raw_text="Frequently Asked Questions. How much does Pro Plan cost? The Pro Plan is $39/month.",
            title="TaskFlow FAQ",
            page_archetype=PageArchetype.FAQ
        )
        ctx = make_context("https://saas-example.com/", [p_home, p_pricing, p_faq])
        conflicts = analyze_cross_page_consistency(ctx)
        self.assertEqual(len(conflicts), 0, "Consistent pricing across pages should produce 0 contradictions.")

    # -------------------------------------------------------------------------
    # Test 2: Same product, different price across pages -> contradiction
    # -------------------------------------------------------------------------
    def test_02_same_product_different_price_across_pages_contradiction(self):
        p_home = make_page(
            url="https://saas-example.com/",
            raw_text="TaskFlow Pro Plan is only $39/mo for modern teams.",
            title="TaskFlow Homepage",
            is_primary_page=True,
            page_archetype=PageArchetype.HOMEPAGE
        )
        p_pricing = make_page(
            url="https://saas-example.com/pricing",
            raw_text="Pricing Plans: Pro Plan is $49/month with enterprise security.",
            title="TaskFlow Pricing",
            page_archetype=PageArchetype.PRICING
        )
        p_faq = make_page(
            url="https://saas-example.com/faq",
            raw_text="FAQ: Pro Plan is $39/month for unlimited workspaces.",
            title="TaskFlow FAQ",
            page_archetype=PageArchetype.FAQ
        )
        ctx = make_context("https://saas-example.com/", [p_home, p_pricing, p_faq])
        conflicts = analyze_cross_page_consistency(ctx)
        self.assertEqual(len(conflicts), 1, "Conflicting prices for Pro Plan must emit 1 contradiction finding.")
        c = conflicts[0]
        self.assertEqual(c["entity_name"].lower(), "pro plan")
        self.assertEqual(c["attribute"], "monthly_price")
        self.assertIn("https://saas-example.com/", c["urls"])
        self.assertIn("https://saas-example.com/pricing", c["urls"])
        self.assertIn("https://saas-example.com/faq", c["urls"])
        self.assertIn("$39.00", c["evidence_text"])
        self.assertIn("$49.00", c["evidence_text"])

    # -------------------------------------------------------------------------
    # Test 3: Sale vs MSRP -> no finding
    # -------------------------------------------------------------------------
    def test_03_sale_vs_msrp_no_finding(self):
        p_prod = make_page(
            url="https://shop.example.com/product/chair",
            page_archetype=PageArchetype.PRODUCT_DETAIL,
            title="ErgoComfort Office Chair",
            raw_text="ErgoComfort Office Chair. Sale Price: $799.00 USD (Original Price: $999.00 MSRP — Save $200). Status: In Stock."
        )
        ctx = make_context("https://shop.example.com/", [p_prod], SiteArchetype.ECOMMERCE)
        conflicts = analyze_cross_page_consistency(ctx)
        self.assertEqual(len(conflicts), 0, "Sale price ($799) vs MSRP ($999) must NOT trigger a contradiction.")

    # -------------------------------------------------------------------------
    # Test 4: Introductory vs standard price -> no finding
    # -------------------------------------------------------------------------
    def test_04_introductory_vs_standard_price_no_finding(self):
        p_sub = make_page(
            url="https://saas.example.com/pricing",
            page_archetype=PageArchetype.PRICING,
            title="SaaS Plans & Pricing",
            raw_text="Standard Plan: Introductory price $29.00 for the first month, then $49.00 per month standard rate."
        )
        ctx = make_context("https://saas.example.com/", [p_sub])
        conflicts = analyze_cross_page_consistency(ctx)
        self.assertEqual(len(conflicts), 0, "Introductory price vs standard price must NOT trigger a contradiction.")

    # -------------------------------------------------------------------------
    # Test 5: Different product variants -> no finding
    # -------------------------------------------------------------------------
    def test_05_different_product_variants_no_finding(self):
        p_prod = make_page(
            url="https://store.example.com/product/headphones",
            page_archetype=PageArchetype.PRODUCT_DETAIL,
            title="AcousticPro Wireless Headphones",
            raw_text="AcousticPro Wireless Headphones. Available Options: Standard Model $199.00 | Noise-Canceling Model $249.00."
        )
        ctx = make_context("https://store.example.com/", [p_prod], SiteArchetype.ECOMMERCE)
        conflicts = analyze_cross_page_consistency(ctx)
        self.assertEqual(len(conflicts), 0, "Different product variants on product page must NOT trigger contradiction.")

    # -------------------------------------------------------------------------
    # Test 6: Different products with different prices -> no finding
    # -------------------------------------------------------------------------
    def test_06_different_products_different_prices_no_finding(self):
        p_prod_a = make_page(
            url="https://store.example.com/product/monitor-27",
            page_archetype=PageArchetype.PRODUCT_DETAIL,
            title="UltraVision 27-inch 4K Monitor",
            raw_text="UltraVision 27-inch 4K Monitor. Price: $399.00. In Stock."
        )
        p_prod_b = make_page(
            url="https://store.example.com/product/monitor-34",
            page_archetype=PageArchetype.PRODUCT_DETAIL,
            title="UltraVision 34-inch Curved Display",
            raw_text="UltraVision 34-inch Curved Display. Price: $799.00. In Stock."
        )
        ctx = make_context("https://store.example.com/", [p_prod_a, p_prod_b], SiteArchetype.ECOMMERCE)
        conflicts = analyze_cross_page_consistency(ctx)
        self.assertEqual(len(conflicts), 0, "Different products with different prices must NEVER trigger a contradiction.")

    # -------------------------------------------------------------------------
    # Test 7: Same phone number with formatting differences -> no finding
    # -------------------------------------------------------------------------
    def test_07_same_phone_formatting_differences_no_finding(self):
        p_home = make_page(
            url="https://service.example.com/",
            raw_text="Contact our support center anytime at (800) 555-0199.",
            title="Apex Services",
            is_primary_page=True
        )
        p_contact = make_page(
            url="https://service.example.com/contact",
            page_archetype=PageArchetype.CONTACT,
            raw_text="Reach us directly at +1-800-555-0199 or visit our office.",
            title="Contact Apex Services"
        )
        ctx = make_context("https://service.example.com/", [p_home, p_contact], SiteArchetype.LOCAL_SERVICE)
        conflicts = analyze_cross_page_consistency(ctx)
        self.assertEqual(len(conflicts), 0, "Phone number with formatting differences must normalize and produce 0 contradictions.")

    # -------------------------------------------------------------------------
    # Test 8: Different phone numbers across first-party pages -> contradiction
    # -------------------------------------------------------------------------
    def test_08_different_phone_numbers_contradiction(self):
        p_home = make_page(
            url="https://service.example.com/",
            raw_text="Call our main headquarters at 800-555-0100.",
            title="Apex Legal Homepage",
            is_primary_page=True
        )
        p_contact = make_page(
            url="https://service.example.com/contact",
            page_archetype=PageArchetype.CONTACT,
            raw_text="Official direct telephone line: 800-555-0999.",
            title="Contact Apex Legal"
        )
        ctx = make_context("https://service.example.com/", [p_home, p_contact], SiteArchetype.LOCAL_SERVICE)
        conflicts = analyze_cross_page_consistency(ctx)
        self.assertEqual(len(conflicts), 1, "Different primary phone numbers across pages must emit a contradiction.")
        c = conflicts[0]
        self.assertEqual(c["attribute"], "phone_number")
        self.assertIn("800-555-0100", c["evidence_text"])
        self.assertIn("800-555-0999", c["evidence_text"])

    # -------------------------------------------------------------------------
    # Test 9: Visible price vs JSON-LD price -> contradiction
    # -------------------------------------------------------------------------
    def test_09_visible_price_vs_json_ld_price_contradiction(self):
        p_prod = make_page(
            url="https://store.example.com/product/laptop",
            page_archetype=PageArchetype.PRODUCT_DETAIL,
            title="Zenith Pro 16 Laptop",
            raw_text="Zenith Pro 16 Laptop. Current Price: $1,299.00 USD. Order now for next day delivery.",
            json_ld=[
                JsonLdBlock(
                    raw_json='{"@context": "https://schema.org", "@type": "Product", "name": "Zenith Pro 16 Laptop", "offers": {"@type": "Offer", "price": "1499.00", "priceCurrency": "USD"}}',
                    parsed_data={
                        "@context": "https://schema.org",
                        "@type": "Product",
                        "name": "Zenith Pro 16 Laptop",
                        "offers": {
                            "@type": "Offer",
                            "price": "1499.00",
                            "priceCurrency": "USD"
                        }
                    },
                    schema_types=["Product", "Offer"]
                )
            ]
        )
        ctx = make_context("https://store.example.com/", [p_prod], SiteArchetype.ECOMMERCE)
        conflicts = analyze_cross_page_consistency(ctx)
        self.assertEqual(len(conflicts), 1, "Visible price $1,299 vs JSON-LD price $1499 must emit a contradiction.")
        c = conflicts[0]
        self.assertEqual(c["attribute"], "product_price")
        self.assertIn("1299.00", c["evidence_text"])
        self.assertIn("1499.00", c["evidence_text"])

    # -------------------------------------------------------------------------
    # Test 10: Visible price with missing JSON-LD price -> no contradiction
    # -------------------------------------------------------------------------
    def test_10_visible_price_missing_json_ld_no_contradiction(self):
        p_prod = make_page(
            url="https://store.example.com/product/mouse",
            page_archetype=PageArchetype.PRODUCT_DETAIL,
            title="ErgoGrip Wireless Mouse",
            raw_text="ErgoGrip Wireless Mouse. Price: $49.00 USD. In Stock.",
            json_ld=[
                JsonLdBlock(
                    raw_json='{"@context": "https://schema.org", "@type": "Product", "name": "ErgoGrip Wireless Mouse"}',
                    parsed_data={
                        "@context": "https://schema.org",
                        "@type": "Product",
                        "name": "ErgoGrip Wireless Mouse"
                    },
                    schema_types=["Product"]
                )
            ]
        )
        ctx = make_context("https://store.example.com/", [p_prod], SiteArchetype.ECOMMERCE)
        conflicts = analyze_cross_page_consistency(ctx)
        self.assertEqual(len(conflicts), 0, "Missing JSON-LD price must NOT automatically become a contradiction.")

    # -------------------------------------------------------------------------
    # Test 11: Different currencies -> no contradiction
    # -------------------------------------------------------------------------
    def test_11_different_currencies_no_contradiction(self):
        p_us = make_page(
            url="https://global.example.com/us/pro",
            raw_text="GlobalPro Plan is $39.00 per month in North America.",
            title="GlobalPro US"
        )
        p_eu = make_page(
            url="https://global.example.com/eu/pro",
            raw_text="GlobalPro Plan is €35.00 per month in Europe.",
            title="GlobalPro EU"
        )
        ctx = make_context("https://global.example.com/", [p_us, p_eu])
        conflicts = analyze_cross_page_consistency(ctx)
        self.assertEqual(len(conflicts), 0, "Different currencies represent legitimate localized pricing and must NOT contradict.")

    # -------------------------------------------------------------------------
    # Test 12: Explicit historical price -> no contradiction
    # -------------------------------------------------------------------------
    def test_12_explicit_historical_price_no_contradiction(self):
        p_pricing = make_page(
            url="https://saas.example.com/pricing",
            page_archetype=PageArchetype.PRICING,
            title="Pricing History and Active Plans",
            raw_text="CloudSync Pro Plan. Previously in 2022 our Pro Plan was $29.00/mo, currently the active Pro Plan is $39.00/month."
        )
        ctx = make_context("https://saas.example.com/", [p_pricing])
        conflicts = analyze_cross_page_consistency(ctx)
        self.assertEqual(len(conflicts), 0, "Explicit historical pricing statements must NOT contradict current active pricing.")

    # -------------------------------------------------------------------------
    # Test 13: Systemic repeated contradiction across several pages consolidated
    # -------------------------------------------------------------------------
    def test_13_systemic_repeated_contradiction_consolidated(self):
        # 4 different pages declare conflicting pricing for the same Acme Pro Plan
        p1 = make_page(
            url="https://example.com/",
            title="Acme Homepage",
            raw_text="Acme Pro Plan is $39/mo."
        )
        p2 = make_page(
            url="https://example.com/features",
            title="Acme Features",
            raw_text="Get Acme Pro Plan for $39/mo."
        )
        p3 = make_page(
            url="https://example.com/pricing",
            title="Acme Pricing",
            raw_text="Acme Pro Plan is $49/mo."
        )
        p4 = make_page(
            url="https://example.com/faq",
            title="Acme FAQ",
            raw_text="How much is Acme Pro Plan? $39/mo."
        )
        ctx = make_context("https://example.com/", [p1, p2, p3, p4])
        conflicts = analyze_cross_page_consistency(ctx)
        self.assertEqual(len(conflicts), 1, "Repeated cross-page contradiction should consolidate into 1 finding.")
        c = conflicts[0]
        self.assertEqual(len(c["urls"]), 4, "All 4 affected URLs must be retained in the consolidated finding.")
        self.assertIn("https://example.com/", c["urls"])
        self.assertIn("https://example.com/pricing", c["urls"])
        self.assertIn("https://example.com/features", c["urls"])
        self.assertIn("https://example.com/faq", c["urls"])

    # -------------------------------------------------------------------------
    # Test 14: End-to-End Fixture A (SaaS Pricing Inconsistency)
    # -------------------------------------------------------------------------
    def test_14_e2e_fixture_a_saas_pricing_inconsistency(self):
        p_home = make_page(
            url="https://cloudmatrix.example/",
            title="CloudMatrix Cloud Infrastructure",
            raw_text="Scale your apps with CloudMatrix. Enterprise Plan is $199/mo with 24/7 SLA.",
            page_archetype=PageArchetype.HOMEPAGE,
            is_primary_page=True
        )
        p_pricing = make_page(
            url="https://cloudmatrix.example/pricing",
            title="CloudMatrix Pricing",
            raw_text="Transparent CloudMatrix Pricing. Enterprise Plan is $249/mo billed monthly.",
            page_archetype=PageArchetype.PRICING
        )
        p_faq = make_page(
            url="https://cloudmatrix.example/faq",
            title="CloudMatrix FAQ",
            raw_text="FAQ: How much does Enterprise Plan cost? The Enterprise Plan is $199/mo.",
            page_archetype=PageArchetype.FAQ
        )
        ctx = make_context("https://cloudmatrix.example/", [p_home, p_pricing, p_faq], SiteArchetype.B2B_SAAS)
        report = self.orchestrator.run(target_url=ctx.root_url, existing_context=ctx)
        contradiction_findings = [
            f for f in report["findings"]
            if "contradiction" in f["title"].lower() or "contradiction" in f["observation"].lower()
        ]
        self.assertEqual(len(contradiction_findings), 1)
        f = contradiction_findings[0]
        self.assertEqual(f["severity"], "high")
        self.assertEqual(f["category"], "freshness_corroboration")
        self.assertIn("https://cloudmatrix.example/pricing", f["affected_urls"])
        self.assertIn("https://cloudmatrix.example/", f["affected_urls"])
        self.assertIn("199.00", f["evidence"])
        self.assertIn("249.00", f["evidence"])

    # -------------------------------------------------------------------------
    # Test 15: End-to-End Fixture B (E-commerce JSON-LD vs Visible Price Mismatch)
    # -------------------------------------------------------------------------
    def test_15_e2e_fixture_b_ecommerce_jsonld_visible_mismatch(self):
        p_prod = make_page(
            url="https://gearshop.example/product/smart-watch",
            page_archetype=PageArchetype.PRODUCT_DETAIL,
            title="AeroPulse Smart Watch",
            raw_text="AeroPulse Smart Watch. Current retail price: $299.00 USD. Free shipping on all orders.",
            json_ld=[
                JsonLdBlock(
                    raw_json='{"@context": "https://schema.org", "@type": "Product", "name": "AeroPulse Smart Watch", "offers": {"@type": "Offer", "price": "349.00", "priceCurrency": "USD"}}',
                    parsed_data={
                        "@context": "https://schema.org",
                        "@type": "Product",
                        "name": "AeroPulse Smart Watch",
                        "offers": {
                            "@type": "Offer",
                            "price": "349.00",
                            "priceCurrency": "USD"
                        }
                    },
                    schema_types=["Product", "Offer"]
                )
            ]
        )
        ctx = make_context("https://gearshop.example/", [p_prod], SiteArchetype.ECOMMERCE)
        report = self.orchestrator.run(target_url=ctx.root_url, existing_context=ctx)
        contradiction_findings = [
            f for f in report["findings"]
            if "contradiction" in f["title"].lower() or "factual contradiction" in f["observation"].lower()
        ]
        self.assertEqual(len(contradiction_findings), 1)
        f = contradiction_findings[0]
        self.assertIn("299.00", f["evidence"])
        self.assertIn("349.00", f["evidence"])

    # -------------------------------------------------------------------------
    # Test 16: End-to-End Fixture C (Local Service Phone Contradiction)
    # -------------------------------------------------------------------------
    def test_16_e2e_fixture_c_local_service_phone_contradiction(self):
        p_home = make_page(
            url="https://city-plumbing.example/",
            title="City Plumbing 24/7",
            raw_text="Call City Plumbing day or night: 800-555-1234.",
            page_archetype=PageArchetype.HOMEPAGE,
            is_primary_page=True
        )
        p_contact = make_page(
            url="https://city-plumbing.example/contact",
            title="Contact City Plumbing",
            raw_text="Our central dispatch phone line: 800-555-9876.",
            page_archetype=PageArchetype.CONTACT
        )
        ctx = make_context("https://city-plumbing.example/", [p_home, p_contact], SiteArchetype.LOCAL_SERVICE)
        report = self.orchestrator.run(target_url=ctx.root_url, existing_context=ctx)
        phone_findings = [
            f for f in report["findings"]
            if "phone" in f["title"].lower() or "phone" in f["observation"].lower()
        ]
        self.assertEqual(len(phone_findings), 1)
        f = phone_findings[0]
        self.assertEqual(f["severity"], "high")
        self.assertIn("800-555-1234", f["evidence"])
        self.assertIn("800-555-9876", f["evidence"])

    # -------------------------------------------------------------------------
    # Test 17: End-to-End Fixture D (Legitimate Pricing Variations E2E)
    # -------------------------------------------------------------------------
    def test_17_e2e_fixture_d_legitimate_pricing_variation_e2e(self):
        p_prod = make_page(
            url="https://gearshop.example/product/jacket",
            page_archetype=PageArchetype.PRODUCT_DETAIL,
            title="All-Weather Expedition Jacket",
            raw_text="All-Weather Expedition Jacket. Sale Price: $149.00 USD (Original Price: $199.00 MSRP). Sizes S/M/L.",
            json_ld=[
                JsonLdBlock(
                    raw_json='{"@context": "https://schema.org", "@type": "Product", "name": "All-Weather Expedition Jacket", "offers": {"@type": "Offer", "price": "149.00", "priceCurrency": "USD"}}',
                    parsed_data={
                        "@context": "https://schema.org",
                        "@type": "Product",
                        "name": "All-Weather Expedition Jacket",
                        "offers": {
                            "@type": "Offer",
                            "price": "149.00",
                            "priceCurrency": "USD"
                        }
                    },
                    schema_types=["Product", "Offer"]
                )
            ]
        )
        ctx = make_context("https://gearshop.example/", [p_prod], SiteArchetype.ECOMMERCE)
        report = self.orchestrator.run(target_url=ctx.root_url, existing_context=ctx)
        contradiction_findings = [
            f for f in report["findings"]
            if "contradiction" in f["title"].lower() or "factual contradiction" in f["observation"].lower()
        ]
        self.assertEqual(len(contradiction_findings), 0, "Legitimate Sale vs MSRP with matching JSON-LD must produce 0 contradiction findings.")

    # -------------------------------------------------------------------------
    # Test 18: End-to-End Fixture E (Repeated Template Inconsistency)
    # -------------------------------------------------------------------------
    def test_18_e2e_fixture_e_repeated_template_mismatch_e2e(self):
        p_a = make_page(
            url="https://shop.example/prod/widget-a",
            page_archetype=PageArchetype.PRODUCT_DETAIL,
            title="Widget Alpha",
            raw_text="Widget Alpha. Price: $100.00 USD.",
            json_ld=[
                JsonLdBlock(
                    raw_json='{"@context": "https://schema.org", "@type": "Product", "name": "Widget Alpha", "offers": {"@type": "Offer", "price": "120.00", "priceCurrency": "USD"}}',
                    parsed_data={"@context": "https://schema.org", "@type": "Product", "name": "Widget Alpha", "offers": {"@type": "Offer", "price": "120.00", "priceCurrency": "USD"}},
                    schema_types=["Product", "Offer"]
                )
            ]
        )
        p_b = make_page(
            url="https://shop.example/prod/widget-b",
            page_archetype=PageArchetype.PRODUCT_DETAIL,
            title="Widget Beta",
            raw_text="Widget Beta. Price: $200.00 USD.",
            json_ld=[
                JsonLdBlock(
                    raw_json='{"@context": "https://schema.org", "@type": "Product", "name": "Widget Beta", "offers": {"@type": "Offer", "price": "220.00", "priceCurrency": "USD"}}',
                    parsed_data={"@context": "https://schema.org", "@type": "Product", "name": "Widget Beta", "offers": {"@type": "Offer", "price": "220.00", "priceCurrency": "USD"}},
                    schema_types=["Product", "Offer"]
                )
            ]
        )
        ctx = make_context("https://shop.example/", [p_a, p_b], SiteArchetype.ECOMMERCE)
        report = self.orchestrator.run(target_url=ctx.root_url, existing_context=ctx)
        contradiction_findings = [
            f for f in report["findings"]
            if "contradiction" in f["title"].lower() or "factual contradiction" in f["observation"].lower()
        ]
        self.assertEqual(len(contradiction_findings), 2, "Distinct products must produce separate contradiction findings.")
        entities_found = {f["observation"] for f in contradiction_findings}
        self.assertTrue(any("Widget Alpha" in obs for obs in entities_found))
        self.assertTrue(any("Widget Beta" in obs for obs in entities_found))

    # -------------------------------------------------------------------------
    # Test 19: Adversarial - Historical Article with Old Price -> No finding
    # -------------------------------------------------------------------------
    def test_19_adversarial_historical_article_old_price_no_finding(self):
        p_pricing = make_page(
            url="https://saas.example/pricing",
            title="CloudMatrix Pricing",
            raw_text="CloudMatrix Active Plans. Pro Plan is $49/mo.",
            page_archetype=PageArchetype.PRICING
        )
        p_blog = make_page(
            url="https://saas.example/blog/announcement-v1",
            title="CloudMatrix Launch Announcement (2020)",
            raw_text="In our initial 2020 launch announcement, the Pro Plan was $19/mo.",
            page_archetype=PageArchetype.ARTICLE
        )
        ctx = make_context("https://saas.example/", [p_pricing, p_blog])
        conflicts = analyze_cross_page_consistency(ctx)
        self.assertEqual(len(conflicts), 0, "Historical editorial articles with old launch prices must NOT contradict active pricing.")

    # -------------------------------------------------------------------------
    # Test 20: Adversarial - Regional / Localized Pricing -> No finding
    # -------------------------------------------------------------------------
    def test_20_adversarial_regional_pricing_no_finding(self):
        p_us = make_page(
            url="https://global.example/us/pricing",
            title="Global Services US",
            raw_text="United States Pricing: Pro Plan is $49/mo.",
            page_archetype=PageArchetype.PRICING
        )
        p_ca = make_page(
            url="https://global.example/ca/pricing",
            title="Global Services Canada",
            raw_text="Canada Regional Pricing: Pro Plan is $59/mo.",
            page_archetype=PageArchetype.PRICING
        )
        ctx = make_context("https://global.example/", [p_us, p_ca])
        conflicts = analyze_cross_page_consistency(ctx)
        self.assertEqual(len(conflicts), 0, "Explicit regional URL paths (/us/ vs /ca/) represent legitimate regional pricing and must NOT contradict.")

    # -------------------------------------------------------------------------
    # Test 21: Adversarial - Monthly vs Annual Commitment Billing -> No finding
    # -------------------------------------------------------------------------
    def test_21_adversarial_monthly_vs_annual_commitment_no_finding(self):
        p_pricing = make_page(
            url="https://saas.example/pricing",
            title="Subscription Options",
            raw_text="Pro Plan is $39/mo billed annually. Or pay $49/mo billed monthly.",
            page_archetype=PageArchetype.PRICING
        )
        ctx = make_context("https://saas.example/", [p_pricing])
        conflicts = analyze_cross_page_consistency(ctx)
        self.assertEqual(len(conflicts), 0, "Annual commitment billing discount vs monthly rate must NOT trigger a false contradiction.")

    # -------------------------------------------------------------------------
    # Test 22: Adversarial - Customer-Segment Pricing -> No finding
    # -------------------------------------------------------------------------
    def test_22_adversarial_customer_segment_pricing_no_finding(self):
        p_home = make_page(
            url="https://saas.example/",
            title="Platform Overview",
            raw_text="Pro Plan is $49/mo for commercial teams.",
            page_archetype=PageArchetype.HOMEPAGE
        )
        p_edu = make_page(
            url="https://saas.example/education",
            title="Education Discount",
            raw_text="Academic Offer: Pro Plan for Students is $19/mo with verified student email.",
            page_archetype=PageArchetype.OTHER
        )
        ctx = make_context("https://saas.example/", [p_home, p_edu])
        conflicts = analyze_cross_page_consistency(ctx)
        self.assertEqual(len(conflicts), 0, "Customer-segmented pricing (e.g. Students, Non-profit) must NOT contradict standard commercial pricing.")

    # -------------------------------------------------------------------------
    # Test 23: Adversarial - Temporary Campaign Language -> No finding
    # -------------------------------------------------------------------------
    def test_23_adversarial_temporary_campaign_no_finding(self):
        p_pricing = make_page(
            url="https://saas.example/pricing",
            title="Pricing",
            raw_text="Standard rate: Pro Plan is $49/mo.",
            page_archetype=PageArchetype.PRICING
        )
        p_promo = make_page(
            url="https://saas.example/promo",
            title="Black Friday Sale",
            raw_text="Black Friday Limited Time Special: Pro Plan is $29/mo.",
            page_archetype=PageArchetype.OTHER
        )
        ctx = make_context("https://saas.example/", [p_pricing, p_promo])
        conflicts = analyze_cross_page_consistency(ctx)
        self.assertEqual(len(conflicts), 0, "Temporary campaign promotions (Black Friday, Flash Sale) must NOT contradict standard active pricing.")

    # -------------------------------------------------------------------------
    # Test 24: Adversarial - Role-Specific Phone Numbers -> No finding
    # -------------------------------------------------------------------------
    def test_24_adversarial_role_specific_phones_no_finding(self):
        p_contact = make_page(
            url="https://company.example/contact",
            title="Contact Directory",
            raw_text="Get in touch. Direct Sales Department: 800-111-1111. Customer Support & Help Desk: 800-222-2222. Billing Office: 800-333-3333.",
            page_archetype=PageArchetype.CONTACT
        )
        ctx = make_context("https://company.example/", [p_contact], SiteArchetype.CORPORATE)
        conflicts = analyze_cross_page_consistency(ctx)
        self.assertEqual(len(conflicts), 0, "Role-specific phone numbers (Sales vs Support vs Billing) must NOT contradict each other.")

    # -------------------------------------------------------------------------
    # Test 25: Adversarial - Similar Compound Plan Names -> No finding
    # -------------------------------------------------------------------------
    def test_25_adversarial_similar_compound_plan_names_no_finding(self):
        p_home = make_page(
            url="https://saas.example/",
            title="Homepage",
            raw_text="Pro Plan is $39/mo.",
            page_archetype=PageArchetype.HOMEPAGE
        )
        p_pricing = make_page(
            url="https://saas.example/pricing",
            title="Pricing",
            raw_text="Our Tiers: Pro Plan is $39/mo. Upgrade to Pro Plus Plan for $59/mo.",
            page_archetype=PageArchetype.PRICING
        )
        ctx = make_context("https://saas.example/", [p_home, p_pricing])
        conflicts = analyze_cross_page_consistency(ctx)
        self.assertEqual(len(conflicts), 0, "'Pro Plan' ($39) and 'Pro Plus Plan' ($59) are distinct tiers and must NOT contradict.")

    # -------------------------------------------------------------------------
    # Test 26: True End-to-End JSON and Markdown Report Integration
    # -------------------------------------------------------------------------
    def test_26_end_to_end_json_and_markdown_report_integration(self):
        p_home = make_page(
            url="https://verify-e2e.example/",
            title="Acme Cloud Platform",
            raw_text="Welcome to Acme. Pro Plan is $39/mo with full features.",
            page_archetype=PageArchetype.HOMEPAGE,
            is_primary_page=True
        )
        p_pricing = make_page(
            url="https://verify-e2e.example/pricing",
            title="Acme Cloud Pricing",
            raw_text="Acme Pricing: Pro Plan is $49/mo.",
            page_archetype=PageArchetype.PRICING
        )
        ctx = make_context("https://verify-e2e.example/", [p_home, p_pricing], SiteArchetype.B2B_SAAS)
        
        # 1. Run through actual Orchestrator
        report = self.orchestrator.run(target_url=ctx.root_url, existing_context=ctx)
        self.assertIn("findings", report)
        
        # 2. Verify contradiction finding in JSON
        contradictions = [f for f in report["findings"] if "contradiction" in f["title"].lower() or "contradiction" in f["observation"].lower()]
        self.assertEqual(len(contradictions), 1, "Must synthesize 1 confirmed contradiction in report JSON.")
        
        f = contradictions[0]
        # Check all required evidence-first fields per Section 7 & 14
        self.assertIn("Entity: Pro Plan", f["evidence"])
        self.assertIn("Attribute: Monthly Price", f["evidence"])
        self.assertIn("https://verify-e2e.example/", f["affected_urls"])
        self.assertIn("https://verify-e2e.example/pricing", f["affected_urls"])
        self.assertEqual(f["severity"], "high")
        self.assertEqual(f["confidence"], "high")
        self.assertTrue(f["root_cause"])
        self.assertTrue(f["impact"])
        self.assertTrue(f["suggested_action"]["summary"])
        
        # 3. Format as Markdown using actual Markdown formatter
        render_markdown = _orchestrate_mod.render_markdown_report
        md_output = render_markdown(report)
        
        # 4. Verify Markdown structure contains complete contradiction block
        self.assertIn("## Audit Findings", md_output)
        self.assertIn("Internal cross-page factual contradiction", md_output)
        self.assertIn("Entity: Pro Plan", md_output)
        self.assertIn("Attribute: Monthly Price", md_output)
        self.assertIn("- **Root Cause:**", md_output)
        self.assertIn("- **Impact:**", md_output)
        self.assertIn("- **Suggested Action", md_output)


if __name__ == "__main__":
    unittest.main()
