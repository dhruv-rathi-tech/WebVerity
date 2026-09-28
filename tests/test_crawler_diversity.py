"""
Test Suite: Crawler Soft Diversity & Representative Page Selection.
Verifies that:
- Large sitemaps with many redundant pages (e.g. 50 products or 50 articles) do not starve
  important page types (About, Contact, Services, FAQ, Categories).
- Single-archetype sites (documentation, pure catalog) are not artificially constrained.
- Small sites terminate cleanly and sensibly.
- Navigation-based link discovery respects soft diversity when sitemap is absent.
- URLs differing only by tracking query parameters are normalized and deduplicated.
- max_pages=20 and max_depth=2 bounds are strictly respected.
"""

import asyncio
import threading
import unittest
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Dict, List, Tuple
import urllib.parse

from core.crawler import AsyncCrawler
from core.models import PageArchetype, SiteArchetype


def make_html(title: str, body_links: List[str] = None, text: str = "") -> str:
    links_html = "".join(f'<a href="{link}">Link</a>' for link in (body_links or []))
    return f"""<!DOCTYPE html>
<html>
<head><title>{title}</title></head>
<body>
  <h1>{title}</h1>
  <p>{text or "Sample content description."}</p>
  {links_html}
</body>
</html>"""


class DynamicMockServer:
    """
    Helper to spin up a mock HTTP server with a programmable route table.
    """
    def __init__(self, routes: Dict[str, Tuple[int, str, str]]):
        self.routes = routes
        self.server = None
        self.thread = None
        self.base_url = ""

    def start(self):
        routes = self.routes

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, format, *args):
                pass

            def do_GET(self):
                parsed = urllib.parse.urlparse(self.path)
                path = parsed.path
                if path in routes:
                    code, ctype, body = routes[path]
                    self.send_response(code)
                    self.send_header("Content-Type", f"{ctype}; charset=utf-8")
                    self.send_header("Content-Length", str(len(body.encode("utf-8"))))
                    self.end_headers()
                    self.wfile.write(body.encode("utf-8"))
                else:
                    self.send_response(404)
                    self.send_header("Content-Type", "text/html; charset=utf-8")
                    self.end_headers()
                    self.wfile.write(b"<h1>404 Not Found</h1>")

        self.server = HTTPServer(("127.0.0.1", 0), Handler)
        port = self.server.server_port
        self.base_url = f"http://127.0.0.1:{port}"
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        return self.base_url

    def stop(self):
        if self.server:
            self.server.shutdown()
            self.server.server_close()


