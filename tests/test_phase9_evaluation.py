"""
Phase 9 End-to-End Evaluation & Hardening Test Suite.
Tests the complete multi-skill pipeline against 18 deterministic fixtures covering:
- Precision, recall, false-positive control, and missed findings
- Evidence completeness and causal chain integrity
- Severity and confidence scoring accuracy
- Recommendation specificity (preventing generic SEO boilerplate)
- Cross-skill deduplication (preserving multi-fault URLs and merging identical root causes)
- Cross-archetype generalization (e-commerce, B2B SaaS, local service, publisher, corporate, portfolio)
- Graceful degradation on unreachable/invalid targets
- Bounded execution runtime
"""

import os
import sys
import time
import unittest
from typing import Dict, Any, List, Set

# Ensure workspace root in path
_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import importlib.util

# Load orchestrator dynamically due to hyphen in folder name
_orchestrator_path = os.path.abspath(os.path.join(_ROOT, "skills", "audit-orchestrator", "scripts", "orchestrate.py"))
_spec = importlib.util.spec_from_file_location("orchestrate", _orchestrator_path)
_orchestrate_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_orchestrate_mod)
AuditOrchestrator = _orchestrate_mod.AuditOrchestrator

from tests.fixtures.eval_fixtures import get_all_eval_fixtures
from core.models import (
    CrawlContext, PageEvidence, SiteArchetype, PageArchetype,
    HeadingItem, LinkItem, JsonLdBlock, RobotsPolicy, SitemapSummary
)


