---
name: freshness-corroboration-audit
description: Audits temporal signals (outdated copyright years, stale dateModified attributes) and identifies cross-page factual contradictions across different URLs of the target domain.
license: Apache-2.0
---

# Freshness & Corroboration Audit Skill

## When to use
Use this skill during an audit to diagnose:
1. Signals indicating abandoned or unmaintained web assets (e.g. copyright year outdated by >= 2 years, stale publish dates on time-sensitive offers).
2. Inconsistent or conflicting factual claims across different pages of the same website (e.g. contradictory pricing on `/pricing` vs `/products`, or mismatched contact phone numbers).

## Inputs
- `crawl_context` (object, required): The shared crawl context containing multi-page metadata, dates, and extracted entity dictionaries.

## Procedure
1. **Temporal Staleness Audit**:
   - Extract footer copyright statements (`© [0-9]{4}`) using regex. Compare with the current calendar year on active commercial pages.
   - Parse `dateModified` / `datePublished` schema properties and HTTP `Last-Modified` response headers.
   - Flag pages where time-sensitive commercial offerings display ancient modification dates.
2. **Cross-Page Entity Consistency Reconciliation**:
   - Build a multi-page entity matrix for core brand attributes (organization name, primary contact numbers, physical addresses, product prices).
   - Compare entity values across all crawled pages.
   - Detect and flag contradictions (e.g., footer lists Phone A, but `/contact` lists Phone B).

## Output
Emits a list of normalized `Finding` objects covering:
- `category`: `freshness_corroboration`
- Evidence of temporal staleness or conflicting URL pairs with exact discordant values
- Clear suggested actions for content synchronization
