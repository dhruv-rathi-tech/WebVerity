"""
Selective headless rendering engine.
Only executes headless rendering for pages already flagged by Phase 3 (CSR triggers),
strictly bounded by page limits and navigation timeouts.
"""

import asyncio
import re
from typing import List, Optional
from bs4 import BeautifulSoup, Comment
from core.models import CrawlContext, PageEvidence
from core.diff_analyzer import analyze_raw_vs_rendered_dom


async def selectively_render_pages(
    crawl_context: CrawlContext,
    max_render_pages: int = 5,
    render_timeout_sec: float = 10.0
) -> None:
    """
    Renders flagged pages using Playwright (if available) and populates rendered_dom,
    rendered_text, and missing_facts_in_raw in-place.
    """
    flagged_pages = [p for p in crawl_context.pages if p.required_rendering_trigger and p.status_code == 200]
    if not flagged_pages:
        return

    pages_to_render = flagged_pages[:max_render_pages]

    try:
        from playwright.async_api import async_playwright
    except ImportError:
        # Graceful fallback: Playwright not installed
        crawl_context.rendering_available = False
        for p in pages_to_render:
            p.rendered_dom = p.raw_html
            p.rendered_text = p.raw_text
        return

    try:
        async with async_playwright() as p:
            try:
                browser = await p.chromium.launch(headless=True)
            except Exception as launch_err:
                # Browser binary might not be installed; fallback gracefully
                crawl_context.rendering_available = False
                for page_ev in pages_to_render:
                    page_ev.rendered_dom = page_ev.raw_html
                    page_ev.rendered_text = page_ev.raw_text
                return

            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                viewport={"width": 1280, "height": 800}
            )

            for page_ev in pages_to_render:
                try:
                    page = await context.new_page()
                    # Navigate with timeout
                    await page.goto(
                        page_ev.url,
                        wait_until="domcontentloaded",
                        timeout=int(render_timeout_sec * 1000)
                    )
                    # Short stabilization wait
                    await asyncio.sleep(0.5)

                    rendered_html = await page.content()
                    await page.close()

                    # Extract clean rendered text
                    rendered_text = _extract_clean_text(rendered_html)
                    page_ev.rendered_dom = rendered_html
                    page_ev.rendered_text = rendered_text

                    # Analyze Diff
                    missing_facts, ratio, is_meaningful = analyze_raw_vs_rendered_dom(
                        raw_html=page_ev.raw_html,
                        rendered_dom=rendered_html,
                        raw_text=page_ev.raw_text,
                        rendered_text=rendered_text
                    )
                    page_ev.missing_facts_in_raw = missing_facts

                except Exception as page_err:
                    # Graceful degradation on timeout or render error
                    page_ev.rendered_dom = page_ev.raw_html
                    page_ev.rendered_text = page_ev.raw_text

            await browser.close()

    except Exception:
        # Top-level safety fallback
        for page_ev in pages_to_render:
            if not page_ev.rendered_dom:
                page_ev.rendered_dom = page_ev.raw_html
                page_ev.rendered_text = page_ev.raw_text


def _extract_clean_text(html: str) -> str:
    if not html:
        return ""
    soup = BeautifulSoup(html, "html.parser")
    for elem in soup(["script", "style", "noscript", "svg", "header", "footer"]):
        elem.decompose()
    for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
        comment.extract()
    text = soup.get_text(separator=" ", strip=True)
    return re.sub(r"\s+", " ", text)
