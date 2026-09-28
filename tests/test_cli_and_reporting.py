"""
Phase 10 Test Suite: CLI Invocation & Standardized Reporting.
Tests:
- CLI argument parsing and exit behavior
- Canonical entrypoint (audit / orchestrate)
- JSON output schema validation
- Human-readable Markdown output generation
- Output file writing (-o / --output)
- Graceful handling of malformed URLs, network failures, and skill exceptions
- Preservation of complete causal chain in rendered reports
- Separation of confirmed findings and proactive recommendations
- External corroboration file ingestion and graceful absence
"""

import os
import sys
import json
import tempfile
import unittest
from io import StringIO
from unittest.mock import patch

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from audit import main, orchestrate_audit, render_markdown_report, AuditOrchestrator
from tests.fixtures.eval_fixtures import get_all_eval_fixtures
from core.models import CrawlContext, PageEvidence, SiteArchetype, PageArchetype, RobotsPolicy, SitemapSummary


class TestCliAndReporting(unittest.TestCase):
    """
    Test suite for CLI entrypoint, argument parsing, JSON and Markdown rendering.
    """

    @classmethod
    def setUpClass(cls):
        cls.fixtures = get_all_eval_fixtures()
        # Load official report schema
        schema_path = os.path.join(_ROOT, "skills", "audit-orchestrator", "references", "report-schema.json")
        with open(schema_path, "r", encoding="utf-8") as f:
            cls.report_schema = json.load(f)

    def _validate_report_schema_strictly(self, report: dict):
        """
        Validates report against references/report-schema.json specification.
        """
        # Required top-level keys
        for key in ("site", "audited_at", "summary", "findings"):
            self.assertIn(key, report, f"Missing required top-level key '{key}'")

        # Summary structure
        summary = report["summary"]
        for sum_key in ("total_findings", "critical", "high", "medium"):
            self.assertIn(sum_key, summary, f"Summary missing required key '{sum_key}'")
            self.assertIsInstance(summary[sum_key], int)

        # Findings structure
        for f in report["findings"]:
            for req_f_key in ("id", "title", "severity", "evidence", "suggested_action"):
                self.assertIn(req_f_key, f, f"Finding missing required key '{req_f_key}'")
            self.assertIn(f["severity"], ("critical", "high", "medium", "low", "info"))
            self.assertIn(f.get("confidence", "high"), ("high", "medium", "low"))
            self.assertIn("summary", f["suggested_action"])
            self.assertIn("priority", f["suggested_action"])

        # Proactive recommendations structure (if present)
        for r in report.get("proactive_recommendations", []):
            for req_r_key in ("id", "title", "opportunity", "suggested_action"):
                self.assertIn(req_r_key, r, f"Recommendation missing required key '{req_r_key}'")
            self.assertIn("summary", r["suggested_action"])
            self.assertIn("priority", r["suggested_action"])

    def test_01_cli_help_and_exit_behavior(self):
        """
        Running with -h/--help displays help and exits with code 0.
        Running with no args prints usage and returns code 1.
        """
        with patch("sys.stdout", new=StringIO()):
            with self.assertRaises(SystemExit) as cm:
                main(["--help"])
            self.assertEqual(cm.exception.code, 0)

        with patch("sys.stderr", new=StringIO()) as fake_stderr:
            exit_code = main([])
            self.assertEqual(exit_code, 1)
            self.assertIn("usage", fake_stderr.getvalue().lower())

    def test_02_cli_json_output_format(self):
        """
        Running CLI with default/explicit json format outputs valid JSON conforming to schema.
        """
        healthy_fix = self.fixtures["1_healthy_static_site"]
        with patch.object(AuditOrchestrator, "run") as mock_run:
            mock_run.return_value = {
                "site": "https://stellar-analytics.example/",
                "audited_at": "2026-09-03T12:00:00Z",
                "summary": {"total_findings": 0, "critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0},
                "findings": [],
                "proactive_recommendations": []
            }
            with patch("sys.stdout", new=StringIO()) as fake_stdout:
                exit_code = main(["https://stellar-analytics.example/", "--format", "json"])
                self.assertEqual(exit_code, 0)
                output = fake_stdout.getvalue()
                data = json.loads(output)
                self._validate_report_schema_strictly(data)
                self.assertEqual(data["site"], "https://stellar-analytics.example/")

    def test_03_cli_markdown_output_format(self):
        """
        Running CLI with --format markdown produces clean human-readable Markdown.
        """
        report_data = {
            "site": "https://test-example.com/",
            "audited_at": "2026-09-03T12:00:00Z",
            "summary": {"total_findings": 1, "critical": 0, "high": 1, "medium": 0, "low": 0, "info": 0},
            "findings": [
                {
                    "id": "F-001",
                    "title": "Key factual content missing from initial HTML response",
                    "category": "machine_readability",
                    "severity": "high",
                    "confidence": "high",
                    "observation": "Price data rendered only via JavaScript.",
                    "evidence": "URL: https://test-example.com/product\nMissing: $49.00",
                    "root_cause": "Client-side hydration without SSR.",
                    "impact": "Automated extractors cannot read prices.",
                    "detection_method": "deterministic",
                    "affected_urls": ["https://test-example.com/product"],
                    "suggested_action": {
                        "summary": "Implement SSR for pricing.",
                        "implementation_details": "Render inside <p class='price'> on server.",
                        "priority": "high"
                    }
                }
            ],
            "proactive_recommendations": [
                {
                    "id": "REC-001",
                    "title": "Entity Disambiguation",
                    "opportunity": "Add sameAs URIs to Organization.",
                    "suggested_action": {"summary": "Add official registry links.", "priority": "low"}
                }
            ]
        }

        md_output = render_markdown_report(report_data)

        # Assert key elements present
        self.assertIn("# WebVerity - AI Readiness & Website Intelligence Report", md_output)
        self.assertIn("https://test-example.com/", md_output)
        self.assertIn("Executive Summary", md_output)
        self.assertIn("[HIGH] Key factual content missing from initial HTML response", md_output)
        self.assertIn("F-001", md_output)
        self.assertIn("Observation:", md_output)
        self.assertIn("Evidence:", md_output)
        self.assertIn("Root Cause:", md_output)
        self.assertIn("Impact:", md_output)
        self.assertIn("Suggested Action (Priority: High):", md_output)
        self.assertIn("Proactive Recommendations", md_output)
        self.assertIn("[REC-001] Entity Disambiguation", md_output)

    def test_04_cli_output_to_file(self):
        """
        Testing -o/--output writes report content directly to file.
        """
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp_file:
            tmp_path = tmp_file.name

        try:
            with patch.object(AuditOrchestrator, "run") as mock_run:
                mock_run.return_value = {
                    "site": "https://example.com/",
                    "audited_at": "2026-09-03T12:00:00Z",
                    "summary": {"total_findings": 0, "critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0},
                    "findings": [],
                    "proactive_recommendations": []
                }
                exit_code = main(["https://example.com/", "-o", tmp_path, "-q"])
                self.assertEqual(exit_code, 0)

            with open(tmp_path, "r", encoding="utf-8") as f:
                saved_content = f.read()
            data = json.loads(saved_content)
            self._validate_report_schema_strictly(data)
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    def test_05_cli_malformed_url_graceful_handling(self):
        """
        Malformed URL string produces controlled structured output with 0 unhandled exceptions.
        """
        with patch("sys.stdout", new=StringIO()) as fake_stdout:
            exit_code = main(["htp://broken-url-with-invalid-schema", "--format", "json"])
            self.assertEqual(exit_code, 0)
            data = json.loads(fake_stdout.getvalue())
            self._validate_report_schema_strictly(data)
            self.assertEqual(data["summary"]["total_findings"], 0)

    def test_06_cli_healthy_site_markdown_rendering(self):
        """
        Healthy site with 0 findings renders cleanly as HEALTHY without false alarms.
        """
        healthy_report = {
            "site": "https://healthy-site.example/",
            "audited_at": "2026-09-03T12:00:00Z",
            "summary": {"total_findings": 0, "critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0},
            "findings": [],
            "proactive_recommendations": []
        }
        md = render_markdown_report(healthy_report)
        self.assertIn("HEALTHY (0 Defects Detected)", md)
        self.assertIn("No defects or discoverability barriers detected", md)

    def test_07_cli_both_format_option(self):
        """
        Testing --format both includes JSON block and Markdown block.
        """
        with patch.object(AuditOrchestrator, "run") as mock_run:
            mock_run.return_value = {
                "site": "https://both.example/",
                "audited_at": "2026-09-03T12:00:00Z",
                "summary": {"total_findings": 0, "critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0},
                "findings": [],
                "proactive_recommendations": []
            }
            with patch("sys.stdout", new=StringIO()) as fake_stdout:
                exit_code = main(["https://both.example/", "-f", "both"])
                self.assertEqual(exit_code, 0)
                out = fake_stdout.getvalue()
                self.assertIn("--- JSON REPORT ---", out)
                self.assertIn("--- MARKDOWN REPORT ---", out)

    def test_08_external_corroboration_file_flag(self):
        """
        Testing --external loads external records JSON and passes to orchestrator.
        """
        ext_data = [
            {
                "attribute": "organization_name",
                "source_name": "Official Registry",
                "source_type": "official_registry",
                "is_entity_relevant": True,
                "is_direct_statement": True,
                "external_value": "Acme Global International"
            }
        ]
        with tempfile.NamedTemporaryFile(suffix=".json", mode="w", delete=False, encoding="utf-8") as tmp_f:
            json.dump(ext_data, tmp_f)
            tmp_path = tmp_f.name

        try:
            with patch.object(AuditOrchestrator, "run") as mock_run:
                mock_run.return_value = {
                    "site": "https://acme.example/",
                    "audited_at": "2026-09-03T12:00:00Z",
                    "summary": {"total_findings": 1, "critical": 0, "high": 0, "medium": 1, "low": 0, "info": 0},
                    "findings": [{
                        "id": "F-001",
                        "title": "Discrepancy in organization name",
                        "category": "freshness_corroboration",
                        "severity": "medium",
                        "confidence": "high",
                        "observation": "Mismatch with official registry",
                        "evidence": "Source: Official Registry",
                        "root_cause": "Out of sync registry",
                        "impact": "Ambiguity in knowledge graphs",
                        "affected_urls": ["https://acme.example/"],
                        "suggested_action": {"summary": "Synchronize name", "priority": "medium"}
                    }],
                    "proactive_recommendations": []
                }
                with patch("sys.stdout", new=StringIO()):
                    exit_code = main(["https://acme.example/", "--external", tmp_path, "-q"])
                    self.assertEqual(exit_code, 0)
                    mock_run.assert_called_once()
                    call_kwargs = mock_run.call_args[1]
                    self.assertEqual(call_kwargs.get("external_records"), ext_data)
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    def test_09_graceful_transport_network_failure(self):
        """
        Simulated network transport error generates valid report with 1 critical finding
        explaining the unreachable host rather than crashing.
        """
        orchestrator = AuditOrchestrator()
        # Non-routable IP to simulate immediate connection failure
        report = orchestrator.run("http://192.0.2.1:1/nonexistent-test", crawl_options={"timeout": 0.5})
        self._validate_report_schema_strictly(report)
        self.assertEqual(report["summary"]["critical"], 1)
        self.assertEqual(report["findings"][0]["category"], "crawlability")
        self.assertIn("unreachable", report["findings"][0]["root_cause"].lower())


if __name__ == "__main__":
    unittest.main()
