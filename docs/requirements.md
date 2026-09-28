# System Requirements & Constraints Specification

## 1. Overview & Objectives
The system is an **Agent Skill Marketplace** conforming to the `agentskills.io` standard, designed to empower general AI agents to autonomously audit any arbitrary website URL across two primary dimensions:
1. **AI Discoverability (Off-site)**: Identifying why an AI assistant/search engine fails to crawl, read, understand, corroborate, or cite a brand's web assets.
2. **On-site Engagement (On-site)**: Identifying why human visitors arriving on the website fail to orient, find answers, or navigate toward meaningful next steps.

---

## 2. Hard Requirements & Guardrails

### 2.1 Marketplace & Skill Packaging
- **Marketplace Manifest**: Must contain a root-level `marketplace.json` that lists all skills and designates **exactly one entrypoint skill** (`"entrypoint": true`).
- **Skill Format**: Each skill directory must strictly adhere to the `agentskills.io` specification:
  - `SKILL.md` with standard YAML frontmatter (`name`, `description`, `license`) and clean procedural markdown.
  - Progressive disclosure: High-level instructions in `SKILL.md`, executable inspection logic in `scripts/`, reference schemas/rules in `references/`.
- **Packaging Constraints**:
  - Entire marketplace repository/submission ZIP must be **<= 50 MB**.
  - **Zero pre-trained weights**: No bundled binary models, PyTorch/TensorFlow weights, or heavy machine learning artifacts.
  - Self-contained portable dependencies.

### 2.2 Execution & Safety Guardrails
- **Recommend-Only & Read-Only**: Absolutely no destructive, mutating, state-altering, or administrative actions on audited websites.
- **No Authenticated Access**: Never bypass authentication gates, paywalls, or login screens.
- **Robots.txt Adherence**: Must fetch, parse, and strictly respect `robots.txt` disallow/allow rules during crawling.
- **Bounded Runtime**: Complete audit must execute in **< 5 minutes** on standard commodity hardware for a typical website (e.g., 10–25 representative pages).
- **Concurrency & Resource Throttling**: Bounded crawl depth (e.g., max depth 2-3), bounded page ceiling (e.g., 15-30 pages), request timeouts (5-10s per request), and polite rate limiting.

### 2.3 Generalization Across Unseen Domains
- **Zero Hardcoding**: Absolutely no hardcoded domain names, brand identifiers, fixed URL paths, or site-specific CSS selectors.
- **Multi-Archetype Support**: Must adapt dynamically to varied website models:
  - E-Commerce & Retail
  - B2B SaaS & Enterprise Software
  - Professional & Local Services
  - Publishers, News & Media
  - Corporate Portfolios & Non-Profits

---

## 3. Output Schema Specification

The designated entrypoint skill must emit a single unified JSON audit report conforming to the following schema:

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "WebsiteAuditReport",
  "type": "object",
  "required": ["site", "audited_at", "summary", "findings"],
  "properties": {
    "site": { "type": "string", "format": "uri-reference" },
    "audited_at": { "type": "string", "format": "date-time" },
    "summary": {
      "type": "object",
      "required": ["total_findings", "critical", "high", "medium"],
      "properties": {
        "total_findings": { "type": "integer", "minimum": 0 },
        "critical": { "type": "integer", "minimum": 0 },
        "high": { "type": "integer", "minimum": 0 },
        "medium": { "type": "integer", "minimum": 0 },
        "low": { "type": "integer", "minimum": 0 },
        "info": { "type": "integer", "minimum": 0 }
      }
    },
    "findings": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["id", "title", "severity", "evidence", "suggested_action"],
        "properties": {
          "id": { "type": "string", "pattern": "^F-[0-9]{3,}$" },
          "title": { "type": "string" },
          "category": { 
            "type": "string", 
            "enum": ["crawlability", "machine_readability", "structured_data", "entity_clarity", "freshness_corroboration", "on_site_engagement"] 
          },
          "severity": { "type": "string", "enum": ["critical", "high", "medium", "low", "info"] },
          "confidence": { "type": "string", "enum": ["high", "medium", "low"] },
          "evidence": { "type": "string" },
          "affected_urls": { "type": "array", "items": { "type": "string" } },
          "root_cause": { "type": "string" },
          "impact": { "type": "string" },
          "detection_method": { "type": "string", "enum": ["deterministic", "llm_semantic", "hybrid"] },
          "suggested_action": {
            "type": "object",
            "required": ["summary", "priority"],
            "properties": {
              "summary": { "type": "string" },
              "implementation_details": { "type": "string" },
              "priority": { "type": "string", "enum": ["critical", "high", "medium", "low"] }
            }
          }
        }
      }
    },
    "proactive_recommendations": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["id", "title", "opportunity", "suggested_action"],
        "properties": {
          "id": { "type": "string" },
          "title": { "type": "string" },
          "opportunity": { "type": "string" },
          "suggested_action": {
            "type": "object",
            "required": ["summary", "priority"],
            "properties": {
              "summary": { "type": "string" },
              "priority": { "type": "string", "enum": ["high", "medium", "low"] }
            }
          }
        }
      }
    }
  }
}
```

---

## 4. Evaluation Rubric Alignment

| Rubric Dimension | Evaluation Standard | Design Implementation |
|---|---|---|
| **Detection Accuracy** | Accurately identifies real technical defects with high precision and low false positives. | Multi-tier evidence verification; deterministic validation before semantic flagging; archetype-aware rules. |
| **Suggested-Action Quality** | Specific, mechanism-sound, root-cause-resolving fixes; non-obvious proactive guidance. | Action templates specify *what*, *where*, *how*, and *why*; includes exact markup/tag code structures. |
| **Output Design** | Actionable, structured, severity-ranked, readable by technical and non-technical stakeholders. | Strict JSON schema + clear executive summaries + transparent evidence trails. |
| **Skill-Format & Engineering Hygiene** | Standard compliance (`agentskills.io`), clean manifest, modular code, error-resilient, read-only. | Strict validation against agentskills specification; graceful timeouts and fallback mechanisms. |
| **Marketplace Composition** | Meaningful separation of concerns without artificial skill proliferation. | 4 specialized domain skills coordinated by 1 entrypoint orchestrator. |
| **Generalization** | Flawlessly evaluates unseen, heterogeneous websites without hardcoded rules. | Adaptive pattern detection and heuristics driven by semantic HTML, schema.org, and response profiles. |
