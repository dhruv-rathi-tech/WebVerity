"""
Integration Test Suite: Audit Orchestrator Skill
Tests end-to-end multi-skill composition, cross-skill deduplication,
schema compliance, fault isolation, and graceful degradation.
"""

import os
import sys
import json
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
    LinkItem,
    JsonLdBlock
)

# Load orchestrator
_skill_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "skills", "audit-orchestrator", "scripts", "orchestrate.py"))
_spec = importlib.util.spec_from_file_location("orchestrate", _skill_path)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)
AuditOrchestrator = _mod.AuditOrchestrator


class TestAuditOrchestratorIntegration(unittest.TestCase):

    def setUp(self):
        self.orchestrator = AuditOrchestrator()

        # Load official report schema
        schema_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "skills", "audit-orchestrator", "references", "report-schema.json"))
        with open(schema_path, "r", encoding="utf-8") as f:
            self.report_schema = json.load(f)

    def _validate_report_structure(self, report: dict):
        """Validates report matches report-schema.json requirements"""
        self.assertIn("site", report)
        self.assertIn("audited_at", report)
        self.assertIn("summary", report)
        self.assertIn("findings", report)
        self.assertIn("proactive_recommendations", report)

        summary = report["summary"]
        for k in ("total_findings", "critical", "high", "medium", "low", "info"):
            self.assertIn(k, summary)
            self.assertIsInstance(summary[k], int)

        for f in report["findings"]:
            self.assertIn("id", f)
            self.assertTrue(f["id"].startswith("F-"))
            self.assertIn("title", f)
            self.assertIn("severity", f)
            self.assertIn(f["severity"], ("critical", "high", "medium", "low", "info"))
            self.assertIn("evidence", f)
            self.assertIn("suggested_action", f)
            self.assertIn("summary", f["suggested_action"])
            self.assertIn("priority", f["suggested_action"])

    def test_full_audit_multi_skill_composition(self):
        # 1. Page with Crawl/Render CSR issue, Structured Data conflict, and Engagement dead-end
        page = PageEvidence(
            url="https://store.example.com/product/bad-camera",
            normalized_url="https://store.example.com/product/bad-camera",
            status_code=200,
            response_time_ms=25.0,
            content_type="text/html",
            page_archetype=PageArchetype.PRODUCT_DETAIL,
            is_primary_page=True,
            title="Cinema Camera 8K",
            meta_description="",
            canonical_url=None,
            meta_tags={},
            raw_html="<div id='app'>Loading camera details...</div>",
            raw_text="Loading camera details...",
            raw_text_length=26,
            raw_word_count=3,
            rendered_dom="<div id='app'><h1>Cinema Camera 8K</h1><p>Price: $4999.00 USD</p></div>",
            rendered_text="Cinema Camera 8K Price: $4999.00 USD",
            missing_facts_in_raw=["price", "$4999.00", "camera"],
            heading_tree=[HeadingItem(tag="h1", level=1, text="Cinema Camera 8K", dom_index=0)],
            internal_links=[],  # Dead end
            json_ld=[
                JsonLdBlock(
                    raw_json='{"@type": "Product", "offers": {"@type": "Offer", "price": "1999.00", "priceCurrency": "USD"}}',
                    parsed_data={"@type": "Product", "offers": {"@type": "Offer", "price": "1999.00", "priceCurrency": "USD"}},
                    schema_types=["Product", "Offer"]
                )
            ]
        )
        ctx = CrawlContext(
            root_url="https://store.example.com/",
            domain="store.example.com",
            audited_at="2026-09-02T12:00:00Z",
            site_archetype=SiteArchetype.ECOMMERCE,
            robots_policy=RobotsPolicy(exists=True, url="https://store.example.com/robots.txt", raw_content="User-agent: GPTBot\nDisallow: /"),
            sitemap_summary=SitemapSummary(exists=False),
            pages=[page]
        )

        report = self.orchestrator.run("https://store.example.com/", existing_context=ctx)
        self._validate_report_structure(report)

        # Must contain findings across multiple domain skills
        categories = {f["category"] for f in report["findings"]}
        self.assertTrue("crawlability" in categories or "machine_readability" in categories)
        self.assertIn("structured_data", categories)
        self.assertIn("on_site_engagement", categories)
        self.assertGreaterEqual(report["summary"]["total_findings"], 3)

    def test_distinct_findings_on_same_url_preserved(self):
        # A single URL with both CSR content loss and a Dead-end CTA should have BOTH findings preserved
        page = PageEvidence(
            url="https://store.example.com/product/item",
            normalized_url="https://store.example.com/product/item",
            status_code=200,
            response_time_ms=20.0,
            content_type="text/html",
            page_archetype=PageArchetype.PRODUCT_DETAIL,
            is_primary_page=True,
            title="Item",
            meta_description="",
            canonical_url=None,
            meta_tags={},
            raw_html="<div id='app'>Loading...</div>",
            raw_text="Loading...",
            raw_text_length=10,
            raw_word_count=1,
            rendered_dom="<div id='app'><h1>Item</h1><p>Price: $100</p></div>",
            rendered_text="Item Price: $100",
            missing_facts_in_raw=["price", "$100"],
            internal_links=[]
        )
        ctx = CrawlContext(
            root_url="https://store.example.com/",
            domain="store.example.com",
            audited_at="2026-09-02T12:00:00Z",
            site_archetype=SiteArchetype.ECOMMERCE,
            robots_policy=RobotsPolicy(exists=False, url="", raw_content=""),
            sitemap_summary=SitemapSummary(exists=False),
            pages=[page]
        )
        report = self.orchestrator.run("https://store.example.com/", existing_context=ctx)
        
        # Verify both CSR finding and Next-Step finding exist
        has_csr = any("missing from initial HTML" in f["title"] or f["category"] == "machine_readability" for f in report["findings"])
        has_next_step = any("purchase pathway" in f["title"].lower() for f in report["findings"])
        self.assertTrue(has_csr, "CSR finding must be preserved.")
        self.assertTrue(has_next_step, "Engagement next-step finding must be preserved as a distinct finding.")

    def test_deduplication_of_exact_duplicate_findings(self):
        # Two findings with identical category, url, and root-cause -> deduplicate to 1
        raw_findings = [
            {
                "id": "F-001",
                "title": "Invalid JSON-LD syntax (title variant A)",
                "category": "structured_data",
                "severity": "high",
                "confidence": "high",
                "observation": "Malformed syntax",
                "evidence": "Syntax error line 1",
                "root_cause": "The embedded JSON-LD script contains unescaped characters",
                "impact": "Parsers fail",
                "affected_urls": ["https://example.com/p1"],
                "suggested_action": {"summary": "Fix syntax", "priority": "high"}
            },
            {
                "id": "F-002",
                "title": "JSON-LD syntax error (title variant B - different title same root)",
                "category": "structured_data",
                "severity": "high",
                "confidence": "high",
                "observation": "Malformed syntax",
                "evidence": "Syntax error line 1",
                "root_cause": "The embedded JSON-LD script contains unescaped characters",
                "impact": "Parsers fail",
                "affected_urls": ["https://example.com/p1"],
                "suggested_action": {"summary": "Fix syntax", "priority": "high"}
            }
        ]
        deduped = self.orchestrator._deduplicate_findings(raw_findings)
        self.assertEqual(len(deduped), 1, "Findings with same category+url+root-cause must deduplicate regardless of different titles.")

    def test_csr_missing_fact_and_missing_schema_preserved_as_distinct(self):
        # CSR content loss (machine_readability) and missing machine-readable schema (structured_data)
        # on the SAME URL have DIFFERENT root causes -> both must be preserved
        raw_findings = [
            {
                "id": "F-001",
                "title": "Key factual content missing from initial HTML response",
                "category": "machine_readability",
                "severity": "high",
                "confidence": "high",
                "observation": "Price and specs rendered only via JavaScript.",
                "evidence": "URL: https://example.com/product/cam",
                "root_cause": "Product attributes, pricing, or core body copy are injected purely via client-side JavaScript hydration without server-side rendering (SSR).",
                "impact": "Automated extractors that inspect only the initial HTTP response will not observe these attributes.",
                "affected_urls": ["https://example.com/product/cam"],
                "suggested_action": {"summary": "Implement SSR.", "priority": "high"}
            },
            {
                "id": "F-002",
                "title": "Visible commercial product facts lack structured Product/Offer representation",
                "category": "structured_data",
                "severity": "high",
                "confidence": "high",
                "observation": "Page has commercial signals but no Product/Offer JSON-LD.",
                "evidence": "URL: https://example.com/product/cam",
                "root_cause": "Commercial attributes are embedded only in visual markup without corresponding machine-readable JSON-LD metadata.",
                "impact": "Automated assistants must rely on heuristic scraping.",
                "affected_urls": ["https://example.com/product/cam"],
                "suggested_action": {"summary": "Add Product/Offer JSON-LD.", "priority": "high"}
            }
        ]
        deduped = self.orchestrator._deduplicate_findings(raw_findings)
        self.assertEqual(len(deduped), 2, "CSR rendering defect and missing schema have genuinely different root causes and must be preserved as distinct findings.")

    def test_graceful_fault_isolation_on_skill_error(self):
        # Simulate a skill failure by temporarily replacing a handler with an exception raiser
        orig_fn = self.orchestrator._validate_structured_data
        self.orchestrator._validate_structured_data = lambda ctx: (_ for _ in ()).throw(RuntimeError("Simulated Skill Failure"))
        
        ctx = CrawlContext(
            root_url="https://example.com/",
            domain="example.com",
            audited_at="2026-09-02T12:00:00Z",
            site_archetype=SiteArchetype.CORPORATE,
            robots_policy=RobotsPolicy(exists=False, url="", raw_content=""),
            sitemap_summary=SitemapSummary(exists=False),
            pages=[]
        )
        try:
            report = self.orchestrator.run("https://example.com/", existing_context=ctx)
            self._validate_report_structure(report)
            # Must return valid report without throwing uncaught exception
            self.assertIsInstance(report, dict)
        finally:
            self.orchestrator._validate_structured_data = orig_fn

    def test_healthy_site_produces_zero_findings(self):
        # Healthy static site with complete schema, clear headings, consistent facts
        page = PageEvidence(
            url="https://example.com/",
            normalized_url="https://example.com/",
            status_code=200,
            response_time_ms=15.0,
            content_type="text/html",
            page_archetype=PageArchetype.HOMEPAGE,
            is_primary_page=True,
            title="Apex Precision Dynamics",
            meta_description="Global leader in optical systems.",
            canonical_url="https://example.com/",
            meta_tags={},
            raw_html="<h1>Apex Precision Dynamics</h1><h2>Products</h2><a href='/contact'>Contact Sales</a><footer>© 2026 Apex Dynamics</footer>",
            raw_text="Apex Precision Dynamics Products Contact Sales © 2026 Apex Dynamics",
            raw_text_length=70,
            raw_word_count=10,
            heading_tree=[
                HeadingItem(tag="h1", level=1, text="Apex Precision Dynamics", dom_index=0),
                HeadingItem(tag="h2", level=2, text="Products", dom_index=1)
            ],
            internal_links=[LinkItem(url="https://example.com/contact", anchor_text="Contact Sales", is_internal=True)],
            extracted_dates={"copyright_year": "2026"}
        )
        ctx = CrawlContext(
            root_url="https://example.com/",
            domain="example.com",
            audited_at="2026-09-02T12:00:00Z",
            site_archetype=SiteArchetype.CORPORATE,
            robots_policy=RobotsPolicy(exists=True, url="https://example.com/robots.txt", raw_content="User-agent: *\nAllow: /"),
            sitemap_summary=SitemapSummary(exists=True),
            pages=[page]
        )
        report = self.orchestrator.run("https://example.com/", existing_context=ctx)
        self._validate_report_structure(report)
        self.assertEqual(report["summary"]["total_findings"], 0, "Healthy site must produce 0 defect findings.")

    def test_malformed_invalid_url_handling(self):
        report = self.orchestrator.run("not-a-valid-url")
        self._validate_report_structure(report)
        self.assertEqual(report["summary"]["total_findings"], 0)
        self.assertEqual(len(report["findings"]), 0)

    def test_csr_impact_language_avoids_bot_claims(self):
        # Verify CSR findings do not make blanket claims about specific named AI bots
        page = PageEvidence(
            url="https://example.com/product/x",
            normalized_url="https://example.com/product/x",
            status_code=200,
            response_time_ms=20.0,
            content_type="text/html",
            page_archetype=PageArchetype.PRODUCT_DETAIL,
            is_primary_page=True,
            title="Product X",
            meta_description="",
            canonical_url=None,
            meta_tags={},
            raw_html="<div id='app'>Loading...</div>",
            raw_text="Loading...",
            raw_text_length=10,
            raw_word_count=1,
            missing_facts_in_raw=["price", "stock"]
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
        report = self.orchestrator.run("https://example.com/", existing_context=ctx)
        csr_findings = [f for f in report["findings"] if f.get("category") == "machine_readability"]
        self.assertGreater(len(csr_findings), 0, "Should have a CSR finding.")
        for f in csr_findings:
            impact = f.get("impact", "")
            # Must NOT make blanket claims about specific named bot rendering behaviors
            self.assertNotIn("GPTBot", impact, "AI-impact must not mention specific bot names.")
            self.assertNotIn("PerplexityBot", impact, "AI-impact must not mention specific bot names.")
            self.assertNotIn("ClaudeBot", impact, "AI-impact must not mention specific bot names.")

    def test_sameAs_appears_as_proactive_recommendation_not_defect(self):
        # Organization schema present but no sameAs -> should be proactive recommendation, not a defect
        org_block = JsonLdBlock(
            raw_json='{"@type": "Organization", "name": "Acme Corp", "url": "https://acmecorp.com"}',
            parsed_data={"@type": "Organization", "name": "Acme Corp", "url": "https://acmecorp.com"},
            schema_types=["Organization"]
        )
        page = PageEvidence(
            url="https://acmecorp.com/",
            normalized_url="https://acmecorp.com/",
            status_code=200,
            response_time_ms=15.0,
            content_type="text/html",
            page_archetype=PageArchetype.HOMEPAGE,
            is_primary_page=True,
            title="Acme Corp",
            meta_description="",
            canonical_url=None,
            meta_tags={},
            raw_html="<h1>Acme Corp</h1>",
            raw_text="Acme Corp",
            raw_text_length=9,
            raw_word_count=2,
            json_ld=[org_block]
        )
        ctx = CrawlContext(
            root_url="https://acmecorp.com/",
            domain="acmecorp.com",
            audited_at="2026-09-02T12:00:00Z",
            site_archetype=SiteArchetype.CORPORATE,
            robots_policy=RobotsPolicy(exists=False, url="", raw_content=""),
            sitemap_summary=SitemapSummary(exists=False),
            pages=[page]
        )
        report = self.orchestrator.run("https://acmecorp.com/", existing_context=ctx)
        
        # Must appear as proactive recommendation, NOT a defect finding
        sameAs_defects = [f for f in report["findings"] if "sameAs" in f.get("title", "")]
        sameAs_recs = [r for r in report["proactive_recommendations"] if "sameAs" in r.get("title", "") or "disambiguation" in r.get("title", "").lower()]
        self.assertEqual(len(sameAs_defects), 0, "sameAs absence must NOT be a defect finding.")
        self.assertGreater(len(sameAs_recs), 0, "sameAs absence should appear as a proactive recommendation.")

    def test_sameAs_recommendation_not_prescriptive_wikidata_linkedin(self):
        # The sameAs recommendation must not universally prescribe specific platforms like Wikidata/LinkedIn
        import importlib.util
        _sp = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "skills", "structured-data-entity-audit", "scripts", "validate_schema.py"))
        _sp_spec = importlib.util.spec_from_file_location("vs", _sp)
        vs_mod = importlib.util.module_from_spec(_sp_spec)
        _sp_spec.loader.exec_module(vs_mod)
        
        org_block = JsonLdBlock(
            raw_json='{"@type": "Organization", "name": "Beta Labs"}',
            parsed_data={"@type": "Organization", "name": "Beta Labs"},
            schema_types=["Organization"]
        )
        page = PageEvidence(
            url="https://betalabs.com/",
            normalized_url="https://betalabs.com/",
            status_code=200,
            response_time_ms=10.0,
            content_type="text/html",
            page_archetype=PageArchetype.HOMEPAGE,
            is_primary_page=True,
            title="Beta Labs",
            meta_description="",
            canonical_url=None,
            meta_tags={},
            raw_html="",
            raw_text="Beta Labs",
            raw_text_length=9,
            raw_word_count=2,
            json_ld=[org_block]
        )
        ctx = CrawlContext(
            root_url="https://betalabs.com/",
            domain="betalabs.com",
            audited_at="2026-09-02T12:00:00Z",
            site_archetype=SiteArchetype.CORPORATE,
            robots_policy=RobotsPolicy(exists=False, url="", raw_content=""),
            sitemap_summary=SitemapSummary(exists=False),
            pages=[page]
        )
        findings = vs_mod.validate_structured_data(ctx)
        sameAs_finding = next((f for f in findings if "sameAs" in f.get("title", "")), None)
        if sameAs_finding:
            summary = sameAs_finding.get("suggested_action", {}).get("summary", "")
            # Must not universally prescribe specific platforms by name
            self.assertNotIn("Wikidata", summary, "Should not prescribe Wikidata universally.")
            self.assertNotIn("LinkedIn", summary, "Should not prescribe LinkedIn universally.")
            self.assertNotIn("Crunchbase", summary, "Should not prescribe Crunchbase universally.")


if __name__ == "__main__":
    unittest.main()
