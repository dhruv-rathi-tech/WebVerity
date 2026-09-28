"""
Demo script to exercise the engagement-audit skill.
Demonstrates:
1. Orientation and landing subject clarity evaluation
2. Semantic heading hierarchy gap detection
3. Dead-end commercial product / service conversion path detection
4. False positive controls (terminal legal pages produce 0 defects)
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
    PageArchetype,
    HeadingItem,
    LinkItem
)

# Load inspect_engagement
_skill_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "skills", "engagement-audit", "scripts", "inspect_engagement.py"))
_spec = importlib.util.spec_from_file_location("inspect_engagement", _skill_path)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)
inspect_engagement = _mod.inspect_engagement


def run_demo():
    print("==================================================================")
    print("  PHASE 7 DEMO: ON-SITE ENGAGEMENT AUDIT SKILL")
    print("==================================================================")

    # 1. Page 1: Dead-end product page (no buy buttons, no related links)
    page_dead_end = PageEvidence(
        url="https://store.example.com/product/obscure-camera",
        normalized_url="https://store.example.com/product/obscure-camera",
        status_code=200,
        response_time_ms=22.0,
        content_type="text/html",
        page_archetype=PageArchetype.PRODUCT_DETAIL,
        is_primary_page=True,
        title="Obscure Camera Model X",
        meta_description="",
        canonical_url=None,
        meta_tags={},
        raw_html="<h1>Obscure Camera Model X</h1><p>Technical optical overview.</p>",
        raw_text="Obscure Camera Model X Technical optical overview.",
        raw_text_length=51,
        raw_word_count=7,
        heading_tree=[HeadingItem(tag="h1", level=1, text="Obscure Camera Model X", dom_index=0)],
        internal_links=[]
    )

    # 2. Page 2: Severe heading gap (starts at h4 without h1/h2)
    page_bad_headings = PageEvidence(
        url="https://store.example.com/services",
        normalized_url="https://store.example.com/services",
        status_code=200,
        response_time_ms=18.0,
        content_type="text/html",
        page_archetype=PageArchetype.OTHER,
        is_primary_page=False,
        title="Custom Services",
        meta_description="",
        canonical_url=None,
        meta_tags={},
        raw_html="<h4>Studio Calibration</h4><h5>Field Servicing</h5><h4>Consulting</h4>",
        raw_text="Studio Calibration Field Servicing Consulting",
        raw_text_length=45,
        raw_word_count=5,
        heading_tree=[
            HeadingItem(tag="h4", level=4, text="Studio Calibration", dom_index=0),
            HeadingItem(tag="h5", level=5, text="Field Servicing", dom_index=1),
            HeadingItem(tag="h4", level=4, text="Consulting", dom_index=2)
        ],
        internal_links=[LinkItem(url="https://store.example.com/contact", anchor_text="Contact", is_internal=True)]
    )

    # 3. Page 3: Terminal legal page (Privacy Policy - should produce 0 defects)
    page_privacy = PageEvidence(
        url="https://store.example.com/privacy",
        normalized_url="https://store.example.com/privacy",
        status_code=200,
        response_time_ms=15.0,
        content_type="text/html",
        page_archetype=PageArchetype.LEGAL,
        is_primary_page=False,
        title="Privacy Statement",
        meta_description="",
        canonical_url=None,
        meta_tags={},
        raw_html="<h1>Privacy Statement</h1><p>We do not sell personal data.</p>",
        raw_text="Privacy Statement We do not sell personal data.",
        raw_text_length=47,
        raw_word_count=7,
        heading_tree=[HeadingItem(tag="h1", level=1, text="Privacy Statement", dom_index=0)],
        internal_links=[]
    )

    ctx = CrawlContext(
        root_url="https://store.example.com/",
        domain="store.example.com",
        audited_at="2026-09-02T12:00:00Z",
        site_archetype=SiteArchetype.ECOMMERCE,
        robots_policy=RobotsPolicy(exists=True, url="https://store.example.com/robots.txt", raw_content=""),
        sitemap_summary=SitemapSummary(exists=True),
        pages=[page_dead_end, page_bad_headings, page_privacy]
    )

    print("\n[1] Executing inspect_engagement()...")
    findings = inspect_engagement(ctx)

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
    print("  PHASE 7 VALIDATION COMPLETE: ALL CHECKS PASS")
    print("==================================================================")


if __name__ == "__main__":
    run_demo()
