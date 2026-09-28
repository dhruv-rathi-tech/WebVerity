"""
In-process mock HTTP server providing realistic website fixtures for testing.
"""

from http.server import HTTPServer, BaseHTTPRequestHandler
import threading
import socket
from typing import Tuple


class MockSiteHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        # Suppress standard logging during tests
        pass

    def do_GET(self):
        path = self.path.split("?")[0]

        # Route table for mock fixtures
        if path == "/robots.txt":
            content = """User-agent: *
Allow: /
Disallow: /admin/
Disallow: /checkout/

User-agent: GPTBot
Disallow: /internal/

User-agent: PerplexityBot
Allow: /

Sitemap: /sitemap.xml
"""
            self._send_response(200, "text/plain", content)
            return

        if path == "/sitemap.xml":
            content = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url><loc>/product/pro-camera</loc><lastmod>2026-08-15</lastmod></url>
  <url><loc>/pricing</loc><lastmod>2026-08-20</lastmod></url>
  <url><loc>/about</loc><lastmod>2026-01-10</lastmod></url>
  <url><loc>/contact</loc><lastmod>2026-05-01</lastmod></url>
</urlset>
"""
            self._send_response(200, "application/xml", content)
            return

        if path in ("/", "/index.html"):
            content = """<!DOCTYPE html>
<html lang="en">
<head>
  <title>Apex Dynamics - Precision Camera Gear</title>
  <meta name="description" content="Leading manufacturer of high-end mirrorless camera systems and optical accessories.">
  <link rel="canonical" href="/index.html">
  <script type="application/ld+json">
  {
    "@context": "https://schema.org",
    "@type": "Organization",
    "name": "Apex Dynamics",
    "url": "http://localhost/",
    "sameAs": [
      "https://www.wikidata.org/wiki/Q12345",
      "https://linkedin.com/company/apexdynamics"
    ]
  }
  </script>
</head>
<body>
  <header>
    <h1>Apex Dynamics — Professional Optics & Cameras</h1>
    <nav>
      <a href="/product/pro-camera">Flagship Camera</a>
      <a href="/pricing">Pricing Plans</a>
      <a href="/about">About Us</a>
      <a href="/contact">Contact Support</a>
    </nav>
  </header>
  <main>
    <h2>Next-Generation Optical Clarity</h2>
    <p>We craft premium optical sensors for cinema professionals and photographers worldwide.</p>
    <img src="/images/hero-camera.jpg" alt="Apex 8K Cinema Camera Body" />
    <a href="/pricing" class="btn">Explore Products</a>
  </main>
  <footer>
    <p>© 2026 Apex Dynamics Inc. All rights reserved.</p>
  </footer>
</body>
</html>
"""
            self._send_response(200, "text/html", content)
            return

        if path == "/product/pro-camera":
            content = """<!DOCTYPE html>
<html>
<head>
  <title>Apex 8K Cinema Camera | Pro Gear</title>
  <meta name="description" content="Apex 8K Full-Frame Cinema Camera with dual native ISO and 16 stops of dynamic range.">
  <script type="application/ld+json">
  {
    "@context": "https://schema.org",
    "@type": "Product",
    "name": "Apex 8K Cinema Camera",
    "description": "Full-frame 8K cinema sensor.",
    "brand": { "@type": "Brand", "name": "Apex Dynamics" },
    "offers": {
      "@type": "Offer",
      "price": "3999.00",
      "priceCurrency": "USD",
      "availability": "https://schema.org/InStock"
    }
  }
  </script>
</head>
<body>
  <h1>Apex 8K Cinema Camera</h1>
  <h2>Uncompromising Sensor Performance</h2>
  <p>Price: $3,999.00 USD. Availability: In Stock.</p>
  <img src="/images/camera-specs-chart.png" alt="Detailed Technical Specifications and Dimension Chart" />
  <button type="button">Add to Cart</button>
  <a href="/contact">Request Studio Consultation</a>
</body>
</html>
"""
            self._send_response(200, "text/html", content)
            return

        if path == "/pricing":
            content = """<!DOCTYPE html>
<html>
<head>
  <title>Pricing & Packages | Apex Dynamics</title>
</head>
<body>
  <h1>Transparent Enterprise Pricing</h1>
  <h2>Standard and Cinema Studio Tiers</h2>
  <p>Standard Kit: $3,999 | Cinema Production Bundle: $7,499</p>
  <a href="/contact">Contact Sales</a>
</body>
</html>
"""
            self._send_response(200, "text/html", content)
            return

        if path == "/about":
            content = """<!DOCTYPE html>
<html>
<head>
  <title>About Apex Dynamics</title>
</head>
<body>
  <h1>Our Legacy of Optical Innovation</h1>
  <h2>Founded by Engineers in 2018</h2>
  <p>Apex Dynamics designs cinema-grade sensors trusted by major studios.</p>
  <a href="/contact">Get in touch with leadership</a>
</body>
</html>
"""
            self._send_response(200, "text/html", content)
            return

        if path == "/contact":
            content = """<!DOCTYPE html>
<html>
<head>
  <title>Contact Apex Dynamics</title>
</head>
<body>
  <h1>Contact Our Global Support Team</h1>
  <h2>We are here to assist with gear and service</h2>
  <p>Phone: +1-800-555-0199</p>
  <p>Email: support@apexdynamics.example</p>
  <p>Headquarters: 100 Optics Way, San Jose, CA</p>
</body>
</html>
"""
            self._send_response(200, "text/html", content)
            return

        if path == "/redirect-test":
            self.send_response(301)
            self.send_header("Location", "/product/pro-camera")
            self.end_headers()
            return

        if path == "/csr-shell":
            content = """<!DOCTYPE html>
<html>
<head><title>App Loading...</title></head>
<body>
  <div id="root"></div>
  <script src="/bundle.js"></script>
</body>
</html>"""
            self._send_response(200, "text/html", content)
            return

        # 404 handler
        self._send_response(404, "text/html", "<h1>404 Not Found</h1>")

    def _send_response(self, code: int, content_type: str, body: str):
        self.send_response(code)
        self.send_header("Content-Type", f"{content_type}; charset=utf-8")
        self.send_header("Content-Length", str(len(body.encode("utf-8"))))
        self.end_headers()
        self.wfile.write(body.encode("utf-8"))


def start_mock_server() -> Tuple[HTTPServer, str, threading.Thread]:
    """
    Starts an ephemeral HTTP server on localhost and returns (server, base_url, thread).
    """
    server = HTTPServer(("127.0.0.1", 0), MockSiteHandler)
    port = server.server_port
    base_url = f"http://127.0.0.1:{port}"
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, base_url, thread