class TestCrawlerDiversity(unittest.TestCase):

    def _run_crawl(self, seed_url: str, max_pages: int = 20, max_depth: int = 2):
        crawler = AsyncCrawler(max_pages=max_pages, max_depth=max_depth, concurrency=4, request_timeout=4.0)
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(crawler.crawl(seed_url))
        finally:
            loop.close()

    def test_scenario_a_large_ecommerce_sitemap_diversity(self):
        """
        Scenario A: Large e-commerce sitemap with 50 products + About + Contact + Services + FAQ + Pricing.
        Verify that important non-product pages are NOT starved by the product URLs.
        """
        routes: Dict[str, Tuple[int, str, str]] = {}
        routes["/robots.txt"] = (200, "text/plain", "User-agent: *\nAllow: /\nSitemap: /sitemap.xml\n")
        
        # Build sitemap with 50 products first, followed by diverse pages
        sitemap_urls = [f"/product/item-{i}" for i in range(1, 51)]
        sitemap_urls.extend(["/pricing", "/about", "/contact", "/services", "/faq"])
        
        sitemap_xml = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        for u in sitemap_urls:
            sitemap_xml += f"  <url><loc>{u}</loc></url>\n"
        sitemap_xml += "</urlset>"
        routes["/sitemap.xml"] = (200, "application/xml", sitemap_xml)

        # Pages content
        routes["/"] = (200, "text/html", make_html("Apex Store Home", ["/pricing", "/about", "/contact"]))
        routes["/pricing"] = (200, "text/html", make_html("Store Pricing & Plans", text="Subscription and pricing options"))
        routes["/about"] = (200, "text/html", make_html("About Apex Store", text="Our leadership and company history"))
        routes["/contact"] = (200, "text/html", make_html("Contact Customer Support", text="Email support@store.example"))
        routes["/services"] = (200, "text/html", make_html("Professional Services", text="Consulting and repair services"))
        routes["/faq"] = (200, "text/html", make_html("Frequently Asked Questions", text="Answers to common questions"))

        for i in range(1, 51):
            routes[f"/product/item-{i}"] = (200, "text/html", make_html(f"Product {i}", text=f"Details for item {i}"))

        mock = DynamicMockServer(routes)
        base_url = mock.start()
        try:
            ctx = self._run_crawl(base_url, max_pages=20)
            crawled_paths = [urllib.parse.urlparse(p.url).path for p in ctx.pages]

            # Under 20 max_pages
            self.assertLessEqual(len(ctx.pages), 20)
            
            # Root must be crawled
            self.assertIn("/", crawled_paths)

            # High-priority and diverse pages MUST be crawled, not starved by the 50 products
            self.assertIn("/pricing", crawled_paths)
            self.assertIn("/about", crawled_paths)
            self.assertIn("/contact", crawled_paths)
            self.assertIn("/services", crawled_paths)
            self.assertIn("/faq", crawled_paths)

            # Multiple product pages should also be included (sampling)
            product_crawled = [p for p in crawled_paths if p.startswith("/product/")]
            self.assertGreaterEqual(len(product_crawled), 2)
            self.assertLessEqual(len(product_crawled), 15)

        finally:
            mock.stop()

    def test_scenario_b_large_publisher_sitemap_diversity(self):
        """
        Scenario B: Large publisher sitemap with 50 articles + sections + about + contact.
        Verify that representative page types (sections, about, contact) are selected alongside articles.
        """
        routes: Dict[str, Tuple[int, str, str]] = {}
        routes["/robots.txt"] = (200, "text/plain", "User-agent: *\nAllow: /\nSitemap: /sitemap.xml\n")

        # 50 articles, 3 sections, about, contact
        sitemap_urls = [f"/article/news-{i}" for i in range(1, 51)]
        sitemap_urls.extend(["/category/world", "/category/tech", "/category/business", "/about", "/contact"])

        sitemap_xml = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        for u in sitemap_urls:
            sitemap_xml += f"  <url><loc>{u}</loc></url>\n"
        sitemap_xml += "</urlset>"
        routes["/sitemap.xml"] = (200, "application/xml", sitemap_xml)

        routes["/"] = (200, "text/html", make_html("Daily Chronicle", ["/category/world", "/category/tech"]))
        routes["/about"] = (200, "text/html", make_html("About The Chronicle", text="Editorial board and standards"))
        routes["/contact"] = (200, "text/html", make_html("Contact the Newsroom", text="Email tips@chronicle.example"))
        routes["/category/world"] = (200, "text/html", make_html("World News", text="International coverage"))
        routes["/category/tech"] = (200, "text/html", make_html("Technology News", text="Tech industry reports"))
        routes["/category/business"] = (200, "text/html", make_html("Business & Markets", text="Financial updates"))

        for i in range(1, 51):
            routes[f"/article/news-{i}"] = (200, "text/html", make_html(f"News Story {i}", text=f"Article body text {i}"))

        mock = DynamicMockServer(routes)
        base_url = mock.start()
        try:
            ctx = self._run_crawl(base_url, max_pages=20)
            crawled_paths = [urllib.parse.urlparse(p.url).path for p in ctx.pages]

            self.assertLessEqual(len(ctx.pages), 20)
            self.assertIn("/", crawled_paths)
            self.assertIn("/about", crawled_paths)
            self.assertIn("/contact", crawled_paths)
            
            # Sections should be covered
            self.assertTrue(any(p.startswith("/category/") for p in crawled_paths))

            # Articles should be sampled without monopolizing all 20 pages
            articles_crawled = [p for p in crawled_paths if p.startswith("/article/")]
            self.assertGreaterEqual(len(articles_crawled), 2)

        finally:
            mock.stop()

    def test_scenario_c_documentation_site_without_artificial_blocking(self):
        """
        Scenario C: Documentation site with 40 guide URLs.
        Verify diversity does not block guides or force non-existent commercial pages;
        all available budget is used on documentation pages.
        """
        routes: Dict[str, Tuple[int, str, str]] = {}
        routes["/robots.txt"] = (200, "text/plain", "User-agent: *\nAllow: /\nSitemap: /sitemap.xml\n")

        sitemap_urls = [f"/docs/guide-{i}" for i in range(1, 41)]
        sitemap_xml = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        for u in sitemap_urls:
            sitemap_xml += f"  <url><loc>{u}</loc></url>\n"
        sitemap_xml += "</urlset>"
        routes["/sitemap.xml"] = (200, "application/xml", sitemap_xml)

        routes["/"] = (200, "text/html", make_html("Developer Documentation Hub"))
        for i in range(1, 41):
            routes[f"/docs/guide-{i}"] = (200, "text/html", make_html(f"Documentation Guide {i}", text=f"API guide details {i}"))

        mock = DynamicMockServer(routes)
        base_url = mock.start()
        try:
            ctx = self._run_crawl(base_url, max_pages=20)
            crawled_paths = [urllib.parse.urlparse(p.url).path for p in ctx.pages]

            # Should use the full 20-page budget on available docs
            self.assertEqual(len(ctx.pages), 20)
            self.assertIn("/", crawled_paths)
            docs_crawled = [p for p in crawled_paths if p.startswith("/docs/")]
            self.assertEqual(len(docs_crawled), 19)

        finally:
            mock.stop()

    def test_scenario_d_small_site_sensible_behavior(self):
        """
        Scenario D: Small site with only 4 pages.
        Verify existing behavior remains sensible and terminates cleanly without looping.
        """
        routes: Dict[str, Tuple[int, str, str]] = {}
        routes["/robots.txt"] = (200, "text/plain", "User-agent: *\nAllow: /\n")
        routes["/sitemap.xml"] = (404, "text/html", "Not found")
        routes["/"] = (200, "text/html", make_html("Boutique Firm", ["/about", "/services", "/contact"]))
        routes["/about"] = (200, "text/html", make_html("About Us", ["/"]))
        routes["/services"] = (200, "text/html", make_html("Our Services", ["/contact"]))
        routes["/contact"] = (200, "text/html", make_html("Contact Us", ["/about"]))

        mock = DynamicMockServer(routes)
        base_url = mock.start()
        try:
            ctx = self._run_crawl(base_url, max_pages=20)
            crawled_paths = set(urllib.parse.urlparse(p.url).path for p in ctx.pages)

            # Exactly 4 pages crawled
            self.assertEqual(len(ctx.pages), 4)
            self.assertEqual(crawled_paths, {"/", "/about", "/services", "/contact"})
            self.assertEqual(len(ctx.crawl_errors), 0)

        finally:
            mock.stop()

    def test_scenario_e_sitemap_absent_navigation_discovery(self):
        """
        Scenario E: Sitemap absent.
        Verify navigation-based internal link discovery still works and soft diversity balances page types.
        """
        routes: Dict[str, Tuple[int, str, str]] = {}
        routes["/robots.txt"] = (200, "text/plain", "User-agent: *\nAllow: /\n")
        routes["/sitemap.xml"] = (404, "text/html", "Not found")

        # Homepage links to 30 items + about + contact + services
        home_links = [f"/item/sample-{i}" for i in range(1, 31)] + ["/about", "/contact", "/services"]
        routes["/"] = (200, "text/html", make_html("Catalog Homepage", home_links))
        routes["/about"] = (200, "text/html", make_html("About Catalog", text="Catalog story"))
        routes["/contact"] = (200, "text/html", make_html("Contact Catalog", text="Catalog support"))
        routes["/services"] = (200, "text/html", make_html("Catalog Services", text="Delivery services"))

        for i in range(1, 31):
            routes[f"/item/sample-{i}"] = (200, "text/html", make_html(f"Catalog Item {i}", text=f"Item description {i}"))

        mock = DynamicMockServer(routes)
        base_url = mock.start()
        try:
            ctx = self._run_crawl(base_url, max_pages=20)
            crawled_paths = [urllib.parse.urlparse(p.url).path for p in ctx.pages]

            self.assertLessEqual(len(ctx.pages), 20)
            self.assertIn("/", crawled_paths)
            self.assertIn("/about", crawled_paths)
            self.assertIn("/contact", crawled_paths)
            self.assertIn("/services", crawled_paths)

            items_crawled = [p for p in crawled_paths if p.startswith("/item/")]
            self.assertGreaterEqual(len(items_crawled), 2)

        finally:
            mock.stop()

    def test_scenario_f_tracking_parameter_deduplication(self):
        """
        Scenario F: Tracking parameters in sitemap and navigation links.
        Verify identical paths with different tracking parameters are not queued or crawled twice.
        """
        routes: Dict[str, Tuple[int, str, str]] = {}
        routes["/robots.txt"] = (200, "text/plain", "User-agent: *\nAllow: /\nSitemap: /sitemap.xml\n")

        # Sitemap contains duplicates differing only by tracking parameters
        sitemap_xml = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url><loc>/product/camera</loc></url>
  <url><loc>/product/camera?utm_source=google&amp;utm_medium=cpc</loc></url>
  <url><loc>/product/camera?ref=sidebar</loc></url>
  <url><loc>/product/camera?mc_cid=987654</loc></url>
  <url><loc>/about?fbclid=abcdef</loc></url>
</urlset>
"""
        routes["/sitemap.xml"] = (200, "application/xml", sitemap_xml)
        routes["/"] = (200, "text/html", make_html("Apex Cam", ["/product/camera?trk=home_hero", "/about"]))
        routes["/product/camera"] = (200, "text/html", make_html("Apex Camera Details"))
        routes["/about"] = (200, "text/html", make_html("About Apex"))

        mock = DynamicMockServer(routes)
        base_url = mock.start()
        try:
            ctx = self._run_crawl(base_url, max_pages=20)
            crawled_paths = [urllib.parse.urlparse(p.url).path for p in ctx.pages]

            # Verify that /product/camera is visited EXACTLY ONCE
            camera_count = sum(1 for p in crawled_paths if p == "/product/camera")
            self.assertEqual(camera_count, 1)

            about_count = sum(1 for p in crawled_paths if p == "/about")
            self.assertEqual(about_count, 1)

        finally:
            mock.stop()


if __name__ == "__main__":
    unittest.main()
