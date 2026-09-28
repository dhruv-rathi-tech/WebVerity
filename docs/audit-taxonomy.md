# Website AI Readiness Audit Taxonomy & Skill Decomposition

## 1. Comprehensive Audit Taxonomy

This taxonomy defines the complete set of inspection checks, evidence requirements, severity/confidence heuristics, detection mechanisms, false-positive mitigations, and concrete remediation actions across both **AI Discoverability** and **On-Site Engagement**.

---

### Category A: Crawlability & Indexing Infrastructure

| Check | Problem | Evidence | Impact | Severity | Confidence | Detection | False Positives | Fix |
|---|---|---|---|---|---|---|---|---|
| **A-01: AI Crawler Blockade** | `robots.txt` explicitly disallows leading AI user-agents (`GPTBot`, `ClaudeBot`, `PerplexityBot`, `Google-Extended`) from crawling content. | `robots.txt` directive: `User-agent: GPTBot Disallow: /` or disallow rules covering `/products` or core routes. | Total AI invisibility; AI search engines cannot fetch raw or rendered pages for RAG context. | **Critical** (if entire site blocked) / **High** (if core commercial paths blocked) | **High** | Deterministic (Regex / Robots parser) | Intentional paywalled/private sections. *Mitigation*: Only flag when public root or marketing/product routes are disallowed. | Update `robots.txt` to permit read-only access for verified AI bots on public informational and catalog routes. |
| **A-02: Broken Canonical Reference** | `link[rel="canonical"]` points to a 404/5xx URL, forms a redirect loop, or points cross-domain erroneously. | `canonical` URL string mismatch with HTTP resolution test returning non-200 or circular redirect chain. | AI crawlers discard unindexed or conflicted canonical targets, dropping pages from search/RAG index. | **High** | **High** | Deterministic (HTTP fetch & header check) | Temporary staging domain references during migration. | Ensure every canonical tag targets the exact, self-referential canonical URL returning HTTP 200. |
| **A-03: Sitemap Deficiency** | Missing `sitemap.xml`, sitemap returning 404, or sitemap missing >50% of discoverable internal URLs. | Crawl discovery: `robots.txt` lacks Sitemap directive, `/sitemap.xml` returns 404, or internal link graph contains orphaned nodes. | Delayed or incomplete AI ingestion of deep product/article pages. | **Medium** | **High** | Deterministic (XML parser + link set comparison) | Small 1-page static landing sites without sitemaps. *Mitigation*: Suppress if site has <= 3 total pages. | Generate dynamic, valid XML sitemaps referenced in `robots.txt` and submitted to search consoles. |

---

### Category B: Machine Readability & Client-Side Rendering Gaps

| Check | Problem | Evidence | Impact | Severity | Confidence | Detection | False Positives | Fix |
|---|---|---|---|---|---|---|---|---|
| **B-01: JS-Hydration Content Black Hole** | Critical text/data (pricing, descriptions, specifications, hours) exists in rendered DOM but is completely absent from initial raw HTML. | `TextLength(Raw HTML) / TextLength(Rendered DOM) < 0.25` or key entity tokens present in DOM missing from raw source text. | Fast/lightweight AI crawlers that do not execute full JavaScript engines see an empty page and cannot quote facts. | **Critical** (core product/service missing) / **High** (secondary specs missing) | **High** | Deterministic (Raw vs Headless Render DOM token diff) | CSR on non-essential widgets (chat bubbles, recommendations). *Mitigation*: Exclude known dynamic third-party container selectors. | Implement Server-Side Rendering (SSR) or Static Site Generation (SSG) for core factual content and entity attributes. |
| **B-02: Non-Text Locked Information** | Vital commercial/service data (menus, pricing tables, technical specs, operating schedules) locked in raw images or canvas without HTML text. | Image element `<img>` containing OCR-detected text or filename matching `menu|pricing|schedule` with empty or generic `alt` attribute. | AI summarizers and screen readers cannot extract structured tabular data from bitmap images. | **High** | **Medium** | Hybrid (DOM parser + image heuristics / OCR) | Decorative stock photography. *Mitigation*: Only flag images situated in main content containers with keywords in `src` or adjacent headings. | Convert graphic tables into semantic HTML tables (`<table>`, `<tr>`, `<td>`) or provide comprehensive textual fallbacks. |
| **B-03: Hidden / Tabbed Content Cloaking** | Substantial product or FAQ answers hidden behind collapsed CSS/JS accordions without accessible markup (`aria-expanded`, crawlable text). | Text located inside elements with `display: none` or `visibility: hidden` in initial HTML without `details/summary` semantics. | Retrieval engines may downweight hidden text as potential keyword stuffing or fail to index collapsed sections. | **Medium** | **Medium** | Deterministic (CSS computed style & DOM inspection) | Intentional mobile navigation drawers. *Mitigation*: Ignore `<nav>` and header elements. | Use native `<details>` and `<summary>` elements or ensure accordion text is present in the DOM with proper ARIA attributes. |

