---
name: engagement-audit
description: Audits on-site user engagement barriers including broken heading hierarchies (missing/multiple H1s, skipped heading levels), weak above-the-fold value proposition orientation, buried answers to core visitor questions, and missing next-step conversion guidance.
license: Apache-2.0
---

# On-Site Engagement Audit Skill

## When to use
Use this skill during an audit to diagnose:
1. Why visitors who arrive on a landing page fail to orient, skim, or engage with the content.
2. Semantic heading defects (missing `<h1>`, multiple competing `<h1>` tags, or skipped heading levels like `<h1>` followed directly by `<h3>`).
3. Critical questions (pricing, FAQs, support) that are buried deep down the page without navigation anchors.
4. Dead-end pages that lack clear, contextual next-step calls-to-action (CTAs) or related paths.

## Inputs
- `crawl_context` (object, required): The shared crawl context containing parsed DOM heading trees, vertical layout offsets, interactive CTA counts, and page archetypes.

## Procedure
1. **Information Hierarchy & Heading Tree Traversal**:
   - Traverse the DOM tree and extract all heading tags (`<h1>` through `<h6>`).
   - Validate that each page possesses exactly one descriptive `<h1>` tag.
   - Detect and flag invalid structural skips (e.g. `H1 -> H3`, `H2 -> H5`).
2. **Above-The-Fold Value Proposition & Orientation**:
   - Evaluate whether the top viewport area clearly answers what the site offers and who it is for.
   - Flag generic, ambiguous hero text lacking core category keywords.
3. **Buried Answer Proximity**:
   - Check vertical layout position of key informational answers on commercial / FAQ pages.
   - Flag vital answers positioned >2000px down that lack sticky table-of-contents or anchor links.
4. **Next-Step & Conversion Path Continuity**:
   - Count interactive elements (buttons, links with actionable verbs) in the content flow.
   - Flag dead-end landing pages where visitors have no clear path to purchase, contact, or explore.

## Output
Emits a list of normalized `Finding` objects covering:
- `category`: `on_site_engagement`
- Specific evidence (heading tag sequence, missing CTA counts, vertical pixel offsets)
- Actionable design and structural remediation recommendations
