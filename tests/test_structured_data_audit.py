"""
Test Suite: Structured Data & Entity Audit Skill (Refined)
Tests JSON-LD syntax errors, visible-to-schema factual reconciliation (sale prices, variants, ranges),
objective grounding-risk language, and contextual missing schema rules.
"""

import os
import sys
import unittest
import importlib.util

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

# Load validate_schema module via importlib
_skill_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "skills", "structured-data-entity-audit", "scripts", "validate_schema.py"))
_spec = importlib.util.spec_from_file_location("validate_schema", _skill_path)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)
validate_structured_data = _mod.validate_structured_data


class TestStructuredDataEntityAudit(unittest.TestCase):

    def test_json_ld_syntax_error_detection(self):
        bad_json_block = JsonLdBlock(
            raw_json='{"@context": "https://schema.org", "@type": "Product", "name": "Broken",}',
            parsed_data=None,
            schema_types=[],
            has_syntax_error=True,
            error_message="Expecting property name enclosed in double quotes: line 1 column 61"
        )
        page = PageEvidence(
            url="https://example.com/product/broken",
            normalized_url="https://example.com/product/broken",
            status_code=200,
            response_time_ms=25.0,
            content_type="text/html",
            page_archetype=PageArchetype.PRODUCT_DETAIL,
            is_primary_page=True,
            title="Broken Product",
            meta_description="",
            canonical_url=None,
            meta_tags={},
            raw_html="",
            raw_text="Broken Product Price $50",
            raw_text_length=24,
            raw_word_count=4,
            json_ld=[bad_json_block]
        )
        ctx = CrawlContext(
            root_url="https://example.com",
            domain="example.com",
            audited_at="2026-09-02T12:00:00Z",
            site_archetype=SiteArchetype.ECOMMERCE,
            robots_policy=RobotsPolicy(exists=False, url="", raw_content=""),
            sitemap_summary=SitemapSummary(exists=False),
            pages=[page]
        )
        findings = validate_structured_data(ctx)
        syntax_finding = next((f for f in findings if "Invalid JSON-LD syntax" in f["title"]), None)
        self.assertIsNotNone(syntax_finding)
        self.assertEqual(syntax_finding["severity"], "high")
        # Check that unsupported outcome claims are NOT present
        self.assertNotIn("Google, Bing, Perplexity", syntax_finding["impact"])

    def test_genuine_fact_contradiction_detection(self):
        # Schema says Price: $10.00, Visible DOM text clearly states $59.99 with no sale/variant context
        contradictory_json = JsonLdBlock(
            raw_json='{"@type": "Product", "offers": {"@type": "Offer", "price": "10.00", "priceCurrency": "USD", "availability": "https://schema.org/OutOfStock"}}',
            parsed_data={
                "@type": "Product",
                "name": "Camera",
                "offers": {
                    "@type": "Offer",
                    "price": "10.00",
                    "priceCurrency": "USD",
                    "availability": "https://schema.org/OutOfStock"
                }
            },
            schema_types=["Product", "Offer"]
        )
        page = PageEvidence(
            url="https://example.com/product/camera",
            normalized_url="https://example.com/product/camera",
            status_code=200,
            response_time_ms=20.0,
            content_type="text/html",
            page_archetype=PageArchetype.PRODUCT_DETAIL,
            is_primary_page=True,
            title="Camera",
            meta_description="",
            canonical_url=None,
            meta_tags={},
            raw_html="",
            raw_text="Camera Price: $59.99 USD. Status: In Stock.",
            raw_text_length=42,
            raw_word_count=7,
            json_ld=[contradictory_json]
        )
        ctx = CrawlContext(
            root_url="https://example.com",
            domain="example.com",
            audited_at="2026-09-02T12:00:00Z",
            site_archetype=SiteArchetype.ECOMMERCE,
            robots_policy=RobotsPolicy(exists=False, url="", raw_content=""),
            sitemap_summary=SitemapSummary(exists=False),
            pages=[page]
        )
        findings = validate_structured_data(ctx)
        
        # Must detect Price inconsistency
        price_finding = next((f for f in findings if "price" in f["title"].lower()), None)
        self.assertIsNotNone(price_finding)
        self.assertEqual(price_finding["severity"], "high")
        self.assertIn("10.00", price_finding["evidence"])
        self.assertIn("59.99", price_finding["evidence"])
        # Check that unsupported penalty claims are NOT present
        self.assertNotIn("penalize", price_finding["impact"].lower())
        self.assertNotIn("hallucinate", price_finding["impact"].lower())

    def test_sale_price_and_original_price_no_false_contradiction(self):
        # Visible copy: "Was $149.00, Now Sale Price: $99.00". Schema declares $99.00.
        sale_json = JsonLdBlock(
            raw_json='{"@type": "Product", "offers": {"@type": "Offer", "price": "99.00", "priceCurrency": "USD"}}',
            parsed_data={"@type": "Product", "offers": {"@type": "Offer", "price": "99.00", "priceCurrency": "USD"}},
            schema_types=["Product", "Offer"]
        )
        page = PageEvidence(
            url="https://example.com/product/sale-item",
            normalized_url="https://example.com/product/sale-item",
            status_code=200,
            response_time_ms=20.0,
            content_type="text/html",
            page_archetype=PageArchetype.PRODUCT_DETAIL,
            is_primary_page=True,
            title="Sale Headphones",
            meta_description="",
            canonical_url=None,
            meta_tags={},
            raw_html="",
            raw_text="Sale Headphones. Was $149.00 regular price. Special Sale: $99.00. Save $50 today!",
            raw_text_length=80,
            raw_word_count=13,
            json_ld=[sale_json]
        )
        ctx = CrawlContext(
            root_url="https://example.com",
            domain="example.com",
            audited_at="2026-09-02T12:00:00Z",
            site_archetype=SiteArchetype.ECOMMERCE,
            robots_policy=RobotsPolicy(exists=False, url="", raw_content=""),
            sitemap_summary=SitemapSummary(exists=False),
            pages=[page]
        )
        findings = validate_structured_data(ctx)
        # Should NOT produce any price contradiction finding
        price_findings = [f for f in findings if "price" in f["title"].lower()]
        self.assertEqual(len(price_findings), 0, "Sale vs original price presence should not trigger a false contradiction.")

    def test_variant_prices_no_false_contradiction(self):
        # Visible copy lists multiple variants: "64GB: $599.00 | 128GB: $699.00 | 256GB: $799.00". Schema declares starting price $599.00.
        variant_json = JsonLdBlock(
            raw_json='{"@type": "Product", "offers": {"@type": "Offer", "price": "599.00", "priceCurrency": "USD"}}',
            parsed_data={"@type": "Product", "offers": {"@type": "Offer", "price": "599.00", "priceCurrency": "USD"}},
            schema_types=["Product", "Offer"]
        )
        page = PageEvidence(
            url="https://example.com/product/phone",
            normalized_url="https://example.com/product/phone",
            status_code=200,
            response_time_ms=20.0,
            content_type="text/html",
            page_archetype=PageArchetype.PRODUCT_DETAIL,
            is_primary_page=True,
            title="Smartphone Pro",
            meta_description="",
            canonical_url=None,
            meta_tags={},
            raw_html="",
            raw_text="Smartphone Pro Options: 64GB model $599.00, 128GB model $699.00, 256GB model $799.00. Starting at $599.00.",
            raw_text_length=110,
            raw_word_count=16,
            json_ld=[variant_json]
        )
        ctx = CrawlContext(
            root_url="https://example.com",
            domain="example.com",
            audited_at="2026-09-02T12:00:00Z",
            site_archetype=SiteArchetype.ECOMMERCE,
            robots_policy=RobotsPolicy(exists=False, url="", raw_content=""),
            sitemap_summary=SitemapSummary(exists=False),
            pages=[page]
        )
        findings = validate_structured_data(ctx)
        price_findings = [f for f in findings if "price" in f["title"].lower()]
        self.assertEqual(len(price_findings), 0, "Multi-variant prices matching schema should not trigger a false contradiction.")

    def test_contextual_missing_schema_with_commercial_signals(self):
        # 1. Product page with explicit visible commercial attributes ($499, Add to Cart) missing schema -> MUST Flag
        commercial_page = PageEvidence(
            url="https://example.com/product/camera",
            normalized_url="https://example.com/product/camera",
            status_code=200,
            response_time_ms=20.0,
            content_type="text/html",
            page_archetype=PageArchetype.PRODUCT_DETAIL,
            is_primary_page=True,
            title="Camera",
            meta_description="",
            canonical_url=None,
            meta_tags={},
            raw_html="<h1>Camera</h1><p>Price: $499.00</p><button>Add to Cart</button>",
            raw_text="Camera Price: $499.00 Add to Cart In Stock",
            raw_text_length=43,
            raw_word_count=8,
            json_ld=[]
        )
        ctx_comm = CrawlContext(
            root_url="https://example.com",
            domain="example.com",
            audited_at="2026-09-02T12:00:00Z",
            site_archetype=SiteArchetype.ECOMMERCE,
            robots_policy=RobotsPolicy(exists=False, url="", raw_content=""),
            sitemap_summary=SitemapSummary(exists=False),
            pages=[commercial_page]
        )
        findings = validate_structured_data(ctx_comm)
        self.assertTrue(any("Visible commercial product facts lack structured" in f["title"] for f in findings))

        # 2. Informational page without commercial facts or transaction -> MUST NOT flag missing Product schema
        info_page = PageEvidence(
            url="https://example.com/product/overview",
            normalized_url="https://example.com/product/overview",
            status_code=200,
            response_time_ms=20.0,
            content_type="text/html",
            page_archetype=PageArchetype.PRODUCT_DETAIL,
            is_primary_page=False,
            title="Technology Architecture",
            meta_description="",
            canonical_url=None,
            meta_tags={},
            raw_html="<h1>Architecture</h1><p>Our underlying optical design methodology.</p>",
            raw_text="Architecture Our underlying optical design methodology.",
            raw_text_length=56,
            raw_word_count=7,
            json_ld=[]
        )
        ctx_info = CrawlContext(
            root_url="https://example.com",
            domain="example.com",
            audited_at="2026-09-02T12:00:00Z",
            site_archetype=SiteArchetype.ECOMMERCE,
            robots_policy=RobotsPolicy(exists=False, url="", raw_content=""),
            sitemap_summary=SitemapSummary(exists=False),
            pages=[info_page]
        )
        findings_info = validate_structured_data(ctx_info)
        self.assertFalse(any("Visible commercial product facts lack" in f["title"] for f in findings_info))


if __name__ == "__main__":
    unittest.main()
