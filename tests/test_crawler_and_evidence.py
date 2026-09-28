"""
Test Suite: Crawl & Evidence Foundation
Verifies robots.txt parsing, sitemap discovery, URL prioritization,
evidence extraction, archetype classification, and mock server integration.
"""

import asyncio
import unittest
from core.url_utils import normalize_url, extract_domain, is_same_domain, is_crawlable_web_url
from core.robots import parse_robots_txt, is_path_allowed_for_bot
from core.sitemap import parse_sitemap_xml
from core.extractor import extract_page_evidence
from core.classifier import classify_page_archetype, classify_site_archetype
from core.models import SiteArchetype, PageArchetype, PageEvidence
from core.crawler import AsyncCrawler
from tests.fixtures.mock_server import start_mock_server


class TestCrawlAndEvidenceFoundation(unittest.TestCase):

    def test_url_normalization(self):
        self.assertEqual(
            normalize_url("HTTP://Example.COM:80/path//subpath/?utm_source=twitter&b=2&a=1#section"),
            "http://example.com/path/subpath/?a=1&b=2"
        )
        self.assertEqual(
            normalize_url("/product/pro-camera", "https://example.com/shop/"),
            "https://example.com/product/pro-camera"
        )
        self.assertTrue(is_same_domain("https://example.com", "https://www.example.com"))
        self.assertFalse(is_same_domain("https://example.com", "https://other.com"))
        self.assertFalse(is_crawlable_web_url("https://example.com/image.png"))
        self.assertTrue(is_crawlable_web_url("https://example.com/product/camera"))

    def test_robots_txt_parsing(self):
        sample_robots = """User-agent: *
Disallow: /admin/
Disallow: /checkout/

User-agent: GPTBot
Disallow: /internal/

User-agent: PerplexityBot
Allow: /

Sitemap: https://example.com/sitemap.xml
"""
        policy = parse_robots_txt("https://example.com/robots.txt", sample_robots)
        self.assertTrue(policy.exists)
        self.assertEqual(policy.sitemap_urls, ["https://example.com/sitemap.xml"])
        
        # Test generic bot rules
        self.assertTrue(is_path_allowed_for_bot(policy, "/", "*"))
        self.assertFalse(is_path_allowed_for_bot(policy, "/admin/dashboard", "*"))
        self.assertFalse(is_path_allowed_for_bot(policy, "/checkout/cart", "*"))

        # Test specific AI bot rules
        self.assertFalse(is_path_allowed_for_bot(policy, "/internal/docs", "GPTBot"))
        self.assertTrue(is_path_allowed_for_bot(policy, "/admin/test", "PerplexityBot"))

    def test_sitemap_xml_parsing(self):
        sample_sitemap = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url><loc>https://example.com/product/camera</loc></url>
  <url><loc>https://example.com/pricing</loc></url>
  <url><loc>https://other-domain.com/hack</loc></url>
</urlset>
"""
        page_urls, sub_sitemaps, error = parse_sitemap_xml(sample_sitemap, "https://example.com")
        self.assertIsNone(error)
        self.assertEqual(len(page_urls), 2)
        self.assertIn("https://example.com/product/camera", page_urls)
        self.assertIn("https://example.com/pricing", page_urls)
        # Out of domain link should be filtered out
        self.assertNotIn("https://other-domain.com/hack", page_urls)

    def test_page_evidence_extraction(self):
        sample_html = """<!DOCTYPE html>
<html>
<head>
  <title>Apex 8K Camera</title>
  <meta name="description" content="Cinematic 8K sensor.">
  <link rel="canonical" href="https://example.com/product/camera">
  <script type="application/ld+json">
  {
    "@context": "https://schema.org",
    "@type": "Product",
    "name": "Apex 8K",
    "offers": {
      "@type": "Offer",
      "price": "3999.00",
      "priceCurrency": "USD"
    }
  }
  </script>
