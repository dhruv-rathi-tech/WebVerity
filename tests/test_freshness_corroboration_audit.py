"""
Test Suite: Freshness & Corroboration Audit Skill (Refined)
Tests cross-page factual consistency, temporal freshness signals,
and the multi-factor external corroboration framework (authority, relevance, directness, consistency).
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
    PageArchetype
)

# Load check_freshness module via importlib
_skill_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "skills", "freshness-corroboration-audit", "scripts", "check_freshness.py"))
_spec = importlib.util.spec_from_file_location("check_freshness", _skill_path)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)
check_freshness_and_corroboration = _mod.check_freshness_and_corroboration


class TestFreshnessCorroborationAudit(unittest.TestCase):

    def setUp(self):
        self.sample_home_page = PageEvidence(
            url="https://example.com/",
            normalized_url="https://example.com/",
            status_code=200,
            response_time_ms=15.0,
            content_type="text/html",
            page_archetype=PageArchetype.HOMEPAGE,
            is_primary_page=True,
            title="Apex Dynamics Corp",
            meta_description="",
            canonical_url=None,
            meta_tags={},
            raw_html="<footer>© 2026 Apex Dynamics Inc.</footer>",
            raw_text="Apex Dynamics Corp",
            raw_text_length=18,
            raw_word_count=3,
            extracted_dates={"copyright_year": "2026"}
        )
        self.base_context = CrawlContext(
            root_url="https://example.com/",
            domain="example.com",
            audited_at="2026-09-02T12:00:00Z",
            site_archetype=SiteArchetype.CORPORATE,
            robots_policy=RobotsPolicy(exists=False, url="", raw_content=""),
            sitemap_summary=SitemapSummary(exists=False),
            pages=[self.sample_home_page]
        )

    def test_old_copyright_year_low_severity_observation(self):
        page = PageEvidence(
            url="https://example.com/",
            normalized_url="https://example.com/",
            status_code=200,
            response_time_ms=20.0,
            content_type="text/html",
            page_archetype=PageArchetype.HOMEPAGE,
            is_primary_page=True,
            title="Apex Dynamics",
            meta_description="",
            canonical_url=None,
            meta_tags={},
            raw_html="<footer>© 2022 Apex Dynamics Inc.</footer>",
            raw_text="Apex Dynamics Precision Optics",
            raw_text_length=30,
            raw_word_count=4,
            extracted_dates={"copyright_year": "2022"}
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
        findings = check_freshness_and_corroboration(ctx)
        copyright_finding = next((f for f in findings if "copyright" in f["title"].lower()), None)
        self.assertIsNotNone(copyright_finding)
        self.assertEqual(copyright_finding["severity"], "low", "Old copyright alone must be low severity observation, not a critical defect.")
        self.assertIn("2022", copyright_finding["evidence"])

    def test_genuinely_stale_expired_promotion(self):
        page = PageEvidence(
            url="https://example.com/promo",
            normalized_url="https://example.com/promo",
            status_code=200,
            response_time_ms=20.0,
            content_type="text/html",
            page_archetype=PageArchetype.OTHER,
            is_primary_page=False,
            title="Summer Special",
            meta_description="",
            canonical_url=None,
            meta_tags={},
            raw_html="<p>Special Summer Deal: Offer valid through August 2023 only!</p>",
            raw_text="Special Summer Deal: Offer valid through August 2023 only!",
            raw_text_length=58,
            raw_word_count=9
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
        findings = check_freshness_and_corroboration(ctx)
        stale_finding = next((f for f in findings if "expired promotional" in f["title"].lower()), None)
        self.assertIsNotNone(stale_finding)
        self.assertEqual(stale_finding["severity"], "medium")
        self.assertIn("Offer valid through August 2023", stale_finding["evidence"])

    def test_cross_page_factual_contradiction_phone(self):
        home_page = PageEvidence(
            url="https://example.com/",
            normalized_url="https://example.com/",
            status_code=200,
            response_time_ms=15.0,
            content_type="text/html",
            page_archetype=PageArchetype.HOMEPAGE,
            is_primary_page=True,
            title="Apex Home",
            meta_description="",
            canonical_url=None,
            meta_tags={},
            raw_html="<p>Call us today at +1-800-555-0199</p>",
            raw_text="Apex Home Call us today at +1-800-555-0199",
            raw_text_length=42,
            raw_word_count=7
        )
        contact_page = PageEvidence(
            url="https://example.com/contact",
            normalized_url="https://example.com/contact",
            status_code=200,
            response_time_ms=18.0,
            content_type="text/html",
            page_archetype=PageArchetype.CONTACT,
            is_primary_page=False,
            title="Contact Apex",
            meta_description="",
            canonical_url=None,
            meta_tags={},
            raw_html="<p>Reach our support team at +1-800-555-9999</p>",
            raw_text="Contact Apex Reach our support team at +1-800-555-9999",
            raw_text_length=52,
            raw_word_count=8
        )
        ctx = CrawlContext(
            root_url="https://example.com/",
            domain="example.com",
            audited_at="2026-09-02T12:00:00Z",
            site_archetype=SiteArchetype.CORPORATE,
            robots_policy=RobotsPolicy(exists=False, url="", raw_content=""),
            sitemap_summary=SitemapSummary(exists=False),
            pages=[home_page, contact_page]
        )
        findings = check_freshness_and_corroboration(ctx)
        conflict_finding = next((f for f in findings if "phone number" in f["title"].lower()), None)
        self.assertIsNotNone(conflict_finding)
        self.assertEqual(conflict_finding["severity"], "high")
        self.assertIn("+1-800-555-0199", conflict_finding["evidence"])
        self.assertIn("+1-800-555-9999", conflict_finding["evidence"])

    def test_consistent_facts_across_pages_no_false_contradiction(self):
        home_page = PageEvidence(
            url="https://example.com/",
            normalized_url="https://example.com/",
            status_code=200,
            response_time_ms=15.0,
            content_type="text/html",
            page_archetype=PageArchetype.HOMEPAGE,
            is_primary_page=True,
            title="Apex Home",
            meta_description="",
            canonical_url=None,
            meta_tags={},
            raw_html="<p>Call us: +1-800-555-0199</p>",
            raw_text="Apex Home Call us: +1-800-555-0199",
            raw_text_length=33,
            raw_word_count=5
        )
        contact_page = PageEvidence(
            url="https://example.com/contact",
            normalized_url="https://example.com/contact",
            status_code=200,
            response_time_ms=18.0,
            content_type="text/html",
            page_archetype=PageArchetype.CONTACT,
            is_primary_page=False,
            title="Contact Us",
            meta_description="",
            canonical_url=None,
            meta_tags={},
            raw_html="<p>Official Support: +1-800-555-0199</p>",
            raw_text="Contact Us Official Support: +1-800-555-0199",
            raw_text_length=43,
            raw_word_count=5
        )
        ctx = CrawlContext(
            root_url="https://example.com/",
            domain="example.com",
            audited_at="2026-09-02T12:00:00Z",
            site_archetype=SiteArchetype.CORPORATE,
            robots_policy=RobotsPolicy(exists=False, url="", raw_content=""),
            sitemap_summary=SitemapSummary(exists=False),
            pages=[home_page, contact_page]
        )
        findings = check_freshness_and_corroboration(ctx)
        contradiction_findings = [f for f in findings if "contradiction" in f["title"].lower()]
        self.assertEqual(len(contradiction_findings), 0, "Consistent phone numbers must not produce contradiction findings.")

    # -------------------------------------------------------------------------
    # EXTERNAL CORROBORATION MULTI-FACTOR TESTS
    # -------------------------------------------------------------------------
    def test_authoritative_direct_conflicting_source_emits_finding(self):
        # 1. Authoritative official registry + directly relevant attribute mismatch -> Finding emitted
        records = [
            {
                "source_name": "State Division of Corporations",
                "source_type": "official_registry",
                "attribute": "company_name",
                "is_entity_relevant": True,
                "is_direct_statement": True,
                "external_value": "Apex Dynamics International LLC"
            }
        ]
        findings = check_freshness_and_corroboration(self.base_context, external_records=records)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["severity"], "medium")
        self.assertIn("State Division of Corporations", findings[0]["evidence"])

    def test_weak_or_irrelevant_source_ignored(self):
        # 2. Unverified blog or irrelevant source -> Filtered out (0 findings)
        records = [
            {
                "source_name": "Random Tech Forum",
                "source_type": "blog_forum",  # Non-authoritative
                "attribute": "company_name",
                "is_entity_relevant": True,
                "is_direct_statement": True,
                "external_value": "Apex Camera Hub"
            },
            {
                "source_name": "Wikipedia Disambiguation",
                "source_type": "knowledge_graph",
                "attribute": "company_name",
                "is_entity_relevant": False,  # Irrelevant different entity with similar name
                "is_direct_statement": True,
                "external_value": "Apex Dynamics Robotics"
            }
        ]
        findings = check_freshness_and_corroboration(self.base_context, external_records=records)
        self.assertEqual(len(findings), 0, "Weak or irrelevant sources must not trigger findings.")

    def test_authoritative_but_indirect_source_no_strong_contradiction(self):
        # 3. Authoritative source with indirect statement only -> Filtered out / no hard defect
        records = [
            {
                "source_name": "SEC News Digest",
                "source_type": "regulatory_filing",
                "attribute": "company_name",
                "is_entity_relevant": True,
                "is_direct_statement": False,  # Passing indirect mention
                "external_value": "Apex Group"
            }
        ]
        findings = check_freshness_and_corroboration(self.base_context, external_records=records)
        self.assertEqual(len(findings), 0, "Indirect mentions in authoritative filings should not trigger hard defects.")

    def test_unavailable_external_source_graceful_fallback(self):
        # 4. Unavailable external records -> Graceful fallback
        findings = check_freshness_and_corroboration(self.base_context, external_records=None)
        self.assertEqual(len(findings), 0)

    def test_conflicting_external_sources_disagreement_reports_uncertainty(self):
        # 5. Multiple external authoritative sources disagree among themselves -> Uncertainty observation
        records = [
            {
                "source_name": "State Registrar A",
                "source_type": "official_registry",
                "attribute": "company_name",
                "is_entity_relevant": True,
                "is_direct_statement": True,
                "external_value": "Apex Dynamics Corp"
            },
            {
                "source_name": "National Patent Registry B",
                "source_type": "official_registry",
                "attribute": "company_name",
                "is_entity_relevant": True,
                "is_direct_statement": True,
                "external_value": "Apex Optical Systems Inc"
            }
        ]
        findings = check_freshness_and_corroboration(self.base_context, external_records=records)
        self.assertEqual(len(findings), 1)
        f = findings[0]
        self.assertIn("conflicting records", f["title"].lower())
        self.assertEqual(f["severity"], "low")  # Downgraded to uncertainty observation
        self.assertIn("State Registrar A", f["observation"])
        self.assertIn("National Patent Registry B", f["observation"])

    def test_consistent_first_party_and_external_data_no_findings(self):
        # 6. Authoritative external source matches first-party claim exactly -> 0 findings
        records = [
            {
                "source_name": "Official State Division of Corporations",
                "source_type": "official_registry",
                "attribute": "company_name",
                "is_entity_relevant": True,
                "is_direct_statement": True,
                "external_value": "Apex Dynamics Corp"  # Matches home_page title
            }
        ]
        findings = check_freshness_and_corroboration(self.base_context, external_records=records)
        self.assertEqual(len(findings), 0, "Exact agreement between first-party and external source must produce 0 findings.")


if __name__ == "__main__":
    unittest.main()