class TestPhase9EndToEndEvaluation(unittest.TestCase):
    """
    Comprehensive evaluation harness across 18 deterministic scenarios.
    """

    @classmethod
    def setUpClass(cls):
        cls.orchestrator = AuditOrchestrator()
        cls.fixtures = get_all_eval_fixtures()
        cls.eval_results: Dict[str, Dict[str, Any]] = {}

    def test_01_execute_all_18_fixtures_and_measure_metrics(self):
        """
        Executes all 18 evaluation scenarios through the complete orchestrator pipeline,
        measuring precision, recall, false positives, evidence completeness, and runtime.
        """
        total_tp = 0
        total_fp = 0
        total_fn = 0
        total_tn = 0

        categories_tested: Set[str] = set()
        archetypes_tested: Set[str] = set()

        for fix_key, fix in self.fixtures.items():
            start_t = time.perf_counter()

            # Handle Fixture 16 specifically (deduplication raw findings test)
            if fix["id"] == 16:
                # Test synthetic multi-pass raw finding deduplication
                raw_findings = [
                    {
                        "id": "F-001",
                        "title": "Invalid JSON-LD syntax in header",
                        "category": "structured_data",
                        "severity": "high",
                        "confidence": "high",
                        "observation": "Syntax error encountered during parsing",
                        "evidence": "URL: https://dedup-test.example/\nError: Unescaped character",
                        "root_cause": "The embedded JSON-LD script contains syntax errors such as unescaped characters, trailing commas, or invalid JSON encoding.",
                        "impact": "Automated parsers fail to decode the structured data block.",
                        "detection_method": "deterministic",
                        "affected_urls": ["https://dedup-test.example/"],
                        "suggested_action": {"summary": "Fix JSON-LD formatting.", "priority": "high"}
                    },
                    {
                        "id": "F-002",
                        "title": "Malformed schema.org JSON block",
                        "category": "structured_data",
                        "severity": "high",
                        "confidence": "high",
                        "observation": "Syntax error encountered during parsing",
                        "evidence": "URL: https://dedup-test.example/\nLine 12 syntax failure",
                        "root_cause": "The embedded JSON-LD script contains syntax errors such as unescaped characters, trailing commas, or invalid JSON encoding.",
                        "impact": "Automated parsers fail to decode the structured data block.",
                        "detection_method": "deterministic",
                        "affected_urls": ["https://dedup-test.example/"],
                        "suggested_action": {"summary": "Fix JSON-LD formatting.", "priority": "high"}
                    }
                ]
                deduped = self.orchestrator._deduplicate_findings(raw_findings)
                report = self.orchestrator._synthesize_report(fix["target_url"], "2026-09-03T12:00:00Z", deduped)
            else:
                # Normal pipeline execution
                report = self.orchestrator.run(
                    target_url=fix["target_url"],
                    external_records=fix.get("external_records"),
                    existing_context=fix.get("context")
                )

            elapsed_ms = (time.perf_counter() - start_t) * 1000.0

            findings = report.get("findings", [])
            proactive_recs = report.get("proactive_recommendations", [])
            actual_defect_count = len(findings)
            expected_defect_count = fix["expected_defects"]

            # Evaluate TP, FP, FN, TN
            if expected_defect_count > 0:
                if actual_defect_count == expected_defect_count:
                    tp = actual_defect_count
                    fp = 0
                    fn = 0
                elif actual_defect_count > expected_defect_count:
                    tp = expected_defect_count
                    fp = actual_defect_count - expected_defect_count
                    fn = 0
                else:
                    tp = actual_defect_count
                    fp = 0
                    fn = expected_defect_count - actual_defect_count
                tn = 0
            else:
                # Negative case / healthy target
                if actual_defect_count == 0:
                    tp = 0
                    fp = 0
                    fn = 0
                    tn = 1
                else:
                    tp = 0
                    fp = actual_defect_count
                    fn = 0
                    tn = 0

            total_tp += tp
            total_fp += fp
            total_fn += fn
            total_tn += tn

            archetypes_tested.add(fix["archetype"].value if hasattr(fix["archetype"], "value") else str(fix["archetype"]))
            for f in findings:
                categories_tested.add(f.get("category", ""))

            self.eval_results[fix_key] = {
                "id": fix["id"],
                "name": fix["name"],
                "expected": expected_defect_count,
                "actual": actual_defect_count,
                "proactive_recs": len(proactive_recs),
                "tp": tp,
                "fp": fp,
                "fn": fn,
                "tn": tn,
                "runtime_ms": elapsed_ms,
                "categories": [f.get("category") for f in findings],
                "titles": [f.get("title") for f in findings]
            }

            # 1. Defect count assertion
            self.assertEqual(
                actual_defect_count,
                expected_defect_count,
                f"Fixture [{fix['name']}] defect count mismatch: expected {expected_defect_count}, got {actual_defect_count}. Findings: {[f['title'] for f in findings]}"
            )

            # 2. Category matching
            for exp_cat in fix["expected_categories"]:
                self.assertIn(
                    exp_cat,
                    [f.get("category") for f in findings],
                    f"Fixture [{fix['name']}] must produce category '{exp_cat}'"
                )

            # 3. Forbidden findings check (Negative checks must NOT fire)
            for forbidden_kw in fix.get("forbidden_findings", []):
                for f in findings:
                    self.assertNotIn(
                        forbidden_kw.lower(),
                        f.get("title", "").lower(),
                        f"Fixture [{fix['name']}] emitted forbidden finding '{f.get('title')}' containing '{forbidden_kw}'"
                    )

            # 4. Expected root cause signature verification
            for exp_rc in fix.get("expected_root_cause_keywords", []):
                found_rc = any(exp_rc.lower() in f.get("root_cause", "").lower() for f in findings)
                self.assertTrue(
                    found_rc,
                    f"Fixture [{fix['name']}] missing expected root cause keyword '{exp_rc}' in findings."
                )

            # 5. Evidence & Causal Chain completeness for every finding
            for f in findings:
                self.assertTrue(f.get("evidence"), f"Finding {f.get('id')} in {fix['name']} must have non-empty evidence.")
                self.assertTrue(f.get("observation"), f"Finding {f.get('id')} in {fix['name']} must have non-empty observation.")
                self.assertTrue(f.get("root_cause"), f"Finding {f.get('id')} in {fix['name']} must have non-empty root_cause.")
                self.assertTrue(f.get("impact"), f"Finding {f.get('id')} in {fix['name']} must have non-empty impact.")
                self.assertTrue(f.get("suggested_action", {}).get("summary"), f"Finding {f.get('id')} must have actionable summary.")
                self.assertIn(f.get("severity"), ("critical", "high", "medium", "low", "info"))
                self.assertIn(f.get("confidence"), ("high", "medium", "low"))
                self.assertGreaterEqual(len(f.get("affected_urls", [])), 1)

            # 6. Runtime bound assertion (< 1000ms per in-memory fixture)
            self.assertLess(elapsed_ms, 1000.0, f"Fixture [{fix['name']}] execution took {elapsed_ms:.1f}ms, exceeding 1000ms bound.")

        # Compute Overall Metrics
        precision = total_tp / (total_tp + total_fp) if (total_tp + total_fp) > 0 else 1.0
        recall = total_tp / (total_tp + total_fn) if (total_tp + total_fn) > 0 else 1.0

        self.assertEqual(total_fp, 0, f"Total False Positives must be 0, got {total_fp}")
        self.assertEqual(total_fn, 0, f"Total False Negatives must be 0, got {total_fn}")
        self.assertEqual(precision, 1.0, f"Precision must be 1.0 (100%), got {precision}")
        self.assertEqual(recall, 1.0, f"Recall must be 1.0 (100%), got {recall}")

    def test_02_negative_false_positive_controls(self):
        """
        Validates negative control fixtures specifically designed to trigger false positives
        if thresholds were crude or non-contextual:
        - Sale price vs original MSRP
        - Product variants pricing range
        - Legal/Privacy utility pages lacking CTA buttons
        - Imperfect heading hierarchies that are nonetheless clear
        - Missing sitemap.xml
        - Harmless JavaScript hydration
        - Low-authority or irrelevant external sources
        """
        negative_keys = [
            "1_healthy_static_site",
            "4_product_ecommerce_sale_pricing",
            "8_corporate_institutional_compliant",
            "12_weak_irrelevant_external_source",
            "13_strong_engagement_clear_pathways",
            "18_no_findings_healthy_negative_controls"
        ]

        for n_key in negative_keys:
            fix = self.fixtures[n_key]
            report = self.orchestrator.run(
                target_url=fix["target_url"],
                external_records=fix.get("external_records"),
                existing_context=fix.get("context")
            )
            self.assertEqual(
                report["summary"]["total_findings"],
                0,
                f"Negative control [{fix['name']}] produced {report['summary']['total_findings']} false positive defects! Findings: {[f['title'] for f in report['findings']]}"
            )

    def test_03_causal_chain_and_evidence_completeness(self):
        """
        Verifies that every emitted finding follows the strict causal chain:
        Observation -> Evidence -> Root Cause -> Impact -> Severity/Confidence -> Suggested Action
        """
        for fix_key, fix in self.fixtures.items():
            if fix["id"] in (16, 17):
                continue
            report = self.orchestrator.run(
                target_url=fix["target_url"],
                external_records=fix.get("external_records"),
                existing_context=fix.get("context")
            )
            for f in report.get("findings", []):
                # Observation: must describe what was observed
                self.assertGreater(len(f["observation"]), 15, f"Finding {f['id']} observation too short: '{f['observation']}'")
                # Evidence: must cite URL/domain/source and affected_urls must be non-empty
                self.assertTrue(
                    any(k in f["evidence"].lower() for k in ("url", "domain", "source")),
                    f"Finding {f['id']} evidence must cite the affected target: '{f['evidence']}'"
                )
                self.assertGreaterEqual(len(f.get("affected_urls", [])), 1)
                # Root cause: must describe underlying technical mechanism
                self.assertGreater(len(f["root_cause"]), 20, f"Finding {f['id']} root cause lacks substance.")
                # Impact: must describe machine grounding / extraction consequence without bot conjecture
                self.assertGreater(len(f["impact"]), 20, f"Finding {f['id']} impact lacks substance.")
                # Suggested Action: must be specific to root cause
                self.assertGreater(len(f["suggested_action"]["summary"]), 15)

    def test_04_recommendation_specificity_not_generic_seo(self):
        """
        Asserts that recommendations provide concrete technical remediation rather than
        generic SEO boilerplate (e.g. 'Optimize keywords', 'Build backlinks', 'Improve SEO').
        """
        generic_boilerplate = ["optimize keywords", "build backlinks", "improve your seo", "meta keywords", "rank higher"]

        for fix_key, fix in self.fixtures.items():
            if fix["id"] in (16, 17):
                continue
            report = self.orchestrator.run(
                target_url=fix["target_url"],
                external_records=fix.get("external_records"),
                existing_context=fix.get("context")
            )
            for f in report.get("findings", []):
                summary = f["suggested_action"]["summary"].lower()
                for generic_phrase in generic_boilerplate:
                    self.assertNotIn(
                        generic_phrase,
                        summary,
                        f"Finding {f['id']} contains generic SEO boilerplate: '{generic_phrase}'"
                    )

    def test_05_multi_fault_single_url_preservation(self):
        """
        Asserts that when a single URL has multiple genuinely distinct defects
        (CSR missing facts, missing schema, and dead-end navigation), deduplication
        preserves all distinct root causes.
        """
        fix = self.fixtures["15_same_url_multiple_distinct_problems"]
        report = self.orchestrator.run(
            target_url=fix["target_url"],
            existing_context=fix["context"]
        )
        self.assertEqual(
            len(report["findings"]),
            3,
            f"Multi-fault single URL must preserve 3 distinct findings, got {len(report['findings'])}"
        )
        categories = {f["category"] for f in report["findings"]}
        self.assertEqual(
            categories,
            {"machine_readability", "structured_data", "on_site_engagement"},
            "All three distinct categories must be represented."
        )

    def test_06_proactive_recommendations_separated_from_defects(self):
        """
        Asserts that purely proactive opportunities (e.g. optional sameAs enrichment)
        are placed in proactive_recommendations[] and never inflate defect summary counts.
        """
        # Create a page that has Organization schema without sameAs
        p = PageEvidence(
            url="https://proactive-test.example/",
            normalized_url="https://proactive-test.example/",
            status_code=200,
            response_time_ms=20.0,
            content_type="text/html",
            page_archetype=PageArchetype.HOMEPAGE,
            is_primary_page=True,
            title="Proactive Test Corp",
            meta_description="",
            canonical_url=None,
            meta_tags={},
            raw_html="<h1>Proactive Test Corp</h1><p>Consulting and advisory.</p><a href='/contact'>Contact</a>",
            raw_text="Proactive Test Corp. Consulting and advisory. Contact.",
            raw_text_length=54,
            raw_word_count=7,
            heading_tree=[HeadingItem(tag="h1", level=1, text="Proactive Test Corp", dom_index=0)],
            internal_links=[LinkItem(url="/contact", anchor_text="Contact", is_internal=True)],
            json_ld=[
                JsonLdBlock(
                    raw_json='{"@type": "Organization", "name": "Proactive Test Corp"}',
                    parsed_data={"@type": "Organization", "name": "Proactive Test Corp"},
                    schema_types=["Organization"]
                )
            ]
        )
        ctx = CrawlContext(
            root_url="https://proactive-test.example/",
            domain="proactive-test.example",
            audited_at="2026-09-03T12:00:00Z",
            site_archetype=SiteArchetype.CORPORATE,
            robots_policy=RobotsPolicy(exists=True, url="https://proactive-test.example/robots.txt", raw_content="User-agent: *\nAllow: /"),
            sitemap_summary=SitemapSummary(exists=False),
            pages=[p]
        )
        report = self.orchestrator.run("https://proactive-test.example/", existing_context=ctx)
        self.assertEqual(report["summary"]["total_findings"], 0, "Proactive recommendations must not count as defect findings.")
        self.assertGreater(len(report["proactive_recommendations"]), 0, "sameAs absence should be captured as proactive recommendation.")
        self.assertEqual(report["proactive_recommendations"][0]["id"], "REC-001")


if __name__ == "__main__":
    unittest.main()
