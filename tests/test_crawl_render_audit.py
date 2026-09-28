"""
Test Suite: Crawl & Render Audit Skill
Tests granular bot directives, CSR fact omissions vs harmless JS, non-text traps,
false positive controls, and causal chain finding structure.
"""

import unittest
from core.models import (
    CrawlContext,
    PageEvidence,
    RobotsPolicy,
    BotRule,
    SitemapSummary,
    SiteArchetype,
    PageArchetype,
    ImageItem
)
from core.diff_analyzer import analyze_raw_vs_rendered_dom
import os
import sys
import importlib.util

# Load inspect_crawler from skills/crawl-render-audit/scripts/inspect_crawler.py
_skill_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "skills", "crawl-render-audit", "scripts", "inspect_crawler.py"))
_spec = importlib.util.spec_from_file_location("inspect_crawler", _skill_path)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)
inspect_crawl_and_render = _mod.inspect_crawl_and_render


class TestCrawlRenderAuditSkill(unittest.TestCase):

    def test_robots_directive_granularity_and_false_positives(self):
        # 1. Test standard safe admin disallows -> MUST NOT produce findings (False Positive Control)
        safe_policy = RobotsPolicy(
            exists=True,
            url="https://example.com/robots.txt",
            raw_content="User-agent: *\nDisallow: /admin/\nDisallow: /cart/\nDisallow: /checkout/",
            bot_rules={
                "*": BotRule(user_agent="*", disallowed_paths=["/admin/", "/cart/", "/checkout/"])
            }
        )
        ctx_safe = CrawlContext(
            root_url="https://example.com",
            domain="example.com",
            audited_at="2026-09-02T12:00:00Z",
            site_archetype=SiteArchetype.ECOMMERCE,
            robots_policy=safe_policy,
            sitemap_summary=SitemapSummary(exists=True),
            pages=[]
        )
        findings_safe = inspect_crawl_and_render(ctx_safe)
        self.assertEqual(len(findings_safe), 0, "Standard safe private paths in robots.txt should not trigger findings.")

        # 2. Test specific AI bot blockades -> MUST produce bot-specific finding
        ai_block_policy = RobotsPolicy(
            exists=True,
            url="https://example.com/robots.txt",
            raw_content="User-agent: PerplexityBot\nDisallow: /\nUser-agent: GPTBot\nDisallow: /",
            bot_rules={
                "PerplexityBot": BotRule(user_agent="PerplexityBot", disallowed_paths=["/"], is_fully_blocked=True),
                "GPTBot": BotRule(user_agent="GPTBot", disallowed_paths=["/"], is_fully_blocked=True)
            }
        )
        ctx_ai = CrawlContext(
            root_url="https://example.com",
            domain="example.com",
            audited_at="2026-09-02T12:00:00Z",
            site_archetype=SiteArchetype.ECOMMERCE,
            robots_policy=ai_block_policy,
            sitemap_summary=SitemapSummary(exists=True),
            pages=[]
        )
        findings_ai = inspect_crawl_and_render(ctx_ai)
        self.assertEqual(len(findings_ai), 2)
        
        # Verify PerplexityBot finding
        perp_finding = next(f for f in findings_ai if "PerplexityBot" in f["title"])
        self.assertEqual(perp_finding["severity"], "high")
        self.assertIn("real-time conversational search", perp_finding["impact"].lower())
        self.assertIn("observation", perp_finding)  # Causal chain keys
        self.assertIn("evidence", perp_finding)
        self.assertIn("root_cause", perp_finding)
        self.assertIn("suggested_action", perp_finding)

        # Verify GPTBot finding
        gpt_finding = next(f for f in findings_ai if "GPTBot" in f["title"])
        self.assertEqual(gpt_finding["severity"], "medium")
        self.assertIn("pre-training", gpt_finding["impact"].lower())

    def test_csr_diff_analyzer_factual_omissions(self):
        # Case 1: Raw HTML is empty shell, Rendered DOM has price and stock -> True Positive
        raw_html = "<!DOCTYPE html><html><head><title>Camera</title></head><body><div id='root'></div></body></html>"
        rendered_dom = "<!DOCTYPE html><html><body><h1>Apex Camera</h1><p>Price: $3,999.00 USD</p><p>Status: In Stock</p><p>SKU: SKU-8891</p></body></html>"
        raw_text = "Camera"
        rendered_text = "Apex Camera Price: $3,999.00 USD Status: In Stock SKU: SKU-8891"

        missing_facts, ratio, is_meaningful = analyze_raw_vs_rendered_dom(
            raw_html, rendered_dom, raw_text, rendered_text
        )
        self.assertTrue(is_meaningful)
        self.assertTrue(any("$3,999.00" in f or "USD" in f for f in missing_facts))
        self.assertTrue(any("In Stock" in f for f in missing_facts))

        # Case 2: Raw HTML contains all facts, Rendered DOM adds decorative tracking script -> False Positive Control (True Negative)
        raw_html_full = "<!DOCTYPE html><html><body><h1>Apex Camera</h1><p>Price: $3,999.00 USD</p><p>Status: In Stock</p></body></html>"
        rendered_dom_extra = "<!DOCTYPE html><html><body><h1>Apex Camera</h1><p>Price: $3,999.00 USD</p><p>Status: In Stock</p><div class='chat-widget'>Chat with us</div></body></html>"
        raw_text_full = "Apex Camera Price: $3,999.00 USD Status: In Stock"
        rendered_text_extra = "Apex Camera Price: $3,999.00 USD Status: In Stock Chat with us"

        missing_facts_clean, _, is_meaningful_clean = analyze_raw_vs_rendered_dom(
            raw_html_full, rendered_dom_extra, raw_text_full, rendered_text_extra
        )
        self.assertFalse(is_meaningful_clean, "Harmless chat widget should not be flagged as missing factual content.")
        self.assertEqual(len(missing_facts_clean), 0)

    def test_csr_findings_generation_and_causal_chain(self):
        page_csr = PageEvidence(
            url="https://example.com/product/pro-camera",
            normalized_url="https://example.com/product/pro-camera",
            status_code=200,
            response_time_ms=40.0,
            content_type="text/html",
            page_archetype=PageArchetype.PRODUCT_DETAIL,
            is_primary_page=True,
            title="Pro Camera",
            meta_description="",
            canonical_url=None,
            meta_tags={},
            raw_html="<div id='root'></div>",
            raw_text="Loading...",
            raw_text_length=10,
            raw_word_count=1,
            rendered_dom="<h1>Pro Camera</h1><p>$3,999.00 USD</p><p>In Stock</p>",
            rendered_text="Pro Camera $3,999.00 USD In Stock",
            required_rendering_trigger=True,
            missing_facts_in_raw=["$3,999.00 USD", "In Stock"]
        )

        ctx = CrawlContext(
            root_url="https://example.com",
            domain="example.com",
            audited_at="2026-09-02T12:00:00Z",
            site_archetype=SiteArchetype.ECOMMERCE,
            robots_policy=RobotsPolicy(exists=False, url="", raw_content=""),
            sitemap_summary=SitemapSummary(exists=False),
            pages=[page_csr]
        )

        findings = inspect_crawl_and_render(ctx)
        self.assertEqual(len(findings), 1)
        f = findings[0]
        self.assertEqual(f["category"], "machine_readability")
        self.assertEqual(f["severity"], "high")
        self.assertEqual(f["confidence"], "high")
        self.assertIn("$3,999.00 USD", f["evidence"])
        self.assertIn("In Stock", f["evidence"])
        self.assertIn("Server-Side Rendering", f["suggested_action"]["summary"])

    def test_non_text_image_traps(self):
        page_img = PageEvidence(
            url="https://example.com/pricing",
            normalized_url="https://example.com/pricing",
            status_code=200,
            response_time_ms=30.0,
            content_type="text/html",
            page_archetype=PageArchetype.PRICING,
            is_primary_page=True,
            title="Pricing",
            meta_description="",
            canonical_url=None,
            meta_tags={},
            raw_html="",
            raw_text="Our Pricing",
            raw_text_length=11,
            raw_word_count=2,
            images=[
                ImageItem(src="/pricing-matrix.png", alt="", has_alt=False, is_content_relevant=True, context_keyword="pricing"),
                ImageItem(src="/icon.svg", alt="", has_alt=False, is_content_relevant=False, context_keyword=None)
            ]
        )

        ctx = CrawlContext(
            root_url="https://example.com",
            domain="example.com",
            audited_at="2026-09-02T12:00:00Z",
            site_archetype=SiteArchetype.B2B_SAAS,
            robots_policy=RobotsPolicy(exists=False, url="", raw_content=""),
            sitemap_summary=SitemapSummary(exists=False),
            pages=[page_img]
        )

        findings = inspect_crawl_and_render(ctx)
        self.assertEqual(len(findings), 1)
        self.assertIn("locked in image", findings[0]["title"])
        self.assertIn("/pricing-matrix.png", findings[0]["evidence"])


if __name__ == "__main__":
    unittest.main()
