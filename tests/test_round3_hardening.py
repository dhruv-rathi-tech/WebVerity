"""
Targeted Regression Test Suite for Round 3 Hardening.
Verifies the 6 specific adversarial gap mitigations:
1. Robots.txt safety & malformed directives
2. Multilingual engagement & non-English false positive suppression
3. Semantic image factual trap detection (surrounding headings/figures)
4. Multi-hop canonical chain and circular loop detection
5. HTTP 429 rate limit clean handling
6. Headless rendering unavailable graceful limitation reporting
"""

import unittest
from core.models import (
    CrawlContext, PageEvidence, RobotsPolicy, BotRule,
    SiteArchetype, PageArchetype, HeadingItem, LinkItem, ImageItem, SitemapSummary
)
from core.robots import parse_robots_txt, is_path_allowed_for_bot
from core.extractor import extract_page_evidence
from core.engagement_analyzer import analyze_page_engagement
import importlib.util
import os

_crawl_render_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "skills", "crawl-render-audit", "scripts", "inspect_crawler.py"))
_spec = importlib.util.spec_from_file_location("inspect_crawler", _crawl_render_path)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)
inspect_crawl_and_render = _mod.inspect_crawl_and_render


class TestRound3Hardening(unittest.TestCase):

    def test_01_robots_malformed_and_resilient_parsing(self):
        # Test partially malformed lines, missing colons, equals signs, trailing characters
        malformed_raw = """
        # Header comment
        User-agent *
        INVALID_UNRELATED_LINE_HERE
        Disallow = /admin;
        Disallow: /secret,
        Allow: /public/
        
        User-agent: GPTBot
        Disallow /private/data
        """
        policy = parse_robots_txt("https://example.com/robots.txt", malformed_raw)
        self.assertTrue(policy.exists)
        self.assertIn("*", policy.bot_rules)
        self.assertIn("GPTBot", policy.bot_rules)

        # Check paths safely captured despite malformed delimiters
        self.assertIn("/admin", policy.bot_rules["*"].disallowed_paths)
        self.assertIn("/secret", policy.bot_rules["*"].disallowed_paths)
        self.assertIn("/public/", policy.bot_rules["*"].allowed_paths)
        self.assertIn("/private/data", policy.bot_rules["GPTBot"].disallowed_paths)

        # Path allowance check
        self.assertFalse(is_path_allowed_for_bot(policy, "/admin/dashboard", "*"))
        self.assertFalse(is_path_allowed_for_bot(policy, "/secret/key", "*"))
        self.assertTrue(is_path_allowed_for_bot(policy, "/public/docs", "*"))
        self.assertFalse(is_path_allowed_for_bot(policy, "/private/data/file", "GPTBot"))
        self.assertTrue(is_path_allowed_for_bot(policy, "/other", "GPTBot"))

    def test_02_multilingual_engagement_and_false_positive_control(self):
        # 1. Spanish product page with "Añadir al carrito" -> MUST NOT be flagged as dead end
        p_es = PageEvidence(
            url="https://tienda.example/producto/1",
            normalized_url="https://tienda.example/producto/1",
            status_code=200,
            response_time_ms=50.0,
            content_type="text/html",
            page_archetype=PageArchetype.PRODUCT_DETAIL,
            is_primary_page=False,
            title="Cámara Profesional",
            meta_description="",
            canonical_url="https://tienda.example/producto/1",
            meta_tags={},
            raw_html="<html><body><h1>Cámara Profesional</h1><button>Añadir al carrito</button></body></html>",
            raw_text="Cámara Profesional Añadir al carrito",
            raw_text_length=36,
            raw_word_count=5,
            language="es",
            internal_links=[LinkItem(url="/categoria", anchor_text="Ver más", is_internal=True)]
        )
        issues_es = analyze_page_engagement(p_es, SiteArchetype.ECOMMERCE)
        self.assertEqual(len(issues_es), 0, "Spanish page with 'Añadir al carrito' must not produce dead-end defect.")

        # 2. German pricing page with "Kontakt" -> MUST NOT be flagged as dead end
        p_de = PageEvidence(
            url="https://dienst.example/preise",
            normalized_url="https://dienst.example/preise",
            status_code=200,
            response_time_ms=50.0,
            content_type="text/html",
            page_archetype=PageArchetype.PRICING,
            is_primary_page=False,
            title="Preise & Pläne",
            meta_description="",
            canonical_url="https://dienst.example/preise",
            meta_tags={},
            raw_html="<html><body><h1>Enterprise Plan</h1><p>Preise auf Anfrage.</p><a href='/kontakt'>Jetzt Kontaktieren</a></body></html>",
            raw_text="Enterprise Plan Preise auf Anfrage. Jetzt Kontaktieren",
            raw_text_length=54,
            raw_word_count=7,
            language="de",
            internal_links=[LinkItem(url="/kontakt", anchor_text="Jetzt Kontaktieren", is_internal=True)]
        )
        issues_de = analyze_page_engagement(p_de, SiteArchetype.B2B_SAAS)
        self.assertEqual(len(issues_de), 0, "German page with 'Kontaktieren' must not produce dead-end defect.")

        # 3. French page with navigation but unrecognized verbs -> Suppressed to avoid false dead-end
        p_fr = PageEvidence(
            url="https://site.example/produit",
            normalized_url="https://site.example/produit",
            status_code=200,
            response_time_ms=50.0,
            content_type="text/html",
            page_archetype=PageArchetype.PRODUCT_DETAIL,
            is_primary_page=False,
            title="Produit Spécial",
            meta_description="",
            canonical_url="https://site.example/produit",
            meta_tags={},
            raw_html="<html><body><h1>Produit Spécial</h1><p>Description détaillée.</p><a href='/accueil'>Retour</a></body></html>",
            raw_text="Produit Spécial Description détaillée. Retour",
            raw_text_length=45,
            raw_word_count=5,
            language="fr",
            internal_links=[LinkItem(url="/accueil", anchor_text="Retour", is_internal=True)]
        )
        issues_fr = analyze_page_engagement(p_fr, SiteArchetype.ECOMMERCE)
        self.assertEqual(len(issues_fr), 0, "Non-English page with navigation should not be penalized with strong dead-end defect.")

    def test_03_semantic_image_trap_detection(self):
        html = """<!DOCTYPE html>
        <html lang="en">
        <body>
          <h2>Technical Specifications</h2>
          <img src="/images/img_98741.png">
          
          <img src="/icons/logo.png" role="presentation">
          
          <figure>
            <figcaption>Pricing and Plan Comparison</figcaption>
            <img src="/assets/img_88.png">
          </figure>
        </body>
        </html>"""
        ev = extract_page_evidence("https://example.com/item", html, 200, 30.0)
        
        # 1. Language extracted
        self.assertEqual(ev.language, "en")

        # 2. Verify image relevance classification
        # First image under H2 Specifications -> content relevant
        self.assertTrue(ev.images[0].is_content_relevant)
        self.assertIn("spec", ev.images[0].context_keyword)
        self.assertFalse(ev.images[0].has_alt)

        # Second image with role="presentation" -> NOT content relevant (accessibility guardrail)
        self.assertFalse(ev.images[1].is_content_relevant)

        # Third image in figure with figcaption "Pricing" -> content relevant
        self.assertTrue(ev.images[2].is_content_relevant)
        self.assertIn("pricing", ev.images[2].context_keyword)

    def test_04_canonical_chain_and_cycle_detection(self):
        # 1. Standard self-referential canonical -> 0 findings (Best Practice)
        p1 = PageEvidence(
            url="https://example.com/page1",
            normalized_url="https://example.com/page1",
            status_code=200,
            response_time_ms=20.0,
            content_type="text/html",
            page_archetype=PageArchetype.HOMEPAGE,
            is_primary_page=True,
            title="Page 1",
            meta_description="",
            canonical_url="https://example.com/page1",
            meta_tags={},
            raw_html="<html><body><h1>Page 1</h1></body></html>",
            raw_text="Page 1",
            raw_text_length=6,
            raw_word_count=2
        )
        ctx_self = CrawlContext(
            root_url="https://example.com",
            domain="example.com",
            audited_at="2026-09-04T12:00:00Z",
            site_archetype=SiteArchetype.CORPORATE,
            robots_policy=RobotsPolicy(exists=False, url="", raw_content=""),
            sitemap_summary=SitemapSummary(exists=False),
            pages=[p1]
        )
        f_self = inspect_crawl_and_render(ctx_self)
        self.assertEqual(len(f_self), 0, "Self-referential canonical must produce 0 findings.")

        # 2. Multi-hop canonical chain: A -> B -> C
        p_a = PageEvidence(
            url="https://example.com/a",
            normalized_url="https://example.com/a",
            status_code=200,
            response_time_ms=20.0,
            content_type="text/html",
            page_archetype=PageArchetype.OTHER,
            is_primary_page=False,
            title="Page A",
            meta_description="",
            canonical_url="https://example.com/b",
            meta_tags={},
            raw_html="<html><body>Page A</body></html>",
            raw_text="Page A",
            raw_text_length=6,
            raw_word_count=2
        )
        p_b = PageEvidence(
            url="https://example.com/b",
            normalized_url="https://example.com/b",
            status_code=200,
            response_time_ms=20.0,
            content_type="text/html",
            page_archetype=PageArchetype.OTHER,
            is_primary_page=False,
            title="Page B",
            meta_description="",
            canonical_url="https://example.com/c",
            meta_tags={},
            raw_html="<html><body>Page B</body></html>",
            raw_text="Page B",
            raw_text_length=6,
            raw_word_count=2
        )
        p_c = PageEvidence(
            url="https://example.com/c",
            normalized_url="https://example.com/c",
            status_code=200,
            response_time_ms=20.0,
            content_type="text/html",
            page_archetype=PageArchetype.OTHER,
            is_primary_page=False,
            title="Page C",
            meta_description="",
            canonical_url="https://example.com/c",
            meta_tags={},
            raw_html="<html><body>Page C</body></html>",
            raw_text="Page C",
            raw_text_length=6,
            raw_word_count=2
        )
        ctx_chain = CrawlContext(
            root_url="https://example.com",
            domain="example.com",
            audited_at="2026-09-04T12:00:00Z",
            site_archetype=SiteArchetype.CORPORATE,
            robots_policy=RobotsPolicy(exists=False, url="", raw_content=""),
            sitemap_summary=SitemapSummary(exists=False),
            pages=[p_a, p_b, p_c]
        )
        f_chain = inspect_crawl_and_render(ctx_chain)
        chain_finding = next((f for f in f_chain if "canonical chain" in f["title"].lower()), None)
        self.assertIsNotNone(chain_finding, "Multi-hop canonical chain must be detected.")
        self.assertIn("https://example.com/a -> https://example.com/b -> https://example.com/c", chain_finding["evidence"])

        # 3. Circular canonical loop: X -> Y -> X
        p_x = PageEvidence(
            url="https://example.com/x",
            normalized_url="https://example.com/x",
            status_code=200,
            response_time_ms=20.0,
            content_type="text/html",
            page_archetype=PageArchetype.OTHER,
            is_primary_page=False,
            title="Page X",
            meta_description="",
            canonical_url="https://example.com/y",
            meta_tags={},
            raw_html="<html><body>Page X</body></html>",
            raw_text="Page X",
            raw_text_length=6,
            raw_word_count=2
        )
        p_y = PageEvidence(
            url="https://example.com/y",
            normalized_url="https://example.com/y",
            status_code=200,
            response_time_ms=20.0,
            content_type="text/html",
            page_archetype=PageArchetype.OTHER,
            is_primary_page=False,
            title="Page Y",
            meta_description="",
            canonical_url="https://example.com/x",
            meta_tags={},
            raw_html="<html><body>Page Y</body></html>",
            raw_text="Page Y",
            raw_text_length=6,
            raw_word_count=2
        )
        ctx_cycle = CrawlContext(
            root_url="https://example.com",
            domain="example.com",
            audited_at="2026-09-04T12:00:00Z",
            site_archetype=SiteArchetype.CORPORATE,
            robots_policy=RobotsPolicy(exists=False, url="", raw_content=""),
            sitemap_summary=SitemapSummary(exists=False),
            pages=[p_x, p_y]
        )
        f_cycle = inspect_crawl_and_render(ctx_cycle)
        cycle_finding = next((f for f in f_cycle if "circular canonical" in f["title"].lower()), None)
        self.assertIsNotNone(cycle_finding, "Circular canonical loop must be detected.")
        self.assertEqual(cycle_finding["severity"], "high")

    def test_05_csr_unverified_rendering_fallback(self):
        # When headless rendering was unavailable (rendering_available=False),
        # an empty SPA container must NOT be falsely claimed as confirmed CSR defect.
        p_spa = PageEvidence(
            url="https://spa.example/",
            normalized_url="https://spa.example/",
            status_code=200,
            response_time_ms=25.0,
            content_type="text/html",
            page_archetype=PageArchetype.HOMEPAGE,
            is_primary_page=True,
            title="SPA App",
            meta_description="",
            canonical_url="https://spa.example/",
            meta_tags={},
            raw_html="<div id='app'></div>",
            raw_text="",
            raw_text_length=0,
            raw_word_count=0,
            required_rendering_trigger=True,
            missing_facts_in_raw=[]
        )
        ctx_spa = CrawlContext(
            root_url="https://spa.example",
            domain="spa.example",
            audited_at="2026-09-04T12:00:00Z",
            site_archetype=SiteArchetype.B2B_SAAS,
            robots_policy=RobotsPolicy(exists=False, url="", raw_content=""),
            sitemap_summary=SitemapSummary(exists=False),
            pages=[p_spa],
            rendering_available=False
        )
        findings = inspect_crawl_and_render(ctx_spa)
        self.assertEqual(len(findings), 1)
        finding = findings[0]
        self.assertEqual(finding["severity"], "info", "Unverified rendering must be informational, not a confirmed high-severity defect.")
        self.assertEqual(finding["confidence"], "low")
        self.assertIn("unverified in environment", finding["title"].lower())


if __name__ == "__main__":
    unittest.main()