---

### Category C: Structured Data & Semantic Knowledge Graph

| Check | Problem | Evidence | Impact | Severity | Confidence | Detection | False Positives | Fix |
|---|---|---|---|---|---|---|---|---|
| **C-01: Missing Core Schema Markup** | Page archetype lacks foundational schema.org JSON-LD (e.g., E-commerce product without `Product`, SaaS without `SoftwareApplication`, Local business without `LocalBusiness`). | `0` JSON-LD `<script type="application/ld+json">` blocks detected matching classified page archetype. | AI models must resort to fragile heuristic scraping instead of extracting direct entity graphs and pricing nodes. | **High** | **High** | Hybrid (Archetype classifier + JSON-LD parser) | Blogs or contact pages lacking commercial schema. *Mitigation*: Check schema expectations against page archetype. | Embed valid JSON-LD representing the primary entity (`Product`, `Organization`, `Service`, `Article`) with mandatory fields. |
| **C-02: Invalid / Malformed JSON-LD** | JSON-LD syntax errors, broken schema nesting, or missing required schema.org properties (`name`, `price`, `currency`, `image`). | JSON parser exception on `<script>` contents or schema validator missing required properties per schema.org specification. | Schema is rejected by Google, Bing, and AI ingestors, voiding rich results and structured grounding. | **High** | **High** | Deterministic (JSON syntax parser + Schema validator) | Non-standard proprietary JSON payloads in script tags. *Mitigation*: Only validate scripts with `@context: "https://schema.org"`. | Correct JSON syntax formatting and populate all mandatory schema.org fields according to official specifications. |
| **C-03: Structured-to-Visible Fact Conflict** | JSON-LD declared values (e.g. price `$49.00`, availability `OutOfStock`) directly contradict visible DOM text (e.g. `$59.00`, `In Stock`). | Discrepancy between parsed JSON-LD entity properties and visible rendered DOM text values. | Automated extractors and search agents encounter contradictory factual signals for the same offering, impairing grounding consistency during retrieval. | **Critical** | **High** | Hybrid (Deterministic extraction + LLM semantic alignment) | Currency conversion or geo-located pricing variations. *Mitigation*: Compare normalized currency strings. | Synchronize tag managers and server-rendered structured data to derive directly from the single source of truth database. |
| **C-04: Missing Entity Disambiguation (`sameAs`)** | `Organization` or `Brand` schema lacks `sameAs` authority links to Wikidata, Wikipedia, official social handles, or registry IDs. | `Organization` JSON-LD present, but `sameAs` array is empty or missing external verified URI references. | AI search models cannot resolve entity collisions or link the brand to established global knowledge graphs. | **Medium** | **High** | Deterministic (JSON-LD property audit) | Very small unverified personal blogs. *Mitigation*: Downgrade to Info severity for personal portfolio archetypes. | Add `sameAs` array in `Organization` schema pointing to official Wikidata QID, LinkedIn, Twitter/X, and Crunchbase profiles. |

---

### Category D: Fact Consistency, Freshness & Entity Clarity

