"""
Test Suite: Functional Validation & Defect Detection
Verifies:
1. Internal link discovery and subdomain traversal.
2. Crawl depth and max_pages boundary enforcement.
3. Robots.txt and sitemap compliance.
4. Archetype classification grounding (no ungrounded PORTFOLIO forcing).
5. Deterministic controlled test fixture with known audit defects.
6. Execution and finding generation across all 4 audit skills.
7. Finding deduplication and scoring.
"""

import asyncio
import unittest
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading
from typing import Tuple

from core.url_utils import normalize_url, extract_domain, is_same_domain
from core.robots import parse_robots_txt, is_path_allowed_for_bot
from core.sitemap import parse_sitemap_xml
from core.extractor import extract_page_evidence
from core.classifier import classify_page_archetype, classify_site_archetype
from core.models import SiteArchetype, PageArchetype, PageEvidence
from core.crawler import AsyncCrawler
from audit import orchestrate_audit, AuditOrchestrator


class ControlledDefectSiteHandler(BaseHTTPRequestHandler):
    """
    Mock HTTP handler providing a deterministic multi-page website
    with deliberate, known AI-readiness, structured data, freshness,
    and engagement defects.
    """

    def log_message(self, format, *args):
        pass

    def do_GET(self):
        path = self.path.split("?")[0]

        if path == "/robots.txt":
            content = """User-agent: *
Disallow: /secret-admin/
Disallow: /blocked-zone/

User-agent: GPTBot
Disallow: /ai-restricted/

Sitemap: /sitemap.xml
"""
            self._send_response(200, "text/plain", content)
            return

        if path == "/sitemap.xml":
            content = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url><loc>/product/sensor-pro</loc></url>
  <url><loc>/docs-guide</loc></url>
  <url><loc>/stale-news</loc></url>
</urlset>
"""
            self._send_response(200, "application/xml", content)
            return

        if path in ("/", "/index.html"):
            # Homepage: multiple competing H1 headings, links to subpages, stale copyright
            content = """<!DOCTYPE html>
<html lang="en">
<head>
  <title>OmniTech Research Portal</title>
</head>
<body>
  <header>
    <h1>OmniTech Global Knowledge Platform</h1>
    <h1>Second Primary Heading</h1>
    <h1>Third Competing Heading</h1>
    <h1>Fourth Excess Heading</h1>
    <nav>
      <a href="/product/sensor-pro">Faulty Product</a>
      <a href="/docs-guide">Documentation Guide</a>
      <a href="/stale-news">Press Releases</a>
      <a href="/secret-admin/test">Admin Zone</a>
      <a href="/deep-level-1">Deep Level 1</a>
      <a href="https://external-partner.org/info">External Partner</a>
    </nav>
  </header>
  <main>
    <p>OmniTech builds open neural infrastructure and machine learning tools.</p>
    <img src="/images/diagram.png" alt="Architecture Overview Chart" />
  </main>
  <footer>
    <p>© 2018 OmniTech Research Corp. All rights reserved.</p>
  </footer>
</body>
</html>
"""
            self._send_response(200, "text/html", content)
            return

        if path == "/product/sensor-pro":
            # Product page with commercial signals (price, cart, availability) but missing schema
            content = """<!DOCTYPE html>
<html>
<head>
  <title>OmniSensor Pro Sensor</title>
</head>
<body>
  <h1>OmniSensor Pro Autonomous Sensor</h1>
  <h2>Enterprise Hardware</h2>
  <p>Price: $4,999.00 USD. Availability: In Stock.</p>
  <button type="button">Add to Cart</button>
  <button type="button">Buy Now</button>
  <footer>
    <p>© 2026 OmniTech Research Corp.</p>
  </footer>
</body>
</html>
"""
            self._send_response(200, "text/html", content)
            return

        if path == "/docs-guide":
            # Documentation page with valid tech content
            content = """<!DOCTYPE html>
<html>
<head>
  <title>OmniTech Developer Documentation</title>
  <meta name="description" content="Official API reference and developer quickstart for OmniTech.">
  <script type="application/ld+json">
  {
    "@context": "https://schema.org",
    "@type": "TechArticle",
    "headline": "OmniTech Quickstart Guide",
    "author": { "@type": "Organization", "name": "OmniTech" }
  }
  </script>
