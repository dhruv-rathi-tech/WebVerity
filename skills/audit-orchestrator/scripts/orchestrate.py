"""
Audit Orchestrator Entrypoint Script.
Coordinates the end-to-end website audit pipeline:
1. Bounded Crawl & Evidence Gathering
2. Domain Skill Execution (Crawl/Render, Structured Data, Freshness, Engagement)
3. Cross-Skill Normalization & Semantic Deduplication
4. Severity / Priority Aggregation & Final Report Synthesis
"""

import os
import sys
import json
import asyncio
import datetime
import importlib.util
from typing import List, Dict, Any, Optional

# Ensure workspace root in sys.path
_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from core.models import CrawlContext, PageEvidence, SiteArchetype, PageArchetype
from core.crawler import crawl_site
from core.url_utils import normalize_url

# Dynamic loader for domain skill execution
def _load_skill_fn(skill_folder: str, script_name: str, fn_name: str):
    skill_path = os.path.join(_ROOT, "skills", skill_folder, "scripts", script_name)
    spec = importlib.util.spec_from_file_location(f"{skill_folder}_{fn_name}", skill_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return getattr(mod, fn_name)


class AuditOrchestrator:
    """
    Coordinates multi-skill audit execution, deduplication, and standardized report generation.
    """

    def __init__(self):
        # Lazily load domain skill handlers
        self._inspect_crawl_render = _load_skill_fn("crawl-render-audit", "inspect_crawler.py", "inspect_crawl_and_render")
        self._validate_structured_data = _load_skill_fn("structured-data-entity-audit", "validate_schema.py", "validate_structured_data")
        self._check_freshness = _load_skill_fn("freshness-corroboration-audit", "check_freshness.py", "check_freshness_and_corroboration")
        self._inspect_engagement = _load_skill_fn("engagement-audit", "inspect_engagement.py", "inspect_engagement")

    def run(
        self,
        target_url: str,
        crawl_options: Optional[Dict[str, Any]] = None,
        external_records: Optional[List[Dict[str, Any]]] = None,
        existing_context: Optional[CrawlContext] = None
    ) -> Dict[str, Any]:
        """
        Executes complete audit pipeline for target_url or pre-crawled CrawlContext.
        """
        audited_at = datetime.datetime.now(datetime.timezone.utc).isoformat()
        
        # 1. Input Validation & URL Normalization
        normalized = normalize_url(target_url) if target_url else ""
        if not normalized or not normalized.startswith("http"):
            return {
                "site": target_url or "invalid-url",
                "audited_at": audited_at,
                "summary": {
                    "total_findings": 0,
                    "critical": 0,
                    "high": 0,
                    "medium": 0,
                    "low": 0,
                    "info": 0
                },
                "findings": [],
                "proactive_recommendations": []
            }

        # 2. Crawl & Evidence Gathering (if not already provided)
        if existing_context is not None:
            crawl_context = existing_context
        else:
            opts = crawl_options or {}
            max_pages = opts.get("max_pages", 10)
            max_depth = opts.get("max_depth", 2)
            timeout = opts.get("timeout", 15.0)

            try:
                crawl_context = asyncio.run(
                    crawl_site(
                        root_url=normalized,
                        max_pages=max_pages,
                        max_depth=max_depth,
                        timeout_seconds=timeout
                    )
                )
            except Exception as e:
                # Graceful crawl failure handling
                return {
                    "site": normalized,
                    "audited_at": audited_at,
                    "summary": {
                        "total_findings": 1,
                        "critical": 1,
                        "high": 0,
                        "medium": 0,
                        "low": 0,
                        "info": 0
                    },
                    "findings": [{
                        "id": "F-001",
                        "title": "Crawl transport connection failure",
                        "category": "crawlability",
                        "severity": "critical",
                        "confidence": "high",
                        "observation": f"Could not establish network connection to target host: {str(e)}",
                        "evidence": f"URL: {normalized}\nException: {type(e).__name__}",
                        "root_cause": "The target web server is unreachable, DNS failed to resolve, or the connection timed out.",
                        "impact": "No web pages could be fetched or analyzed for AI discoverability.",
                        "detection_method": "deterministic",
                        "affected_urls": [normalized],
                        "suggested_action": {
                            "summary": "Verify target website host availability and public reachability.",
                            "priority": "critical"
                        }
                    }],
                    "proactive_recommendations": []
                }

        # 3. Check for transport network reachability failure
        if crawl_context.pages and all(p.status_code == 0 for p in crawl_context.pages):
            err_desc = crawl_context.pages[0].error_message or "Connection timed out or host unreachable."
            return {
                "site": normalized,
                "audited_at": audited_at,
                "summary": {
                    "total_findings": 1,
                    "critical": 1,
                    "high": 0,
                    "medium": 0,
                    "low": 0,
                    "info": 0
                },
                "findings": [{
                    "id": "F-001",
                    "title": "Crawl transport connection failure",
                    "category": "crawlability",
                    "severity": "critical",
                    "confidence": "high",
                    "observation": f"Could not establish network connection to target host: {err_desc}",
                    "evidence": f"URL: {normalized}\nHost: {crawl_context.domain}\nError: {err_desc}",
                    "root_cause": "The target web server is unreachable, DNS failed to resolve, or the connection timed out.",
                    "impact": "No web pages could be fetched or analyzed for AI discoverability.",
                    "detection_method": "deterministic",
                    "affected_urls": [normalized],
                    "suggested_action": {
                        "summary": "Verify target website host availability and public reachability.",
                        "priority": "critical"
                    }
                }],
                "proactive_recommendations": []
            }

        # 4. Domain Skill Execution with Fault Isolation
        raw_findings: List[Dict[str, Any]] = []

        # Skill 1: Crawl & Render Audit
        try:
            crawl_findings = self._inspect_crawl_render(crawl_context)
            raw_findings.extend(crawl_findings)
        except Exception as e:
            raw_findings.append({
                "id": "ERR-CR",
                "title": f"Crawl/Render domain skill failure: {str(e)}",
                "category": "crawlability",
                "severity": "info",
                "confidence": "low",
                "observation": f"Skill execution encountered error: {str(e)}",
                "evidence": f"Domain: {crawl_context.domain}",
                "root_cause": "Internal domain skill error during inspection.",
                "impact": "Partial audit metrics for crawl/render could not be computed.",
                "detection_method": "deterministic",
                "affected_urls": [crawl_context.root_url],
                "suggested_action": {
                    "summary": "Check system logs for skill execution details.",
                    "priority": "low"
                }
            })

        # Skill 2: Structured Data & Entity Audit
        try:
            schema_findings = self._validate_structured_data(crawl_context)
            raw_findings.extend(schema_findings)
        except Exception as e:
            pass

        # Skill 3: Freshness & Corroboration Audit
        try:
            freshness_findings = self._check_freshness(crawl_context, external_records)
            raw_findings.extend(freshness_findings)
        except Exception as e:
            pass

        # Skill 4: Engagement Audit
        try:
            engagement_findings = self._inspect_engagement(crawl_context)
            raw_findings.extend(engagement_findings)
        except Exception as e:
            pass

        # 4. Cross-Skill Semantic Deduplication
        deduplicated = self._deduplicate_findings(raw_findings)

        # 5. Schema Normalization & Summary Aggregation
        return self._synthesize_report(crawl_context.root_url, audited_at, deduplicated)

    def _deduplicate_findings(self, findings: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Deduplicates identical issues across skills for the same URL scope,
        merging distinct evidence and upgrading to the highest reported severity.
        Preserves findings across distinct URLs (e.g. separate product pages).
        """
        import re
        unique_map: Dict[str, Dict[str, Any]] = {}
        severity_rank = {"critical": 5, "high": 4, "medium": 3, "low": 2, "info": 1}

        for f in findings:
            urls_key = ",".join(sorted(f.get("affected_urls", [])))
            category = f.get("category", "")
            raw_rc = f.get("root_cause", "")
            title = f.get("title", "")
            
            # Root cause signature captures the specific underlying technical cause
            rc_sig = re.sub(r"[^a-z0-9]", "", (raw_rc[:60] if raw_rc else title[:40]).lower())
            fingerprint = f"{category}|{urls_key}|{rc_sig}"

            if fingerprint in unique_map:
                existing = unique_map[fingerprint]
                curr_rank = severity_rank.get(f.get("severity", "info"), 1)
                prev_rank = severity_rank.get(existing.get("severity", "info"), 1)

                # Merge evidence if distinct
                new_ev = f.get("evidence", "").strip()
                existing_ev = existing.get("evidence", "").strip()
                if new_ev and new_ev not in existing_ev:
                    existing["evidence"] = existing_ev + "\n" + new_ev

                if curr_rank > prev_rank:
                    existing["severity"] = f.get("severity", "info")
                    existing["title"] = f.get("title", existing.get("title"))
                    existing["observation"] = f.get("observation", existing.get("observation"))
            else:
                unique_map[fingerprint] = dict(f)

        return list(unique_map.values())

    def _synthesize_report(
        self,
        site_url: str,
        audited_at: str,
        findings_list: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Formats normalized findings and recommendations into standard report schema.
        Distinguishes confirmed defects from proactive recommendations.
        """
        summary_counts = {
            "total_findings": 0,
            "critical": 0,
            "high": 0,
            "medium": 0,
            "low": 0,
            "info": 0
        }

        normalized_findings: List[Dict[str, Any]] = []
        proactive_recommendations: List[Dict[str, Any]] = []

        counter = 1
        rec_counter = 1

        for f in findings_list:
            sev = f.get("severity", "info").lower()
            if sev not in summary_counts:
                sev = "info"

            # Check if this finding is a purely proactive recommendation (e.g. optional sameAs enrichment)
            if f.get("category") == "entity_clarity" and "sameAs" in f.get("title", ""):
                proactive_recommendations.append({
                    "id": f"REC-{rec_counter:03d}",
                    "title": f.get("title", "Entity Graph Enrichment"),
                    "opportunity": f.get("observation", "Add external authority sameAs references to Organization schema."),
                    "suggested_action": {
                        "summary": f.get("suggested_action", {}).get("summary", "Add relevant authoritative sameAs identifiers."),
                        "priority": "low"
                    }
                })
                rec_counter += 1
                continue

            summary_counts[sev] += 1
            summary_counts["total_findings"] += 1

            norm_f = {
                "id": f"F-{counter:03d}",
                "title": f.get("title", "Audit Finding"),
                "category": f.get("category", "crawlability"),
                "severity": sev,
                "confidence": f.get("confidence", "high"),
                "observation": f.get("observation", ""),
                "evidence": f.get("evidence", ""),
                "root_cause": f.get("root_cause", ""),
                "impact": f.get("impact", ""),
                "detection_method": f.get("detection_method", "deterministic"),
                "affected_urls": f.get("affected_urls", [site_url]),
                "suggested_action": {
                    "summary": f.get("suggested_action", {}).get("summary", "Remediate issue."),
                    "priority": f.get("suggested_action", {}).get("priority", sev if sev != "info" else "low")
                }
            }
            if "implementation_details" in f.get("suggested_action", {}):
                norm_f["suggested_action"]["implementation_details"] = f["suggested_action"]["implementation_details"]

            normalized_findings.append(norm_f)
            counter += 1

        # Sort findings by severity (critical -> high -> medium -> low -> info)
        severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}
        normalized_findings.sort(key=lambda x: severity_order.get(x["severity"], 5))

        # Re-index IDs sequentially
        for idx, f in enumerate(normalized_findings, 1):
            f["id"] = f"F-{idx:03d}"

        return {
            "site": site_url,
            "audited_at": audited_at,
            "summary": summary_counts,
            "findings": normalized_findings,
            "proactive_recommendations": proactive_recommendations
        }


def orchestrate_audit(
    url: str,
    crawl_options: Optional[Dict[str, Any]] = None,
    external_records: Optional[List[Dict[str, Any]]] = None
) -> Dict[str, Any]:
    """
    Main entrypoint function for executing the audit orchestrator.
    """
    orchestrator = AuditOrchestrator()
    return orchestrator.run(url, crawl_options=crawl_options, external_records=external_records)


def render_markdown_report(report: Dict[str, Any]) -> str:
    """
    Renders standardized audit report dictionary into clean, human-readable GitHub-flavored Markdown.
    Preserves site, audited_at, summary, findings (id, title, category, severity, confidence,
    observation, evidence, root_cause, impact, affected_urls, suggested_action, priority),
    and proactive recommendations.
    """
    site = report.get("site", "Unknown")
    audited_at = report.get("audited_at", "")
    summary = report.get("summary", {})
    total = summary.get("total_findings", 0)
    crit = summary.get("critical", 0)
    high = summary.get("high", 0)
    med = summary.get("medium", 0)
    low = summary.get("low", 0)
    info = summary.get("info", 0)

    status = "HEALTHY (0 Defects Detected)" if total == 0 else f"ACTION REQUIRED ({total} Findings Detected)"

    lines = [
        "# WebVerity - AI Readiness & Website Intelligence Report",
        "",
        f"**Target Site:** `{site}`  ",
        f"**Audited At:** `{audited_at}`  ",
        f"**Overall Status:** {status}",
        "",
        "---",
        "",
        "## Executive Summary",
        "",
        "| Total Findings | Critical | High | Medium | Low | Info |",
        "|:---:|:---:|:---:|:---:|:---:|:---:|",
        f"| **{total}** | {crit} | {high} | {med} | {low} | {info} |",
        "",
        "---",
        "",
        "## Audit Findings",
        ""
    ]

    findings = report.get("findings", [])
    if not findings:
        lines.append("*No defects or discoverability barriers detected on audited pages.*")
        lines.append("")
    else:
        for f in findings:
            sev = f.get("severity", "info").upper()
            title = f.get("title", "Finding")
            fid = f.get("id", "F-???")
            cat = f.get("category", "").replace("_", " ").title()
            conf = f.get("confidence", "high").title()
            method = f.get("detection_method", "deterministic").title()

            lines.append(f"### [{sev}] {title}")
            lines.append(f"- **ID:** `{fid}` | **Category:** {cat} | **Severity:** {sev} | **Confidence:** {conf}")
            lines.append(f"- **Detection Method:** {method}")

            urls = f.get("affected_urls", [])
            if urls:
                lines.append("- **Affected URLs:**")
                for u in urls[:5]:
                    lines.append(f"  - `{u}`")
                if len(urls) > 5:
                    lines.append(f"  - *(+{len(urls) - 5} more)*")

            lines.append(f"- **Observation:** {f.get('observation', '')}")
            
            ev = f.get("evidence", "")
            if "\n" in ev:
                lines.append("- **Evidence:**")
                lines.append("  ```")
                for ev_line in ev.splitlines():
                    lines.append(f"  {ev_line}")
                lines.append("  ```")
            else:
                lines.append(f"- **Evidence:** `{ev}`")

            lines.append(f"- **Root Cause:** {f.get('root_cause', '')}")
            lines.append(f"- **Impact:** {f.get('impact', '')}")

            act = f.get("suggested_action", {})
            prio = act.get("priority", sev.lower()).title()
            lines.append(f"- **Suggested Action (Priority: {prio}):** {act.get('summary', '')}")
            if "implementation_details" in act:
                lines.append(f"  - *Implementation Guidance:* {act['implementation_details']}")

            lines.append("")

    proactive = report.get("proactive_recommendations", [])
    if proactive:
        lines.append("---")
        lines.append("")
        lines.append("## Proactive Recommendations")
        lines.append("")
        lines.append("> [!NOTE]")
        lines.append("> These items are not defects, but proactive optimizations to enhance entity grounding and knowledge graph authority.")
        lines.append("")
        for rec in proactive:
            rid = rec.get("id", "REC-???")
            rtitle = rec.get("title", "Recommendation")
            opp = rec.get("opportunity", "")
            ract = rec.get("suggested_action", {})
            rprio = ract.get("priority", "low").title()
            rsum = ract.get("summary", "")

            lines.append(f"### [{rid}] {rtitle}")
            lines.append(f"- **Opportunity:** {opp}")
            lines.append(f"- **Suggested Enhancement (Priority: {rprio}):** {rsum}")
            lines.append("")

    return "\n".join(lines)


def main(argv: Optional[List[str]] = None) -> int:
    """
    Canonical CLI entrypoint for orchestrating a website audit.
    Supports JSON and Markdown formatting, file output, and custom crawl options.
    """
    import argparse
    parser = argparse.ArgumentParser(
        description="WebVerity CLI — AI Readiness & Website Intelligence Workbench. Audits websites for AI discoverability and on-site engagement.",
        prog="audit"
    )
    parser.add_argument("url", nargs="?", help="Target website URL to audit (e.g. https://example.com)")
    parser.add_argument("-u", "--url", dest="opt_url", help="Alternative flag for target URL")
    parser.add_argument("-f", "--format", choices=["json", "markdown", "both"], default="json", help="Output format (default: json)")
    parser.add_argument("-o", "--output", help="Optional path to write output file")
    parser.add_argument("--max-pages", type=int, default=10, help="Maximum pages to crawl (bounded <= 20, default: 10)")
    parser.add_argument("--max-depth", type=int, default=2, help="Maximum crawl depth (default: 2)")
    parser.add_argument("--timeout", type=float, default=15.0, help="Overall audit timeout in seconds (default: 15.0)")
    parser.add_argument("--external", help="Optional path to JSON file containing third-party corroboration records")
    parser.add_argument("-q", "--quiet", action="store_true", help="Quiet mode (suppress progress messages)")

    args = parser.parse_args(argv)
    target_url = args.url or args.opt_url

    if not target_url:
        parser.print_help(sys.stderr)
        return 1

    external_records = None
    if args.external:
        try:
            with open(args.external, "r", encoding="utf-8") as f:
                external_records = json.load(f)
        except Exception as e:
            if not args.quiet:
                sys.stderr.write(f"Warning: Could not read external records file: {e}\n")

    crawl_options = {
        "max_pages": min(max(1, args.max_pages), 20),
        "max_depth": min(max(1, args.max_depth), 3),
        "timeout": max(1.0, args.timeout)
    }

    report = orchestrate_audit(
        url=target_url,
        crawl_options=crawl_options,
        external_records=external_records
    )

    json_str = json.dumps(report, indent=2)
    md_str = render_markdown_report(report)

    if args.format == "json":
        output_content = json_str
    elif args.format == "markdown":
        output_content = md_str
    else:  # both
        output_content = f"--- JSON REPORT ---\n{json_str}\n\n--- MARKDOWN REPORT ---\n{md_str}"

    if args.output:
        try:
            with open(args.output, "w", encoding="utf-8") as out_f:
                out_f.write(output_content)
            if not args.quiet:
                sys.stderr.write(f"Report successfully written to {args.output}\n")
        except Exception as e:
            sys.stderr.write(f"Error writing to output file: {e}\n")
            return 1
    else:
        print(output_content)

    return 0


if __name__ == "__main__":
    sys.exit(main())