| Check | Problem | Evidence | Impact | Severity | Confidence | Detection | False Positives | Fix |
|---|---|---|---|---|---|---|---|---|
| **D-01: Temporal Staleness Signals** | Copyright year is >= 2 years outdated, or `dateModified` / `datePublished` is ancient on time-sensitive product/service offerings. | Footer text matches `© 2021` or `dateModified` meta tag shows stale timestamp while competitor data has updated. | AI systems downweight content relevance, flagging the brand as potentially abandoned or out of business. | **Medium** | **High** | Deterministic (Regex timestamp & footer parser) | Historical archive articles where old publish date is accurate. *Mitigation*: Restrict to home/product/pricing/contact pages. | Implement automated copyright year rendering and ensure `dateModified` reflects actual updates to product catalog. |
| **D-02: Internal Cross-Page Fact Contradiction** | Conflicting prices, phone numbers, addresses, or product claims across different pages of the same domain. | Discrepancy between entity values on `/pricing` vs `/product-detail` or footer contact info vs `/contact-us`. | Causes automated extractors to encounter contradictory signals, creating retrieval and quotation inconsistency across first-party pages. | **High** | **Medium** | Hybrid (Entity extraction + LLM consistency cross-check) | Tiered pricing models where different packages have distinct prices. *Mitigation*: Group entities by package identifier. | Audit and unify core factual claims across all site landing pages into a single centralized content repository. |
| **D-03: Unclear Entity Identity / Value Proposition** | The website fails to explicitly state who the company is, what problem it solves, and what products/services it provides within the initial viewport. | Absence of clear organization identity, H1 tag, or value proposition in top-level DOM nodes. | AI summarizers produce vague descriptions ("a platform that provides solutions") instead of precise category-defining citations. | **High** | **Medium** | LLM Semantic (Page orientation evaluation) | Highly artistic boutique landing pages with video-only hero. | Craft a clear, unambiguous H1 header and concise subhead on the homepage stating the core offering and target audience. |

---

### Category E: On-Site Engagement, Orientation & Intent Hierarchy

| Check | Problem | Evidence | Impact | Severity | Confidence | Detection | False Positives | Fix |
|---|---|---|---|---|---|---|---|---|
| **E-01: Broken Information Hierarchy** | Missing `<h1>`, multiple competing `<h1>` tags, or skipped heading levels (e.g. `<h1>` immediately followed by `<h3>` or `<h5>`). | DOM heading audit: `count(h1) == 0` or `count(h1) > 2` or sequence contains level skips `H1 -> H3`. | Human readers cannot skim; AI retrieval chunks lose hierarchical context during embedding and vector search. | **Medium** | **High** | Deterministic (DOM tree traversal) | Headings visually styled with CSS classes instead of tags. *Mitigation*: Verify visual font sizes vs semantic tags. | Structure pages with exactly one descriptive `<h1>` followed by logical, sequential `<h2>` and `<h3>` section headers. |
| **E-02: Buried Critical Answers** | Crucial user questions (pricing, refund policy, shipping timelines, support access) buried >3 scrolls down without clear navigation or anchor links. | Critical commercial/FAQ answers positioned after >2000px vertical DOM offset with zero table-of-contents or anchor links. | High bounce rates for visitors landing with high purchase or support intent; AI direct answers fail to locate target text. | **High** | **Medium** | Hybrid (DOM layout offset + semantic query matching) | Long-form editorial storytelling articles. *Mitigation*: Only evaluate commercial and FAQ/Support page archetypes. | Elevate key factual answers to the top third of the page or provide sticky jump links / summary callout cards. |
| **E-03: Dead-End Landing / Missing Next Steps** | Landing page lacks clear call-to-action (CTA), next-step guidance, related products, or clear contact paths. | No button or link with actionable verbs (`Get Started`, `Contact Us`, `Buy Now`, `Learn More`) within content flow. | Visitor engagement evaporates immediately after reading; high bounce rate and low conversion velocity. | **High** | **High** | Deterministic / Semantic (Interactive element parser) | Informational legal disclaimer / privacy policy pages. *Mitigation*: Exclude `/privacy`, `/terms`, `/legal` paths. | Add prominent, contextually relevant CTAs and related navigation cards at the conclusion of every substantive section. |

---

### Category F: Proactive Recommendations (Beyond Explicit Defects)