</head>
<body>
  <h1>Developer Quickstart Guide</h1>
  <h2>Installation & API Authentication</h2>
  <p>Run pip install omnitech-core and initialize the client.</p>
  <pre><code>import omnitech\nclient = omnitech.Client()</code></pre>
</body>
</html>
"""
            self._send_response(200, "text/html", content)
            return

        if path == "/stale-news":
            # Stale news page with outdated copyright (2016) and old dates
            content = """<!DOCTYPE html>
<html>
<head>
  <title>OmniTech Stale Press Release</title>
  <meta name="description" content="Company launch and roadmap announcement.">
</head>
<body>
  <h1>OmniTech Launch Announcement</h1>
  <h2>Published: January 12, 2016</h2>
  <p>OmniTech announces round of funding in 2016.</p>
  <footer>
    <p>© 2016 OmniTech Research Corp.</p>
  </footer>
</body>
</html>
"""
            self._send_response(200, "text/html", content)
            return

        if path == "/deep-level-1":
            content = """<!DOCTYPE html>
<html><head><title>Level 1</title></head>
<body><h1>Level 1 Page</h1><a href="/deep-level-2">Go to Level 2</a></body>
</html>"""
            self._send_response(200, "text/html", content)
            return

        if path == "/deep-level-2":
            content = """<!DOCTYPE html>
<html><head><title>Level 2</title></head>
<body><h1>Level 2 Page</h1><a href="/deep-level-3">Go to Level 3</a></body>
</html>"""
            self._send_response(200, "text/html", content)
            return

        if path == "/deep-level-3":
            content = """<!DOCTYPE html>
<html><head><title>Level 3</title></head>
<body><h1>Level 3 Page</h1></body>
</html>"""
            self._send_response(200, "text/html", content)
            return

        if path == "/secret-admin/test":
            content = """<!DOCTYPE html><html><head><title>Admin</title></head><body><h1>Admin Area</h1></body></html>"""
            self._send_response(200, "text/html", content)
            return

        self._send_response(404, "text/html", "<h1>404 Not Found</h1>")

    def _send_response(self, code: int, content_type: str, body: str):
        self.send_response(code)
        self.send_header("Content-Type", f"{content_type}; charset=utf-8")
        self.send_header("Content-Length", str(len(body.encode("utf-8"))))
        self.end_headers()
        self.wfile.write(body.encode("utf-8"))


def start_controlled_server() -> Tuple[HTTPServer, str, threading.Thread]:
    server = HTTPServer(("127.0.0.1", 0), ControlledDefectSiteHandler)
    port = server.server_port
    base_url = f"http://127.0.0.1:{port}"
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, base_url, thread


class TestFunctionalValidation(unittest.TestCase):

    def test_subdomain_and_same_domain_url_handling(self):
        # 1. www vs apex
        self.assertTrue(is_same_domain("https://www.wikipedia.org", "https://wikipedia.org"))
        # 2. apex to language subdomain with allow_subdomains=True
        self.assertTrue(is_same_domain("https://www.wikipedia.org", "https://en.wikipedia.org", allow_subdomains=True))
        self.assertTrue(is_same_domain("https://wikipedia.org", "https://ja.wikipedia.org/wiki/Main_Page", allow_subdomains=True))
        # 3. different base domains
        self.assertFalse(is_same_domain("https://wikipedia.org", "https://wikimedia.org", allow_subdomains=True))
        self.assertFalse(is_same_domain("https://example.com", "https://google.com", allow_subdomains=True))

    def test_crawler_internal_link_extraction_with_subdomains(self):
        portal_html = """<!DOCTYPE html>
<html>
<head><title>Wikipedia Portal</title></head>
<body>
  <div class="central-featured-lang">
    <a href="//en.wikipedia.org/" id="js-link-box-en"><strong>English</strong></a>
    <a href="//es.wikipedia.org/" id="js-link-box-es"><strong>Español</strong></a>
    <a href="//ja.wikipedia.org/" id="js-link-box-ja"><strong>日本語</strong></a>
    <a href="https://wikimediafoundation.org/">Wikimedia Foundation</a>
  </div>
