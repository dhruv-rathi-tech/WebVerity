"""
Freshness & Entity Corroboration Analyzer.
Constructs multi-page entity consistency matrices, audits temporal validity,
and reconciles first-party claims against external corroboration records.
"""

import re
import datetime
from dataclasses import dataclass
from typing import List, Dict, Any, Tuple, Optional, Set
from core.models import CrawlContext, PageEvidence, PageArchetype, SiteArchetype


@dataclass
class FactualObservation:
    entity: str
    entity_key: str
    attribute: str
    value: str
    display_value: str
    currency: Optional[str]
    context_type: str
    source: str
    url: str
    snippet: str
    region: Optional[str] = None


def _extract_region_from_url(url: str) -> Optional[str]:
    try:
        from urllib.parse import urlparse
        path = urlparse(url).path.lower()
        m = re.search(r"^/(us|ca|uk|gb|eu|au|nz|de|fr|in|jp|es|it|nl)(?:/|$)", path)
        if m:
            return m.group(1)
        m_locale = re.search(r"^/[a-z]{2}-([a-z]{2})(?:/|$)", path)
        if m_locale:
            return m_locale.group(1)
    except Exception:
        pass
    return None


def _normalize_entity_name(name: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9\s]", "", name).strip().lower()
    return " ".join(cleaned.split())


def _normalize_phone_number(raw_phone: str) -> Optional[str]:
    digits = re.sub(r"\D", "", raw_phone)
    if len(digits) == 11 and digits.startswith("1"):
        digits = digits[1:]
    if len(digits) == 10:
        return digits
    return None


