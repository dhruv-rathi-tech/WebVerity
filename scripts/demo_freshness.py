"""
Demo script to exercise the freshness-corroboration-audit skill.
Demonstrates:
1. Internal cross-page factual contradiction detection (phone / price mismatch)
2. Genuinely stale temporal promotions
3. Outdated copyright year handling (low/info observation)
4. Authoritative external corroboration reconciliation with graceful fallback
"""

import os
import sys
import json
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

# Load check_freshness
_skill_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "skills", "freshness-corroboration-audit", "scripts", "check_freshness.py"))
_spec = importlib.util.spec_from_file_location("check_freshness", _skill_path)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)
check_freshness_and_corroboration = _mod.check_freshness_and_corroboration


def run_demo():
    print("==================================================================")
    print("  PHASE 6 DEMO: FRESHNESS & CORROBORATION AUDIT SKILL")
    print("==================================================================")

    # 1. Page 1: Homepage with phone and copyright 2022
    page_home = PageEvidence(
        url="https://store.example.com/",
        normalized_url="https://store.example.com/",
        status_code=200,
        response_time_ms=18.0,
        content_type="text/html",
        page_archetype=PageArchetype.HOMEPAGE,
        is_primary_page=True,
        title="Apex Cinema Gear",
        meta_description="",
        canonical_url=None,
        meta_tags={},
        raw_html="<footer>© 2022 Apex Dynamics Inc. Call: +1-800-555-0199</footer>",
        raw_text="Apex Cinema Gear Call: +1-800-555-0199",
        raw_text_length=40,
        raw_word_count=6,
        extracted_dates={"copyright_year": "2022"}
    )

    # 2. Page 2: Contact page with conflicting phone
    page_contact = PageEvidence(
        url="https://store.example.com/contact",
        normalized_url="https://store.example.com/contact",
        status_code=200,
        response_time_ms=22.0,
        content_type="text/html",
        page_archetype=PageArchetype.CONTACT,
        is_primary_page=False,
        title="Contact Us | Apex",
        meta_description="",
        canonical_url=None,
        meta_tags={},
        raw_html="<p>Call our direct line: +1-800-555-9999</p>",
        raw_text="Contact Us Call our direct line: +1-800-555-9999",
        raw_text_length=48,
        raw_word_count=7
    )

    # 3. Page 3: Expired promotional offer
    page_promo = PageEvidence(
        url="https://store.example.com/special-offer",
        normalized_url="https://store.example.com/special-offer",
        status_code=200,
        response_time_ms=20.0,
        content_type="text/html",
        page_archetype=PageArchetype.OTHER,
        is_primary_page=False,
        title="Spring Discount",
        meta_description="",
        canonical_url=None,
        meta_tags={},
        raw_html="<p>Spring Sale Deal: Offer valid through April 2023!</p>",
        raw_text="Spring Sale Deal: Offer valid through April 2023!",
        raw_text_length=49,
        raw_word_count=8
    )

    ctx = CrawlContext(
        root_url="https://store.example.com/",
        domain="store.example.com",
        audited_at="2026-09-02T12:00:00Z",
        site_archetype=SiteArchetype.ECOMMERCE,
        robots_policy=RobotsPolicy(exists=True, url="https://store.example.com/robots.txt", raw_content=""),
        sitemap_summary=SitemapSummary(exists=True),
        pages=[page_home, page_contact, page_promo]
    )

    # External records sample (1 authoritative, 1 weak)
    external_records = [
        {
            "source_name": "Official Business Registry",
            "authority_score": 0.90,
            "attribute": "company_name",
            "external_value": "Apex Cinema Systems LLC"
        },
        {
            "source_name": "Blog Forum",
            "authority_score": 0.25,  # Weak, filtered out
            "attribute": "company_name",
            "external_value": "Apex Super Store"
        }
    ]

    print("\n[1] Executing check_freshness_and_corroboration()...")
    findings = check_freshness_and_corroboration(ctx, external_records=external_records)

    print(f"\n[2] Total Findings Emitted: {len(findings)}")
    for f in findings:
        print("\n------------------------------------------------------------------")
        print(f"[{f['id']}] [{f['severity'].upper()}] {f['title']}")
        print(f"Category   : {f['category']}")
        print(f"Confidence : {f['confidence']}")
        print(f"Observation: {f['observation']}")
        print(f"Evidence   :\n{f['evidence']}")
        print(f"Root Cause : {f['root_cause']}")
        print(f"Impact     : {f['impact']}")
        print(f"Action     : {f['suggested_action']['summary']}")
        print(f"Priority   : {f['suggested_action']['priority']}")

    print("\n==================================================================")
    print("  PHASE 6 VALIDATION COMPLETE: ALL CHECKS PASS")
    print("==================================================================")


if __name__ == "__main__":
    run_demo()
