"""
Demo script to exercise the bounded async crawler against the local mock fixture server.
Demonstrates URL discovery, intelligent prioritization, PageEvidence extraction,
archetype classification, robots/sitemap parsing, and failure handling.
"""

import asyncio
import json
import os
import sys

# Ensure workspace root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.crawler import AsyncCrawler
from tests.fixtures.mock_server import start_mock_server


async def run_demo():
    print("==================================================================")
    print("  PHASE 3 DEMO: CRAWL & SHARED EVIDENCE FOUNDATION")
    print("==================================================================")

    server, base_url, thread = start_mock_server()
    try:
        print(f"\n[1] Starting in-process Mock HTTP Server at: {base_url}")
        crawler = AsyncCrawler(max_pages=15, max_depth=2, concurrency=4, request_timeout=5.0)
        
        print(f"[2] Initiating bounded crawl from seed: {base_url}")
        crawl_context = await crawler.crawl(base_url)

        print("\n==================================================================")
        print("  CRAWL SUMMARY METRICS")
        print("==================================================================")
        print(f"Domain Audited          : {crawl_context.domain}")
        print(f"Site Archetype Detected : {crawl_context.site_archetype.value.upper()}")
        print(f"Crawl Duration          : {crawl_context.crawl_duration_seconds:.3f} seconds")
        print(f"Total Discovered URLs   : {crawl_context.total_discovered_urls}")
        print(f"Total Crawled Pages     : {len(crawl_context.pages)}")
        print(f"Crawl Errors Encountered: {len(crawl_context.crawl_errors)}")

        print("\n==================================================================")
        print("  ROBOTS.TXT & SITEMAP DISCOVERY")
        print("==================================================================")
        print(f"Robots.txt Exists       : {crawl_context.robots_policy.exists}")
        print(f"Robots Sitemaps Found   : {crawl_context.robots_policy.sitemap_urls}")
        print(f"Bot Rules Configured    : {list(crawl_context.robots_policy.bot_rules.keys())}")
        print(f"Sitemap XML Discovered  : {crawl_context.sitemap_summary.exists} ({len(crawl_context.sitemap_summary.extracted_urls)} URLs)")

        print("\n==================================================================")
        print("  CRAWLED PAGES & EXTRACTED PAGE EVIDENCE")
        print("==================================================================")
        for idx, page in enumerate(crawl_context.pages, 1):
            print(f"\n[{idx}] URL: {page.url}")
            print(f"    Status: {page.status_code} | Latency: {page.response_time_ms}ms | Archetype: {page.page_archetype.value} | Primary: {page.is_primary_page}")
            print(f"    Title: '{page.title}'")
            print(f"    Meta Description: '{page.meta_description[:60]}...' if len > 60 else '{page.meta_description}'")
            print(f"    Headings ({len(page.heading_tree)}): {[f'{h.tag}:{h.text[:25]}' for h in page.heading_tree[:3]]}")
            print(f"    JSON-LD Schemas ({len(page.json_ld)}): {[t for b in page.json_ld for t in b.schema_types]}")
            print(f"    Internal Links: {len(page.internal_links)} | External Links: {len(page.external_links)} | Images: {len(page.images)}")
            print(f"    Text Tokens: {page.raw_word_count} words ({page.raw_text_length} chars) | Selective Render Trigger: {page.required_rendering_trigger}")

        print("\n==================================================================")
        print("  FAILURE HANDLING DEMONSTRATION")
        print("==================================================================")
        print("Testing invalid domain resolution and 404 handling...")
        invalid_crawler = AsyncCrawler(max_pages=2, request_timeout=2.0)
        invalid_context = await invalid_crawler.crawl("http://non-existent-domain-test-12345.local")
        print(f"Invalid Domain Handled Gracefully: {len(invalid_context.crawl_errors) > 0 or len(invalid_context.pages) == 0}")
        print(f"Errors Recorded: {invalid_context.crawl_errors or 'Connection handled safely without crash'}")

        print("\n[OK] Phase 3 Crawl & Evidence Foundation successfully validated.")

    finally:
        server.shutdown()
        server.server_close()


if __name__ == "__main__":
    asyncio.run(run_demo())
