---
name: audit-orchestrator
description: Entrypoint skill that coordinates the end-to-end website audit for AI discoverability and on-site engagement. Plans bounded crawl budgets, invokes specialized domain skills, aggregates and deduplicates findings, calculates multi-factor severity, and emits the final validated audit report.
license: Apache-2.0
---

# Audit Orchestrator (Entrypoint Skill)

## When to use
Use this skill when receiving a website URL or domain name to perform a comprehensive, evidence-backed audit of:
1. **AI Discoverability** (crawlability, JS hydration gaps, structured data, entity clarity, freshness)
2. **On-Site Engagement** (information hierarchy, above-the-fold orientation, buried answers, next-step paths)

## Inputs
- `url` (string, required): The target website URL (e.g. `https://example.com`).
- `max_pages` (integer, optional, default: 20): Maximum number of representative pages to crawl (bounded depth <= 2).
- `timeout` (float, optional, default: 300.0): Overall audit execution timeout in seconds (< 5 minutes).
- `enable_llm` (boolean, optional, default: false): Optional flag to enable advanced semantic copy evaluation with graceful deterministic fallback.

## Procedure
1. **URL Validation & Scope Ingestion**:
   - Parse and sanitize the input URL. Verify protocol (`http`/`https`) and canonical hostname.
2. **Foundational Crawl & Evidence Assembly**:
   - Fetch and evaluate `robots.txt` and `sitemap.xml`.
   - Execute bounded async crawl using `httpx` to gather up to `max_pages` representative routes.
   - Run heuristic archetype classification (Site & Page levels).
   - Trigger selective headless browser rendering for JS-heavy routes where raw HTML is an empty container.
   - Construct the immutable `CrawlContext` and `PageEvidence` shared evidence bundle.
3. **Domain Skill Invocation**:
   - Execute `crawl-render-audit` to evaluate crawler directives and CSR fact omissions.
   - Execute `structured-data-entity-audit` to validate schema.org JSON-LD and visible-to-schema consistency.
   - Execute `freshness-corroboration-audit` to audit temporal validity and cross-page factual agreement.
   - Execute `engagement-audit` to evaluate heading trees, layout offsets, and conversion paths.
4. **Findings Normalization & Deduplication**:
   - Collect raw findings from all 4 domain skills.
   - Deduplicate overlapping observations and assign standardized IDs (`F-001`, `F-002`, etc.).
5. **Multi-Factor Severity & Priority Scoring**:
   - Compute severity using $\text{Severity} = f(\text{Impact}, \text{Scope}, \text{Page Importance}, \text{Evidence Strength})$.
   - Compute finding confidence based on directness of deterministic vs semantic evidence.
   - Assign actionable priorities (`critical`, `high`, `medium`, `low`) to suggested actions.
6. **Report Generation & Schema Validation**:
   - Validate the report payload against `references/report-schema.json`.
   - Output structured JSON and companion human-readable Markdown summary.

## Output
A validated JSON audit report containing:
- `site`: Audited domain.
- `audited_at`: ISO 8601 UTC timestamp.
- `summary`: Counts breakdown (`total_findings`, `critical`, `high`, `medium`, `low`, `info`).
- `findings`: Array of evidence-backed findings strictly adhering to the 6-step causal chain (`observation`, `evidence`, `root_cause`, `impact`, `severity`, `confidence`, `suggested_action`).
- `proactive_recommendations`: Beyond-defect optimization opportunities.