| Opportunity | Description | Evidence / Trigger | Strategic Value | Priority |
|---|---|---|---|---|
| **F-01: AI-Grounding FAQ Markup** | Implement dedicated FAQ structured data (`FAQPage`) for high-friction product/pricing questions. | Page contains QA-style content but lacks schema representation. | Enables AI search engines (Perplexity, ChatGPT Search) to directly cite bulleted answers with brand attribution. | **High** |
| **F-02: Structured Author & Organization Authority** | Link author bylines to external professional profiles (`Person` schema with `alumniOf`, `sameAs`). | Articles have text bylines without schema author graph. | Elevates E-E-A-T (Experience, Expertise, Authoritativeness, Trustworthiness) scoring in AI source ranking. | **Medium** |
| **F-03: Enhanced Machine-Readable OpenGraph & Microdata** | Provide rich `og:title`, `og:description`, `og:image` and Twitter card metadata matching entity facts. | Missing or truncated meta tags across secondary product routes. | Ensures consistent thumbnail, title, and descriptive snippet generation across conversational AI cards. | **Medium** |

---

## 2. Proposed Agent Skill Decomposition

To achieve **genuine separation of concerns**, comply with the `agentskills.io` standard, and avoid artificial padding, we propose a modular architecture consisting of **1 orchestrator entrypoint skill** and **4 specialized domain skills**:

```
brand-ai-readiness-audit/               <-- Marketplace Root
├── marketplace.json                   <-- Top-level manifest (designates entrypoint)
├── skills/
│   ├── audit-orchestrator/            <-- [ENTRYPOINT]: Plans, schedules, deduplicates, prioritizes, emits final report
│   │   ├── SKILL.md
│   │   ├── scripts/orchestrate.py
│   │   └── references/report-schema.json
│   │
│   ├── crawl-render-audit/            <-- [SKILL 1]: Crawlability, robots.txt, HTTP headers, Raw vs Rendered DOM gaps
│   │   ├── SKILL.md
│   │   ├── scripts/inspect_crawler.py
│   │   └── references/bot-user-agents.json
│   │
│   ├── structured-data-entity-audit/  <-- [SKILL 2]: Schema.org validation, entity clarity, visible-to-schema consistency
│   │   ├── SKILL.md
│   │   ├── scripts/validate_schema.py
│   │   └── references/schema-types.json
│   │
│   ├── freshness-corroboration-audit/ <-- [SKILL 3]: Temporal staleness, cross-page factual consistency, conflict checks
│   │   ├── SKILL.md
│   │   ├── scripts/check_freshness.py
│   │   └── references/temporal-rules.json
│   │
│   └── engagement-audit/              <-- [SKILL 4]: Orientation, information hierarchy, intent continuity, next steps
│       ├── SKILL.md
│       ├── scripts/inspect_engagement.py
│       └── references/heading-rules.json
│
└── README.md                          <-- Comprehensive marketplace documentation
```

### Skill Separation Justification (No Padding)

1. **`audit-orchestrator` (Entrypoint)**:
   - *Role*: Validates input URL, computes crawl boundaries, coordinates specialized skill execution, aggregates evidence payloads, normalizes and deduplicates findings, calculates severity/priority matrices, and formats the final JSON/Markdown report.
   - *Why Separate*: Decouples orchestration logic from domain inspection heuristics.

2. **`crawl-render-audit` (Domain Skill 1)**:
   - *Role*: Focuses exclusively on network, accessibility, crawler directives, and HTML transport barriers (Raw HTML vs Headless Browser Rendered DOM token diffing, non-text image content locking).
   - *Why Separate*: Requires headless browser instrumentation and HTTP network inspection capabilities.

3. **`structured-data-entity-audit` (Domain Skill 2)**:
   - *Role*: Focuses on formal machine-readable knowledge graphs (JSON-LD syntax, schema.org conformance, `sameAs` entity graph linking, visible text vs structured property alignment).
   - *Why Separate*: Deals with formal semantics, AST schema validation, and graph structure.

4. **`freshness-corroboration-audit` (Domain Skill 3)**:
   - *Role*: Focuses on temporal signals (copyright, modified dates), cross-page fact agreement, and detection of conflicting claims across the domain's indexed assets.
   - *Why Separate*: Operates across aggregated multi-page corpora rather than single-page DOM trees.

5. **`engagement-audit` (Domain Skill 4)**:
   - *Role*: Focuses exclusively on the human visitor's experience (Above-The-Fold orientation, semantic heading trees, buried answer discoverability, and contextual next-step / CTA guidance).
   - *Why Separate*: Evaluates UX information architecture and intent continuity, distinct from backend schema or network transport.