</head>
<body>
  <h1>Apex 8K Camera</h1>
  <h2>Technical Specifications</h2>
  <p>Dual native ISO with 16 stops dynamic range.</p>
  <img src="/images/camera-specs.png" alt="Full Dimension Chart" />
  <img src="/images/icon.png" alt="" />
  <a href="/pricing">View Packages</a>
  <a href="https://twitter.com/apexdynamics" rel="noopener">Follow us</a>
  <footer>
    <p>© 2026 Apex Dynamics Inc.</p>
  </footer>
</body>
</html>"""
        ev = extract_page_evidence(
            url="https://example.com/product/camera",
            raw_html=sample_html,
            status_code=200,
            response_time_ms=45.2,
            base_domain_url="https://example.com"
        )
        self.assertEqual(ev.title, "Apex 8K Camera")
        self.assertEqual(ev.meta_description, "Cinematic 8K sensor.")
        self.assertEqual(ev.canonical_url, "https://example.com/product/camera")
        self.assertEqual(len(ev.json_ld), 1)
        self.assertIn("Product", ev.json_ld[0].schema_types)
        self.assertIn("Offer", ev.json_ld[0].schema_types)
        self.assertEqual(len(ev.heading_tree), 2)
        self.assertEqual(ev.heading_tree[0].tag, "h1")
        self.assertEqual(ev.heading_tree[1].tag, "h2")
        self.assertEqual(len(ev.internal_links), 1)
        self.assertEqual(len(ev.external_links), 1)
        self.assertEqual(ev.extracted_dates.get("copyright_year"), "2026")
        self.assertTrue(ev.raw_word_count > 5)

    def test_archetype_classification(self):
        # Product Page
        product_ev = PageEvidence(
            url="https://example.com/product/pro-camera",
            normalized_url="https://example.com/product/pro-camera",
            status_code=200,
            response_time_ms=50.0,
            content_type="text/html",
            page_archetype=PageArchetype.OTHER,
            is_primary_page=False,
            title="Pro Camera",
            meta_description="",
            canonical_url=None,
            meta_tags={},
            raw_html="",
            raw_text="Add to cart price $3999 in stock",
            raw_text_length=35,
            raw_word_count=7
        )
        classified_page = classify_page_archetype(product_ev, is_root=False)
        self.assertEqual(classified_page, PageArchetype.PRODUCT_DETAIL)

        # Site Archetype Classification
        site_archetype = classify_site_archetype([product_ev])
        self.assertEqual(site_archetype, SiteArchetype.ECOMMERCE)

    def test_async_crawler_on_mock_server(self):
        server, base_url, thread = start_mock_server()
        try:
            crawler = AsyncCrawler(max_pages=10, max_depth=2, concurrency=3, request_timeout=5.0)
            
            # Run crawl asynchronously
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            crawl_context = loop.run_until_complete(crawler.crawl(base_url))
            loop.close()

            # Assertions
            self.assertEqual(crawl_context.domain, "127.0.0.1")
            self.assertTrue(crawl_context.robots_policy.exists)
            self.assertTrue(crawl_context.sitemap_summary.exists)
            self.assertGreater(len(crawl_context.pages), 3)
            self.assertEqual(crawl_context.site_archetype, SiteArchetype.ECOMMERCE)
            self.assertTrue(crawl_context.crawl_duration_seconds > 0)
            self.assertEqual(len(crawl_context.crawl_errors), 0)

            # Check that root was classified as homepage
            home_page = next((p for p in crawl_context.pages if p.page_archetype == PageArchetype.HOMEPAGE), None)
            self.assertIsNotNone(home_page)
            self.assertTrue(home_page.is_primary_page)

            # Check that product page extracted JSON-LD correctly
            product_page = next((p for p in crawl_context.pages if "product" in p.url), None)
            self.assertIsNotNone(product_page)
            self.assertEqual(product_page.page_archetype, PageArchetype.PRODUCT_DETAIL)
            self.assertGreater(len(product_page.json_ld), 0)
            self.assertIn("Product", product_page.json_ld[0].schema_types)

        finally:
            server.shutdown()
            server.server_close()


if __name__ == "__main__":
    unittest.main()
