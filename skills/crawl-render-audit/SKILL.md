---
name: crawl-render-audit
description: Audits crawler barriers, granular robots.txt AI bot exclusions, network transport anomalies, and client-side JavaScript rendering (CSR) content gaps where vital factual information is absent from initial raw HTML.
license: Apache-2.0
---

# Crawl & Render Audit Skill

## When to use
Use this skill during an audit to diagnose:
1. Why an AI assistant or search crawler cannot access, fetch, or index specific pages/routes.
2. Why an AI retrieval engine misses critical facts (prices, inventory, hours, specs) because they only exist in client-rendered DOM rather than initial crawlable HTML.
3. Whether important commercial or service facts are locked inside raw non-text images without accessible text.

## Inputs
- `crawl_context` (object, required): The shared crawl context containing root URL, domain, parsed `robots.txt`, and page evidence list.

## Procedure
1. **Robots.txt Granular Directive Audit**:
   - Parse `robots.txt` against leading AI user-agents defined in `references/bot-user-agents.json`.
   - Distinguish between real-time retrieval bots (`PerplexityBot`, `ChatGPT-User`) and offline training ingestors (`GPTBot`, `ClaudeBot`).
   - Evaluate path scope (e.g. site-wide `/` vs `/products/` vs safe administrative paths like `/admin/` or `/cart/`).
2. **HTTP Transport & Canonical Audit**:
   - Check status codes, redirect chains, and canonical link targets (`link[rel="canonical"]`).
   - Flag broken canonical targets or infinite redirect chains.
3. **Client-Side Rendering (CSR) Gaps**:
   - For pages where selective rendering was triggered, perform substantive token diffing between raw HTML text and rendered DOM text.
   - Verify if specific, vital factual entities (e.g., price, stock status, core service description) are present in rendered DOM but absent in raw HTML.
   - Filter out cosmetic diffs (session IDs, tracking scripts, dynamic ad containers).
4. **Non-Text Content Traps**:
   - Inspect images for textual/tabular data keywords (`menu`, `pricing`, `specs`, `schedule`) coupled with empty or generic `alt` attributes.

## Output
Emits a list of normalized `Finding` objects covering:
- `category`: `crawlability` or `machine_readability`
- Concrete evidence (exact `robots.txt` line, URL, token diffs, missing fact names)
- Severity and confidence ratings
- Targeted remediation instructions
