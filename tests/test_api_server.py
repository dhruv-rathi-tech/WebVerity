"""
Integration Test Suite: FastAPI Server & Audit Service
Tests REST endpoints: /api/health, /api/audit, /api/audit/{id}, /api/audit/{id}/report.
"""

import os
import sys
import unittest
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from server.main import app
from server.services.audit_service import audit_service
from core.models import CrawlContext, PageEvidence, SiteArchetype, PageArchetype, RobotsPolicy, SitemapSummary


class TestApiServer(unittest.TestCase):

    def setUp(self):
        self.client = TestClient(app)

    def test_health_endpoint(self):
        response = self.client.get("/api/health")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "healthy")
        self.assertEqual(data["version"], "1.0.0")
        self.assertIn("services", data)
        self.assertEqual(data["services"]["orchestrator"], "ready")

    def test_audit_endpoint_invalid_url(self):
        response = self.client.post("/api/audit", json={"url": "not-a-valid-url"})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["summary"]["total_findings"], 0)
        self.assertEqual(data["site"], "not-a-valid-url")

    def test_audit_endpoint_empty_url(self):
        response = self.client.post("/api/audit", json={"url": ""})
        self.assertEqual(response.status_code, 400)

    def test_audit_end_to_end_mocked(self):
        # Test audit flow with mocked crawler
        mock_page = PageEvidence(
            url="https://api-test.example.com/",
            normalized_url="https://api-test.example.com/",
            status_code=200,
            response_time_ms=12.5,
            content_type="text/html",
            page_archetype=PageArchetype.HOMEPAGE,
            is_primary_page=True,
            title="API Test Home",
            meta_description="Testing the API server",
            canonical_url="https://api-test.example.com/",
            meta_tags={},
            raw_html="<h1>API Test</h1><p>Welcome</p>",
            raw_text="API Test Welcome",
            raw_text_length=16,
            raw_word_count=3
        )
        mock_ctx = CrawlContext(
            root_url="https://api-test.example.com/",
            domain="api-test.example.com",
            audited_at="2026-09-27T12:00:00Z",
            site_archetype=SiteArchetype.CORPORATE,
            robots_policy=RobotsPolicy(exists=True, url="https://api-test.example.com/robots.txt", raw_content="User-agent: *\nAllow: /"),
            sitemap_summary=SitemapSummary(exists=False),
            pages=[mock_page]
        )

        with patch("server.services.audit_service.crawl_site", new_callable=AsyncMock) as mock_crawl:
            mock_crawl.return_value = mock_ctx
            
            response = self.client.post("/api/audit", json={"url": "https://api-test.example.com/"})
            self.assertEqual(response.status_code, 200)
            data = response.json()

            self.assertIn("id", data)
            self.assertEqual(data["site"], "https://api-test.example.com/")
            self.assertEqual(data["site_archetype"], "corporate")
            self.assertEqual(data["pages_audited"], 1)
            self.assertIn("summary", data)
            self.assertIn("findings", data)
            self.assertIn("pages", data)
            self.assertEqual(len(data["pages"]), 1)
            self.assertEqual(data["pages"][0]["title"], "API Test Home")

            audit_id = data["id"]

            # Test GET /api/audit/{audit_id}
            get_resp = self.client.get(f"/api/audit/{audit_id}")
            self.assertEqual(get_resp.status_code, 200)
            get_data = get_resp.json()
            self.assertEqual(get_data["id"], audit_id)

            # Test GET /api/audit/{audit_id}/report
            rep_resp = self.client.get(f"/api/audit/{audit_id}/report")
            self.assertEqual(rep_resp.status_code, 200)
            self.assertIn("# WebVerity - AI Readiness & Website Intelligence Report", rep_resp.text)

    def test_get_nonexistent_audit(self):
        response = self.client.get("/api/audit/nonexistent-id-999")
        self.assertEqual(response.status_code, 404)


if __name__ == "__main__":
    unittest.main()