def analyze_cross_page_consistency(crawl_context: CrawlContext) -> List[Dict[str, Any]]:
    """
    Builds a multi-page entity index across crawled URLs and detects genuine first-party factual contradictions.
    Compares observations only when:
    1. They refer to the same entity.
    2. They refer to the same attribute.
    3. The values are materially different.
    4. The difference cannot be explained by legitimate context (sale vs msrp, introductory vs standard, currencies).
    """
    contradictions: List[Dict[str, Any]] = []
    observations: List[FactualObservation] = []

    price_pattern = re.compile(
        r"(?:([\$\€\£\₹\¥]|USD|INR|EUR|GBP|CAD|AUD)\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)|\b(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)\s*(USD|INR|EUR|dollars|rupees)\b)",
        re.IGNORECASE
    )
    plan_pattern = re.compile(
        r"\b((?:Free|Starter|Basic|Pro|Professional|Business|Team|Teams|Growth|Premium|Plus|Enterprise|Standard|Personal|Developer)(?:\s+(?:Plus|Pro|Max|Lite|Ultra|Enterprise|Advanced|Ultimate))?)\b(?:\s+(?:Plan|Tier|Edition|Package|Subscription))?",
        re.IGNORECASE
    )
    phone_pattern = re.compile(r"(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}")

    for page in crawl_context.pages:
        if page.status_code != 200:
            continue

        text = page.raw_text or ""
        url = page.url
        arch_val = page.page_archetype.value if hasattr(page.page_archetype, "value") else str(page.page_archetype)
        url_region = _extract_region_from_url(url)
        is_historical_page = (arch_val == "article") or any(
            seg in url.lower() for seg in ("/blog/", "/news/", "/press/", "/archive/", "/changelog/", "/releases/", "/updates/")
        )

        # 1. Structured JSON-LD Observations
        for jb in getattr(page, "json_ld", []):
            if getattr(jb, "has_syntax_error", False) or not getattr(jb, "parsed_data", None):
                continue
            nodes = [jb.parsed_data] if isinstance(jb.parsed_data, dict) else (jb.parsed_data if isinstance(jb.parsed_data, list) else [])
            for node in nodes:
                if not isinstance(node, dict):
                    continue
                node_type = str(node.get("@type", ""))

                # Product & Offer
                if "Product" in node_type or "Offer" in node_type:
                    prod_name = str(node.get("name", "")).strip() or page.title.split("|")[0].split("-")[0].strip()
                    if not prod_name or len(prod_name) < 2:
                        continue

                    price_val = None
                    curr_val = "USD"

                    if "price" in node:
                        price_val = str(node["price"]).replace(",", "").strip()
                        curr_val = str(node.get("priceCurrency", "USD")).strip().upper()
                    elif "offers" in node and isinstance(node["offers"], dict):
                        offer = node["offers"]
                        if "price" in offer:
                            price_val = str(offer["price"]).replace(",", "").strip()
                            curr_val = str(offer.get("priceCurrency", "USD")).strip().upper()

                    if price_val:
                        try:
                            num_p = float(price_val)
                            norm_key = f"prod:{_normalize_entity_name(prod_name)}"
                            observations.append(FactualObservation(
                                entity=prod_name,
                                entity_key=norm_key,
                                attribute="product_price",
                                value=f"{num_p:.2f}",
                                display_value=f"${num_p:.2f}" if curr_val == "USD" else f"{curr_val} {num_p:.2f}",
                                currency=curr_val,
                                context_type="standard",
                                source="json_ld",
                                url=url,
                                snippet=f'JSON-LD Product "{prod_name}" price: {price_val} {curr_val}',
                                region=url_region
                            ))
                        except ValueError:
                            pass

                # Organization telephone
                if "Organization" in node_type or "LocalBusiness" in node_type:
                    raw_tel = str(node.get("telephone", "")).strip()
                    clean_tel = _normalize_phone_number(raw_tel)
                    if clean_tel:
                        observations.append(FactualObservation(
                            entity=crawl_context.domain,
                            entity_key="phone:primary",
                            attribute="phone_number",
                            value=clean_tel,
                            display_value=raw_tel,
                            currency=None,
                            context_type="standard",
                            source="json_ld",
                            url=url,
                            snippet=f'JSON-LD telephone: {raw_tel}',
                            region=url_region
                        ))

        # 2. Visible Text Phone Observations
        if arch_val in ("homepage", "contact", "about", "other") or "/contact" in url or "/about" in url:
            for phone_m in phone_pattern.finditer(text):
                raw_ph = phone_m.group(0)
                clean_ph = _normalize_phone_number(raw_ph)
                if clean_ph:
                    s_start = max(0, phone_m.start() - 35)
                    s_end = min(len(text), phone_m.end() + 35)
                    surr_ph = text[s_start:s_end].lower()

                    # Department / Role context detection to avoid comparing Sales vs Support
                    role = "primary"
                    entity_label = crawl_context.domain
                    if any(k in surr_ph for k in ("sales:", "sales department", "sales inquiries", "sales team:", "direct sales", "new customer")):
                        role = "sales"
                        entity_label = f"{crawl_context.domain} (Sales)"
                    elif any(k in surr_ph for k in ("support:", "customer support", "technical support", "tech support", "help desk", "support desk", "customer service")):
                        role = "support"
                        entity_label = f"{crawl_context.domain} (Support)"
                    elif any(k in surr_ph for k in ("billing:", "billing department", "billing office", "accounts")):
                        role = "billing"
                        entity_label = f"{crawl_context.domain} (Billing)"
                    elif any(k in surr_ph for k in ("press:", "media:", "media inquiries", "press inquiries", "media relations")):
                        role = "media"
                        entity_label = f"{crawl_context.domain} (Media)"

                    observations.append(FactualObservation(
                        entity=entity_label,
                        entity_key=f"phone:{role}",
                        attribute="phone_number",
                        value=clean_ph,
                        display_value=raw_ph,
                        currency=None,
                        context_type="standard",
                        source="visible_text",
                        url=url,
                        snippet=text[s_start:s_end].strip(),
                        region=url_region
                    ))

        # 3. Visible Text Plan / Subscription Pricing
        lines = [line.strip() for line in text.split("\n") if line.strip()]
        for line in lines:
            plan_match = plan_pattern.search(line)
            price_match = price_pattern.search(line)
            if plan_match and price_match:
                plan_name = plan_match.group(0).strip()
                plan_key = f"plan:{_normalize_entity_name(plan_match.group(1))}"

                curr_raw = price_match.group(1) or price_match.group(4) or "$"
                amt_raw = price_match.group(2) or price_match.group(3)
                try:
                    num_val = float(amt_raw.replace(",", ""))
                except (ValueError, TypeError):
                    continue

                curr = "USD"
                if "€" in curr_raw or "EUR" in curr_raw.upper():
                    curr = "EUR"
                elif "£" in curr_raw or "GBP" in curr_raw.upper():
                    curr = "GBP"
                elif "₹" in curr_raw or "INR" in curr_raw.upper() or "rupees" in curr_raw.lower():
                    curr = "INR"

                line_lower = line.lower()

                context_type = "standard"
                if is_historical_page or any(k in line_lower for k in ("in 202", "in 201", "in 200", "previously", "historical", "legacy")):
                    context_type = "historical"
                elif any(k in line_lower for k in ("save $", "save ", "discount of", "savings of", "off ")):
                    context_type = "discount"
                elif bool(re.search(r"(?:/mo|/month|per month)\s+for\s+\d+\s+(?:months|mos|years|yrs)", line_lower)) or any(k in line_lower for k in ("installments", "financing", "monthly payments", "klarna", "afterpay", "affirm")):
                    context_type = "financing"
                elif any(k in line_lower for k in ("student", "students", "academic", "education", "nonprofit", "non-profit", "ngo", "government", "veteran")):
                    context_type = "customer_segment"
                elif any(k in line_lower for k in ("black friday", "cyber monday", "holiday special", "early bird", "limited time", "flash sale", "launch discount", "summer sale", "winter sale")):
                    context_type = "promotional"
                elif any(k in line_lower for k in ("introductory", "intro price", "first month", "trial period")):
                    context_type = "introductory"
                elif any(k in line_lower for k in ("msrp", "original price", "list price", "was $", "was €", "was £")):
                    context_type = "msrp"
                elif any(k in line_lower for k in ("sale", "strike")):
                    context_type = "sale"
                elif any(k in line_lower for k in ("starting at", "from ", "starts at")):
                    context_type = "starting_at"

                has_annual_billing = any(k in line_lower for k in ("billed annually", "annual billing", "paid annually", "yearly billing", "annual plan"))
                attribute = "monthly_price"
                if any(k in line_lower for k in ("/yr", "/year", "per year", "annual", "annually")) and not any(k in line_lower for k in ("/mo", "/month", "per month")):
                    attribute = "annual_price"
                elif has_annual_billing:
                    attribute = "annual_monthly_price"
                elif not any(k in line_lower for k in ("/mo", "/month", "per month", "a month", "monthly")):
                    attribute = "price"

                observations.append(FactualObservation(
                    entity=plan_name.title(),
                    entity_key=plan_key,
                    attribute=attribute,
                    value=f"{num_val:.2f}",
                    display_value=f"${num_val:.2f}" if curr == "USD" else f"{curr} {num_val:.2f}",
                    currency=curr,
                    context_type=context_type,
                    source="visible_text",
                    url=url,
                    snippet=line[:80].strip(),
                    region=url_region
                ))

        # 4. Visible Text Product Pricing
        title_clean = page.title.split("|")[0].split("-")[0].strip()
        is_product_page = (arch_val == "product_detail") or ("/product/" in url) or ("/item/" in url)
        if is_product_page and title_clean and len(title_clean) >= 3:
            prod_key = f"prod:{_normalize_entity_name(title_clean)}"

            for pmatch in price_pattern.finditer(text):
                curr_raw = pmatch.group(1) or pmatch.group(4) or "$"
                amt_raw = pmatch.group(2) or pmatch.group(3)
                try:
                    num_val = float(amt_raw.replace(",", ""))
                except (ValueError, TypeError):
                    continue

                curr = "USD"
                if "€" in curr_raw or "EUR" in curr_raw.upper():
                    curr = "EUR"
                elif "£" in curr_raw or "GBP" in curr_raw.upper():
                    curr = "GBP"
                elif "₹" in curr_raw or "INR" in curr_raw.upper() or "rupees" in curr_raw.lower():
                    curr = "INR"

                m_start = pmatch.start()
                m_end = pmatch.end()

                prefix = text[max(0, m_start - 35):m_start].lower()
                suffix = text[m_end:min(len(text), m_end + 35)].lower()

                # Clip prefix and suffix at nearest sentence or clause punctuation
                p_cuts = [prefix.rfind(d) for d in ('.', '(', ')', ';', '\n', '—', '–') if prefix.rfind(d) != -1]
                if p_cuts:
                    prefix = prefix[max(p_cuts) + 1:]

                s_cuts = [suffix.find(d) for d in ('.', '(', ')', ';', '\n', '—', '–', '|') if suffix.find(d) != -1]
                if s_cuts:
                    suffix = suffix[:min(s_cuts)]

                context_type = "standard"
                if is_historical_page or any(k in prefix for k in ("in 202", "in 201", "in 200", "previously", "historical", "legacy")):
                    context_type = "historical"
                elif any(k in prefix for k in ("save ", "save up to", "discount of", "savings of")) or any(k in suffix for k in (" off", " savings")):
                    context_type = "discount"
                elif bool(re.search(r"(?:/mo|/month|per month)\s+for\s+\d+\s+(?:months|mos|years|yrs)", prefix + " " + suffix)) or any(k in prefix or k in suffix for k in ("installments", "financing", "monthly payments", "klarna", "afterpay", "affirm")):
                    context_type = "financing"
                elif any(k in prefix for k in ("student", "academic", "education", "nonprofit", "non-profit")):
                    context_type = "customer_segment"
                elif any(k in prefix or k in suffix for k in ("black friday", "cyber monday", "holiday special", "early bird", "limited time", "flash sale")):
                    context_type = "promotional"
                elif any(k in prefix for k in ("introductory", "intro price", "first month", "trial period")) or any(k in suffix for k in ("introductory", "intro price")):
                    context_type = "introductory"
                elif any(k in prefix for k in ("original", "was", "list price")) or any(k in suffix for k in ("msrp", "original", "list price")):
                    context_type = "msrp"
                elif any(k in prefix for k in ("sale", "now", "special")) or any(k in suffix for k in ("sale",)):
                    context_type = "sale"
                elif any(k in prefix for k in ("starting", "starts at", "from ")):
                    context_type = "starting_at"

                snippet_start = max(0, m_start - 25)
                snippet_end = min(len(text), m_end + 25)

                observations.append(FactualObservation(
                    entity=title_clean,
                    entity_key=prod_key,
                    attribute="product_price",
                    value=f"{num_val:.2f}",
                    display_value=f"${num_val:.2f}" if curr == "USD" else f"{curr} {num_val:.2f}",
                    currency=curr,
                    context_type=context_type,
                    source="visible_text",
                    url=url,
                    snippet=text[snippet_start:snippet_end].strip(),
                    region=url_region
                ))

    # -------------------------------------------------------------------------
    # Reconcile Observations by (entity_key, attribute)
    # -------------------------------------------------------------------------
    groups: Dict[Tuple[str, str], List[FactualObservation]] = {}
    for obs in observations:
        key = (obs.entity_key, obs.attribute)
        if key not in groups:
            groups[key] = []
        groups[key].append(obs)

    for (entity_key, attribute), obs_list in groups.items():
        if len(obs_list) < 2:
            continue

        # Currencies must match (different currencies are legitimate regional pricing)
        currencies = {o.currency for o in obs_list if o.currency}
        if len(currencies) > 1:
            continue

        # Regional differences must not trigger false contradictions (e.g. /us/ vs /uk/)
        regions = {o.region for o in obs_list if o.region}
        if len(regions) > 1:
            continue

        # Filter out non-comparable observations:
        # Compare active selling offers: context_type in ("standard", "sale")
        # (Legitimate variations: historical, financing, starting_at, introductory, msrp, discount, customer_segment, promotional are excluded)
        comparable_obs = [o for o in obs_list if o.context_type in ("standard", "sale")]
        if len(comparable_obs) < 2:
            continue

        # Group comparable observations by URL
        url_map: Dict[str, List[FactualObservation]] = {}
        for o in comparable_obs:
            url_map.setdefault(o.url, []).append(o)

        contradiction_found = False
        evidence_lines: List[str] = []
        conflicting_obs: List[FactualObservation] = []

        # Check 1: Cross-Representation Contradiction on the SAME URL
        for url, u_obs in url_map.items():
            json_obs = [o for o in u_obs if o.source == "json_ld"]
            vis_obs = [o for o in u_obs if o.source == "visible_text"]
            if json_obs and vis_obs:
                json_vals = {o.value for o in json_obs}
                vis_vals = {o.value for o in vis_obs}
                # Contradiction exists only if structured data (JSON-LD) does NOT match ANY visible selling price on this page
                if not json_vals.intersection(vis_vals):
                    contradiction_found = True
                    for o in json_obs:
                        if o not in conflicting_obs:
                            conflicting_obs.append(o)
                            evidence_lines.append(f"- URL: {url} (Source: json_ld) -> Value: \"{o.display_value}\" [Snippet: {o.snippet}]")
                    for o in vis_obs:
                        if o not in conflicting_obs:
                            conflicting_obs.append(o)
                            evidence_lines.append(f"- URL: {url} (Source: visible_text) -> Value: \"{o.display_value}\" [Snippet: {o.snippet}]")

        # Check 2: Cross-Page Contradiction across DIFFERENT URLs
        if len(url_map) >= 2:
            url_val_sets = {u: {o.value for o in obs} for u, obs in url_map.items()}
            disjoint_urls = set()
            urls_list = list(url_map.keys())
            for i in range(len(urls_list)):
                for j in range(i + 1, len(urls_list)):
                    u1, u2 = urls_list[i], urls_list[j]
                    if not url_val_sets[u1].intersection(url_val_sets[u2]):
                        disjoint_urls.add(u1)
                        disjoint_urls.add(u2)

            if disjoint_urls:
                contradiction_found = True
                for u in sorted(disjoint_urls):
                    for o in url_map[u]:
                        if o not in conflicting_obs:
                            conflicting_obs.append(o)
                            evidence_lines.append(f"- URL: {u} (Source: {o.source}) -> Value: \"{o.display_value}\" [Snippet: {o.snippet}]")

        if not contradiction_found or not conflicting_obs:
            continue

        display_name = conflicting_obs[0].entity
        urls = sorted(list(set(o.url for o in conflicting_obs)))

        val_summary = " vs ".join(sorted(list(set(o.display_value for o in conflicting_obs))))
        url_values = {o.url: f"{o.display_value} (Source: {o.source})" for o in conflicting_obs}

        full_evidence = [
            f"Entity: {display_name}",
            f"Attribute: {attribute.replace('_', ' ').title()}",
            *evidence_lines,
            f"Conflict Reason: Material value disparity ({val_summary}) for identical entity across first-party pages/representations."
        ]

        contradictions.append({
            "entity_type": attribute,
            "entity_name": display_name,
            "attribute": attribute,
            "urls": urls,
            "values": url_values,
            "description": f"First-party factual contradiction detected for '{display_name}' ({attribute.replace('_', ' ')}). Conflicting values: {val_summary}.",
            "evidence_text": "\n".join(full_evidence),
            "severity": "high" if attribute in ("product_price", "monthly_price", "annual_price", "phone_number") else "medium",
            "root_cause": (
                f"Independent website subpages maintain disparate, unsynchronized copies of core business contact attributes for '{display_name}'."
                if attribute == "phone_number" else
                f"Independent website subpages or representations maintain disparate, unsynchronized copies of commercial {attribute.replace('_', ' ')} data for '{display_name}' without a single source of truth."
            ),
            "impact": "Automated extractors and search agents encounter contradictory factual signals when indexing the same entity, impairing factual consistency during retrieval and quotation.",
            "suggested_action_summary": f"Synchronize the conflicting first-party representations using a single source of truth for {display_name}.",
            "suggested_action_details": f"Unify the declared values across marketing, pricing, and structured data templates to reflect the authoritative {attribute.replace('_', ' ')}."
        })

    return contradictions


