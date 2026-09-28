"""
Test Suite: On-Site Engagement Audit Skill
Tests visitor orientation, semantic heading hierarchies, context-sensitive next-step pathways,
and false-positive controls for legitimate terminal and informational pages.
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
    HeadingItem,
    LinkItem
)

# Load inspect_engagement module via importlib
_skill_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "skills", "engagement-audit", "scripts", "inspect_engagement.py"))
_spec = importlib.util.spec_from_file_location("inspect_engagement", _skill_path)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)
inspect_engagement = _mod.inspect_engagement


class TestEngagementAuditSkill(unittest.TestCase):

    def test_well_structured_product_page_no_defects(self):
        # Well-structured product page with clear H1, H2s, Add to Cart CTA, and related links
        page = PageEvidence(
            url="https://example.com/product/camera",
            normalized_url="https://example.com/product/camera",
            status_code=200,
            response_time_ms=25.0,
            content_type="text/html",
            page_archetype=PageArchetype.PRODUCT_DETAIL,
            is_primary_page=True,
            title="Apex 8K Pro Camera",
            meta_description="Flagship cinema sensor.",
            canonical_url=None,
            meta_tags={},
            raw_html="<h1>Apex 8K Pro Camera</h1><h2>Specifications</h2><button>Add to Cart</button><a href='/product/lens'>View Lenses</a>",
            raw_text="Apex 8K Pro Camera Specifications Add to Cart View Lenses",
            raw_text_length=56,
            raw_word_count=9,
            heading_tree=[
                HeadingItem(tag="h1", level=1, text="Apex 8K Pro Camera", dom_index=0),
                HeadingItem(tag="h2", level=2, text="Specifications", dom_index=1)
            ],
            internal_links=[
                LinkItem(url="https://example.com/product/lens", anchor_text="View Lenses", is_internal=True),
                LinkItem(url="https://example.com/cart", anchor_text="Cart", is_internal=True)
            ]
        )
        ctx = CrawlContext(
            root_url="https://example.com/",
            domain="example.com",
            audited_at="2026-09-02T12:00:00Z",
            site_archetype=SiteArchetype.ECOMMERCE,
            robots_policy=RobotsPolicy(exists=False, url="", raw_content=""),
            sitemap_summary=SitemapSummary(exists=False),
            pages=[page]
        )
        findings = inspect_engagement(ctx)
        self.assertEqual(len(findings), 0, "Well-structured product page must produce 0 engagement defects.")

    def test_dead_end_product_page_emits_finding(self):
        # Product detail page with zero purchase actions and zero related internal links
        page = PageEvidence(
            url="https://example.com/product/dead-end-item",
            normalized_url="https://example.com/product/dead-end-item",
            status_code=200,
            response_time_ms=25.0,
            content_type="text/html",
            page_archetype=PageArchetype.PRODUCT_DETAIL,
            is_primary_page=True,
            title="Dead End Gadget",
            meta_description="",
            canonical_url=None,
            meta_tags={},
            raw_html="<h1>Dead End Gadget</h1><p>A description of the gadget.</p>",
            raw_text="Dead End Gadget A description of the gadget.",
            raw_text_length=44,
            raw_word_count=7,
            heading_tree=[HeadingItem(tag="h1", level=1, text="Dead End Gadget", dom_index=0)],
            internal_links=[]  # Dead end
        )
        ctx = CrawlContext(
            root_url="https://example.com/",
            domain="example.com",
            audited_at="2026-09-02T12:00:00Z",
            site_archetype=SiteArchetype.ECOMMERCE,
            robots_policy=RobotsPolicy(exists=False, url="", raw_content=""),
            sitemap_summary=SitemapSummary(exists=False),
            pages=[page]
        )
        findings = inspect_engagement(ctx)
        dead_end_finding = next((f for f in findings if "purchase pathway" in f["title"].lower()), None)
        self.assertIsNotNone(dead_end_finding)
        self.assertEqual(dead_end_finding["severity"], "high")

    def test_terminal_legal_page_no_false_cta_defect(self):
        # Privacy policy page legitimately has no conversion CTA or related product links
        page = PageEvidence(
            url="https://example.com/privacy-policy",
            normalized_url="https://example.com/privacy-policy",
            status_code=200,
            response_time_ms=20.0,
            content_type="text/html",
            page_archetype=PageArchetype.LEGAL,
            is_primary_page=False,
            title="Privacy Policy",
            meta_description="",
            canonical_url=None,
            meta_tags={},
            raw_html="<h1>Privacy Policy</h1><p>We respect your privacy.</p>",
            raw_text="Privacy Policy We respect your privacy.",
            raw_text_length=38,
            raw_word_count=5,
            heading_tree=[HeadingItem(tag="h1", level=1, text="Privacy Policy", dom_index=0)],
            internal_links=[]
        )
        ctx = CrawlContext(
            root_url="https://example.com/",
            domain="example.com",
            audited_at="2026-09-02T12:00:00Z",
            site_archetype=SiteArchetype.ECOMMERCE,
            robots_policy=RobotsPolicy(exists=False, url="", raw_content=""),
            sitemap_summary=SitemapSummary(exists=False),
            pages=[page]
        )
        findings = inspect_engagement(ctx)
        self.assertEqual(len(findings), 0, "Terminal legal/privacy pages must not be flagged for missing CTAs.")

    def test_severe_heading_gap_defect(self):
        # Page omitting H1 and H2 entirely, jumping straight to H4
        page = PageEvidence(
            url="https://example.com/about",
            normalized_url="https://example.com/about",
            status_code=200,
            response_time_ms=20.0,
            content_type="text/html",
            page_archetype=PageArchetype.ABOUT,
            is_primary_page=False,
            title="About Us",
            meta_description="",
            canonical_url=None,
            meta_tags={},
            raw_html="<h4>Our Mission</h4><h5>History</h5>",
            raw_text="Our Mission History",
            raw_text_length=19,
            raw_word_count=3,
            heading_tree=[
                HeadingItem(tag="h4", level=4, text="Our Mission", dom_index=0),
                HeadingItem(tag="h5", level=5, text="History", dom_index=1),
                HeadingItem(tag="h4", level=4, text="Team", dom_index=2)
            ]
        )
        ctx = CrawlContext(
            root_url="https://example.com/",
            domain="example.com",
            audited_at="2026-09-02T12:00:00Z",
            site_archetype=SiteArchetype.CORPORATE,
            robots_policy=RobotsPolicy(exists=False, url="", raw_content=""),
            sitemap_summary=SitemapSummary(exists=False),
            pages=[page]
        )
        findings = inspect_engagement(ctx)
        heading_finding = next((f for f in findings if "heading level gap" in f["title"].lower()), None)
        self.assertIsNotNone(heading_finding)
        self.assertEqual(heading_finding["severity"], "medium")

    def test_imperfect_but_understandable_headings_no_defect(self):
        # Page with H1 followed by two H2s (standard clean layout)
        page = PageEvidence(
            url="https://example.com/features",
            normalized_url="https://example.com/features",
            status_code=200,
            response_time_ms=20.0,
            content_type="text/html",
            page_archetype=PageArchetype.OTHER,
            is_primary_page=False,
            title="Features Overview",
            meta_description="",
            canonical_url=None,
            meta_tags={},
            raw_html="<h1>Features</h1><h2>Analytics</h2><h2>Integrations</h2>",
            raw_text="Features Analytics Integrations",
            raw_text_length=31,
            raw_word_count=3,
            heading_tree=[
                HeadingItem(tag="h1", level=1, text="Features", dom_index=0),
                HeadingItem(tag="h2", level=2, text="Analytics", dom_index=1),
                HeadingItem(tag="h2", level=2, text="Integrations", dom_index=2)
            ]
        )
        ctx = CrawlContext(
            root_url="https://example.com/",
            domain="example.com",
            audited_at="2026-09-02T12:00:00Z",
            site_archetype=SiteArchetype.B2B_SAAS,
            robots_policy=RobotsPolicy(exists=False, url="", raw_content=""),
            sitemap_summary=SitemapSummary(exists=False),
            pages=[page]
        )
        findings = inspect_engagement(ctx)
        heading_findings = [f for f in findings if "heading" in f["title"].lower()]
        self.assertEqual(len(heading_findings), 0, "Normal sequential headings should not trigger defects.")


if __name__ == "__main__":
    unittest.main()
