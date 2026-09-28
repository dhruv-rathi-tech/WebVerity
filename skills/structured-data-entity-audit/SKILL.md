---
name: structured-data-entity-audit
description: Audits machine-readable knowledge graphs, schema.org JSON-LD syntax and semantics, entity disambiguation (sameAs), and flags factual contradictions between structured data and visible page copy.
license: Apache-2.0
---

# Structured Data & Entity Audit Skill

## When to use
Use this skill during an audit to diagnose:
1. Absence or syntax invalidity of schema.org structured data appropriate for the specific page archetype.
2. Contradictions where JSON-LD data states one value (e.g. `$49.00`, `OutOfStock`) but visible page copy displays another (e.g. `$59.00`, `In Stock`).
3. Weak entity disambiguation where `Organization` or `Brand` lacks `sameAs` links to Wikidata, Crunchbase, or verified social profiles.

## Inputs
- `crawl_context` (object, required): The shared crawl context containing parsed JSON-LD blocks, meta tags, and visible rendered text per page.

## Procedure
1. **JSON-LD Syntax & Schema Conformance**:
   - Parse all `<script type="application/ld+json">` elements into Abstract Syntax Trees (ASTs).
   - Validate against standard schema.org types using rules in `references/schema-types.json`.
   - Flag syntax errors, missing mandatory properties (`price`, `currency`, `headline`), or unresolvable type references.
2. **Archetype-Aware Schema Expectation**:
   - Check if the page contains the expected schema for its classified archetype (e.g. `Product` for e-commerce PDP, `LocalBusiness` for local service).
   - Do not flag irrelevant schemas (e.g. do not penalize SaaS homepages for lacking `Product/Offer`).
3. **Visible-to-Structured Fact Reconciliation**:
   - Extract declared facts from schema (price, currency, availability, organization name).
   - Compare against rendered text tokens extracted from the visible DOM.
   - Flag direct discrepancies as high/critical severity integrity defects.
4. **Entity Clarity & Disambiguation**:
   - Inspect `Organization` / `Brand` schemas for `sameAs` array containing external authority URIs (Wikidata QIDs, verified social profiles).

## Output
Emits a list of normalized `Finding` objects covering:
- `category`: `structured_data` or `entity_clarity`
- Detailed evidence (JSON-LD snippets, line numbers, conflicting DOM values)
- Concrete remediation markup examples