def analyze_temporal_freshness(crawl_context: CrawlContext) -> Dict[str, Any]:
    """
    Evaluates temporal freshness indicators (copyright years, modified timestamps).
    Distinguishes old copyright signals on active sites from genuinely stale offerings.
    """
    current_year = datetime.datetime.now(datetime.timezone.utc).year
    
    temporal_data = {
        "copyright_years": set(),
        "has_expired_promotions": False,
        "stale_offering_urls": [],
        "old_copyright_signal": False,
        "oldest_copyright_year": None
    }

    for page in crawl_context.pages:
        if page.status_code != 200:
            continue

        # Check copyright year
        c_year = page.extracted_dates.get("copyright_year")
        if c_year:
            try:
                y = int(c_year)
                if 2000 <= y <= current_year + 1:
                    temporal_data["copyright_years"].add(y)
            except ValueError:
                pass

        # Check for expired time-sensitive promotions/dates in visible copy
        # e.g. "Offer valid until December 2023", "Sale ends March 2024"
        expired_match = re.search(
            r"(?:offer valid through|sale ends|valid until|expires on|event date)[:\s]+(?:january|february|march|april|may|june|july|august|september|october|november|december)?\s*\d{0,2},?\s*(201\d|202[0-4])\b",
            page.raw_text,
            re.IGNORECASE
        )
        if expired_match:
            temporal_data["has_expired_promotions"] = True
            temporal_data["stale_offering_urls"].append({
                "url": page.url,
                "snippet": expired_match.group(0),
                "expired_year": expired_match.group(1)
            })

    if temporal_data["copyright_years"]:
        oldest = min(temporal_data["copyright_years"])
        temporal_data["oldest_copyright_year"] = oldest
        if current_year - oldest >= 2:
            temporal_data["old_copyright_signal"] = True

    return temporal_data