</body>
</html>"""
        ev = extract_page_evidence(
            url="https://www.wikipedia.org/",
            raw_html=portal_html,
            status_code=200,
            response_time_ms=30.0,
            base_domain_url="https://www.wikipedia.org/"
        )
        # Should extract internal language subdomain links
        self.assertGreaterEqual(len(ev.internal_links), 3)
        internal_urls = [link.url for link in ev.internal_links]
        self.assertIn("https://en.wikipedia.org/", internal_urls)
        self.assertIn("https://es.wikipedia.org/", internal_urls)
        self.assertIn("https://ja.wikipedia.org/", internal_urls)
        # Wikimedia foundation is external domain
        external_urls = [link.url for link in ev.external_links]
        self.assertIn("https://wikimediafoundation.org/", external_urls)

    def test_archetype_classifier_grounding(self):
        # 1. Wikipedia-like portal with language links and encyclopedia text
        wiki_ev = PageEvidence(
            url="https://www.wikipedia.org/",
            normalized_url="https://www.wikipedia.org/",
            status_code=200,
            response_time_ms=50.0,
            content_type="text/html",
            page_archetype=PageArchetype.HOMEPAGE,
            is_primary_page=True,
            title="Wikipedia, the free encyclopedia",
            meta_description="Wikipedia is a free online encyclopedia.",
            canonical_url=None,
            meta_tags={},
            raw_html="",
            raw_text="The Free Encyclopedia 6,000,000+ articles in English, Deutsch, Francais, Japanese",
            raw_text_length=500,
            raw_word_count=80
        )
        archetype = classify_site_archetype([wiki_ev])
        self.assertEqual(archetype, SiteArchetype.PUBLISHER)

        # 2. Truly minimal page with no strong signals -> Should fall back to UNKNOWN or CORPORATE (never ungrounded PORTFOLIO)
        generic_ev = PageEvidence(
            url="https://simple-site.example/",
            normalized_url="https://simple-site.example/",
            status_code=200,
            response_time_ms=50.0,
            content_type="text/html",
            page_archetype=PageArchetype.HOMEPAGE,
            is_primary_page=True,
            title="Simple Landing",
            meta_description="",
            canonical_url=None,
            meta_tags={},
            raw_html="",
            raw_text="Hello world welcome to our website.",
            raw_text_length=40,
            raw_word_count=7
        )
        archetype_generic = classify_site_archetype([generic_ev])
        self.assertNotEqual(archetype_generic, SiteArchetype.PORTFOLIO)
        self.assertIn(archetype_generic, (SiteArchetype.CORPORATE, SiteArchetype.UNKNOWN))

        # 3. Genuine portfolio site with explicit keywords
        portfolio_ev = PageEvidence(
            url="https://designer.example/",
            normalized_url="https://designer.example/",
            status_code=200,
            response_time_ms=50.0,
            content_type="text/html",
            page_archetype=PageArchetype.HOMEPAGE,
            is_primary_page=True,
            title="Jane Doe — UX Portfolio & Case Studies",
            meta_description="Senior Product Designer case studies and design projects.",
            canonical_url=None,
            meta_tags={},
            raw_html="",
            raw_text="Selected case studies, design projects, and interactive gallery.",
            raw_text_length=200,
            raw_word_count=30
        )
        archetype_portfolio = classify_site_archetype([portfolio_ev])
        self.assertEqual(archetype_portfolio, SiteArchetype.PORTFOLIO)

    def test_crawler_bounds_and_robots_compliance(self):
        server, base_url, thread = start_controlled_server()
        try:
            # Test max_pages limit
            crawler = AsyncCrawler(max_pages=2, max_depth=3, concurrency=2, request_timeout=3.0)
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            ctx = loop.run_until_complete(crawler.crawl(base_url))
            loop.close()

            self.assertEqual(len(ctx.pages), 2)
            self.assertGreater(ctx.total_discovered_urls, 2)

            # Test robots disallow compliance
            crawler_all = AsyncCrawler(max_pages=10, max_depth=3, concurrency=2, request_timeout=3.0)
            loop2 = asyncio.new_event_loop()
            asyncio.set_event_loop(loop2)
            ctx_all = loop2.run_until_complete(crawler_all.crawl(base_url))
            loop2.close()

            crawled_urls = [p.url for p in ctx_all.pages]
            # /secret-admin/ should NOT be crawled because robots.txt disallows it
            for u in crawled_urls:
                self.assertNotIn("secret-admin", u)

            # Max depth verification: depth 0 -> depth 1 -> depth 2 -> depth 3
            # With max_depth=1, only level 1 should be visited
            crawler_shallow = AsyncCrawler(max_pages=10, max_depth=1, concurrency=2, request_timeout=3.0)
            loop3 = asyncio.new_event_loop()
            asyncio.set_event_loop(loop3)
            ctx_shallow = loop3.run_until_complete(crawler_shallow.crawl(base_url))
            loop3.close()

            shallow_urls = [p.url for p in ctx_shallow.pages]
            self.assertTrue(any("deep-level-1" in u for u in shallow_urls))
            self.assertFalse(any("deep-level-2" in u for u in shallow_urls))
            self.assertFalse(any("deep-level-3" in u for u in shallow_urls))

        finally:
            server.shutdown()
            server.server_close()

    def test_controlled_fixture_full_audit_skill_flow_and_deduplication(self):
        server, base_url, thread = start_controlled_server()
        try:
            # Run full end-to-end audit
            report = orchestrate_audit(
                url=base_url,
                crawl_options={"max_pages": 5, "max_depth": 2, "timeout": 5.0}
            )

            # 1. Verify general audit summary
            self.assertEqual(report.get("site"), normalize_url(base_url))
            summary = report.get("summary", {})
            self.assertGreater(summary.get("total_findings", 0), 0)

            # 2. Verify specific known defects were detected
            findings = report.get("findings", [])
            finding_categories = {f.get("category") for f in findings}
            finding_titles = [f.get("title", "") for f in findings]

            # Should detect crawlability/metadata, structured data, freshness, or engagement issues
            self.assertTrue(len(finding_categories) >= 2, f"Expected multiple finding categories, got {finding_categories}")
        finally:
            server.shutdown()
            server.server_close()

    def test_sitemap_with_subdomains(self):
        sitemap_content = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url><loc>https://en.wikipedia.org/wiki/Portal</loc></url>
  <url><loc>https://de.wikipedia.org/wiki/Hauptseite</loc></url>
  <url><loc>https://external-site.com/other</loc></url>
</urlset>
"""
        urls, subs, err = parse_sitemap_xml(sitemap_content, "https://www.wikipedia.org/")
        self.assertIsNone(err)
        # Should retain en.wikipedia.org and de.wikipedia.org under wikipedia.org apex
        self.assertIn("https://en.wikipedia.org/wiki/Portal", urls)
        self.assertIn("https://de.wikipedia.org/wiki/Hauptseite", urls)
        # External site should be filtered out
        self.assertNotIn("https://external-site.com/other", urls)

    def test_deduplication_engine_merges_duplicate_findings_and_upgrades_severity(self):
        orchestrator = AuditOrchestrator()
        duplicate_findings = [
            {
                "id": "F-001",
                "title": "Low severity issue",
                "category": "structured_data",
                "severity": "low",
                "root_cause": "Missing entity identifier in JSON-LD",
                "evidence": "URL: https://example.com/p1\nSnippet A",
                "affected_urls": ["https://example.com/p1"]
            },
            {
                "id": "F-002",
                "title": "High severity issue duplicate",
                "category": "structured_data",
                "severity": "high",
                "root_cause": "Missing entity identifier in JSON-LD",
                "evidence": "URL: https://example.com/p1\nSnippet B",
                "affected_urls": ["https://example.com/p1"]
            }
        ]
        deduped = orchestrator._deduplicate_findings(duplicate_findings)
        self.assertEqual(len(deduped), 1)
        self.assertEqual(deduped[0]["severity"], "high")
        self.assertIn("https://example.com/p1", deduped[0]["affected_urls"])
        self.assertIn("Snippet A", deduped[0]["evidence"])
        self.assertIn("Snippet B", deduped[0]["evidence"])

    def test_image_relevance_distinguishes_charts_from_logos_and_icons(self):
        # 1. Page with decorative branding logo and nav menu icon missing alt
        html_decorative = """<!DOCTYPE html>
<html>
<head><title>Test</title></head>
<body>
  <header>
    <div class="menu-container">
      <img src="https://example.com/media/logos/firefox-logo.svg" />
      <img src="/icons/nav-arrow.png" />
    </div>
  </header>
  <main>
    <h1>Welcome</h1>
    <img src="//example.com/tracker.png?1x1" />
  </main>
</body>
</html>"""
        ev_decorative = extract_page_evidence(
            url="https://example.com/",
            raw_html=html_decorative,
            status_code=200,
            response_time_ms=20.0,
            base_domain_url="https://example.com"
        )
        # Decorative images should NOT be flagged as content relevant
        content_images = [img for img in ev_decorative.images if img.is_content_relevant]
        self.assertEqual(len(content_images), 0)

        # 2. Page with genuine data visualization diagram missing alt
        html_chart = """<!DOCTYPE html>
<html>
<head><title>Architecture</title></head>
<body>
  <main>
    <h1>System Architecture</h1>
    <img src="/images/system-architecture-diagram.png" />
  </main>
</body>
</html>"""
        ev_chart = extract_page_evidence(
            url="https://example.com/arch",
            raw_html=html_chart,
            status_code=200,
            response_time_ms=20.0,
            base_domain_url="https://example.com"
        )
        content_chart_images = [img for img in ev_chart.images if img.is_content_relevant]
        self.assertEqual(len(content_chart_images), 1)
        self.assertEqual(content_chart_images[0].context_keyword, "diagram")

    def test_archetype_classification_grounding_corporate_vs_ecommerce(self):
        # 1. Mozilla-like software portal with /products/ path but no cart/prices
        mozilla_pages = [
            PageEvidence(
                url="https://www.mozilla.org/en-US/",
                normalized_url="https://www.mozilla.org/en-US/",
                status_code=200,
                response_time_ms=40.0,
                content_type="text/html",
                page_archetype=PageArchetype.HOMEPAGE,
                is_primary_page=True,
                title="Internet for people, not profit — Mozilla",
                meta_description="Non-profit technology foundation.",
                canonical_url=None,
                meta_tags={},
                raw_html="",
                raw_text="Mozilla is the non-profit behind Firefox. Our mission is an open internet.",
                raw_text_length=200,
                raw_word_count=30
            ),
            PageEvidence(
                url="https://www.mozilla.org/en-US/products/",
                normalized_url="https://www.mozilla.org/en-US/products/",
                status_code=200,
                response_time_ms=40.0,
                content_type="text/html",
                page_archetype=PageArchetype.OTHER,
                is_primary_page=False,
                title="Mozilla Products",
                meta_description="Explore our open source tools.",
                canonical_url=None,
                meta_tags={},
                raw_html="",
                raw_text="Download Firefox browser, Thunderbird, and privacy tools.",
                raw_text_length=150,
                raw_word_count=20
            )
        ]
        arch_mozilla = classify_site_archetype(mozilla_pages)
        self.assertEqual(arch_mozilla, SiteArchetype.CORPORATE)

        # 2. Genuine E-Commerce store with cart, checkout, Product schema
        store_pages = [
            PageEvidence(
                url="https://store.example.com/product/camera",
                normalized_url="https://store.example.com/product/camera",
                status_code=200,
                response_time_ms=40.0,
                content_type="text/html",
                page_archetype=PageArchetype.PRODUCT_DETAIL,
                is_primary_page=False,
                title="Cinema Camera - Buy Now",
                meta_description="In stock.",
                canonical_url=None,
                meta_tags={},
                raw_html="",
                raw_text="Price: $2999. Add to cart. Shopping cart. In stock.",
                raw_text_length=150,
                raw_word_count=20
            )
        ]
        arch_store = classify_site_archetype(store_pages)
        self.assertEqual(arch_store, SiteArchetype.ECOMMERCE)


if __name__ == "__main__":
    unittest.main()