def evaluate_external_corroboration(
    first_party_claims: Dict[str, Any],
    external_records: Optional[List[Dict[str, Any]]] = None
) -> List[Dict[str, Any]]:
    """
    Evaluates external third-party corroboration records against first-party claims.
    Evaluates five explicit dimensions per PRD:
    1. Authority (official_registry, knowledge_graph, regulatory_filing vs unverified/forum)
    2. Relevance (verified same-entity match vs potential naming collision)
    3. Directness (direct explicit record vs passing indirect mention)
    4. Consistency (multi-source agreement vs external dispute)
    5. Recency (record timestamp relative to current context)

    Gracefully degrades to an empty list when external sources are unavailable or offline.
    Never assumes popularity or repetition equals truth.
    """
    if not external_records:
        return []

    AUTHORITATIVE_TYPES = {"official_registry", "regulatory_filing", "knowledge_graph"}
    
    # Group external records by attribute for multi-source consistency check
    grouped_by_attr: Dict[str, List[Dict[str, Any]]] = {}
    for rec in external_records:
        attr = rec.get("attribute")
        if attr:
            grouped_by_attr.setdefault(attr, []).append(rec)

    corroboration_findings: List[Dict[str, Any]] = []

    for attr, records in grouped_by_attr.items():
        first_party_val = first_party_claims.get(attr)
        if not first_party_val:
            continue

        # Filter for authoritative and relevant records
        authoritative_records = [
            r for r in records 
            if r.get("source_type") in AUTHORITATIVE_TYPES and r.get("is_entity_relevant", True)
        ]

        if not authoritative_records:
            # All available records are weak, irrelevant, or unverified -> Discard to avoid false positives
            continue

        # Check directness
        direct_authoritative = [r for r in authoritative_records if r.get("is_direct_statement", True)]
        if not direct_authoritative:
            # Authoritative source exists but only has indirect/passing mention -> Do not treat as a hard defect
            continue

        # Check Multi-Source External Consistency
        external_values = list({r.get("external_value", "").strip() for r in direct_authoritative if r.get("external_value")})

        if len(external_values) > 1:
            # Multiple authoritative external sources disagree among themselves!
            sources_summary = ", ".join(f"{r.get('source_name')} ('{r.get('external_value')}')" for r in direct_authoritative[:3])
            corroboration_findings.append({
                "source": "Multiple Authoritative Sources (Disputed)",
                "source_type": "disputed_external",
                "attribute": attr,
                "first_party_value": first_party_val,
                "external_value": " / ".join(external_values),
                "is_disputed": True,
                "description": f"External authoritative sources report conflicting records for {attr} ({sources_summary}), creating external grounding uncertainty relative to first-party value '{first_party_val}'."
            })
            continue

        # Single unambiguous authoritative external consensus
        ext_val = external_values[0] if external_values else ""
        if not ext_val:
            continue

        # Compare with first-party claim
        if ext_val.lower() != first_party_val.strip().lower():
            primary_rec = direct_authoritative[0]
            corroboration_findings.append({
                "source": primary_rec.get("source_name", "Authoritative Registry"),
                "source_type": primary_rec.get("source_type"),
                "attribute": attr,
                "first_party_value": first_party_val,
                "external_value": ext_val,
                "is_disputed": False,
                "description": f"Authoritative {primary_rec.get('source_type', 'registry').replace('_', ' ')} ({primary_rec.get('source_name')}) directly records {attr} as '{ext_val}', which conflicts with first-party website claim '{first_party_val}'."
            })

    return corroboration_findings
