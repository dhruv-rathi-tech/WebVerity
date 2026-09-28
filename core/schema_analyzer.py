"""
Schema.org JSON-LD analyzer and visible-to-structured fact reconciler.
Performs deterministic AST validation, archetype expectation mapping,
entity relationship inspection, and visible content contradiction checks.
"""

import re
import json
from typing import List, Dict, Any, Tuple, Optional, Set
from core.models import PageEvidence, PageArchetype, SiteArchetype, JsonLdBlock


def extract_entities_from_json_ld(json_ld_blocks: List[JsonLdBlock]) -> Dict[str, Any]:
    """
    Extracts high-value structured commercial and identity attributes from parsed JSON-LD.
    """
    extracted = {
        "types": set(),
        "names": [],
        "prices": [],
        "currencies": [],
        "availabilities": [],
        "brands": [],
        "same_as": [],
        "has_nested_offers": False,
        "has_author": False,
        "has_publisher": False,
        "syntax_errors": []
    }

    for block in json_ld_blocks:
        if block.has_syntax_error:
            extracted["syntax_errors"].append(block.error_message or "Invalid JSON syntax")
            continue

        if not block.parsed_data:
            continue

        _traverse_schema_node(block.parsed_data, extracted)

    return extracted


def _traverse_schema_node(node: Any, extracted: Dict[str, Any]) -> None:
    if isinstance(node, dict):
        # Type
        if "@type" in node:
            t = node["@type"]
            if isinstance(t, list):
                extracted["types"].update(str(x) for x in t)
            elif isinstance(t, str):
                extracted["types"].add(t)

        # Name / Headline
        if "name" in node and isinstance(node["name"], str):
            extracted["names"].append(node["name"].strip())
        if "headline" in node and isinstance(node["headline"], str):
            extracted["names"].append(node["headline"].strip())

        # Brand
        if "brand" in node:
            b = node["brand"]
            if isinstance(b, dict) and "name" in b:
                extracted["brands"].append(str(b["name"]).strip())
            elif isinstance(b, str):
                extracted["brands"].append(b.strip())

        # Offers
        if "offers" in node:
            extracted["has_nested_offers"] = True

        if "price" in node:
            p_val = str(node["price"]).strip().replace(",", "")
            if p_val and p_val not in extracted["prices"]:
                extracted["prices"].append(p_val)

        if "priceCurrency" in node and isinstance(node["priceCurrency"], str):
            curr = node["priceCurrency"].strip().upper()
            if curr and curr not in extracted["currencies"]:
                extracted["currencies"].append(curr)

        if "availability" in node and isinstance(node["availability"], str):
            avail = node["availability"].strip()
            if avail and avail not in extracted["availabilities"]:
                extracted["availabilities"].append(avail)

        # sameAs
        if "sameAs" in node:
            sa = node["sameAs"]
            if isinstance(sa, list):
                for x in sa:
                    if str(x).strip() and str(x).strip() not in extracted["same_as"]:
                        extracted["same_as"].append(str(x).strip())
            elif isinstance(sa, str) and sa.strip() and sa.strip() not in extracted["same_as"]:
                extracted["same_as"].append(sa.strip())

        # Author / Publisher
        if "author" in node:
            extracted["has_author"] = True
        if "publisher" in node:
            extracted["has_publisher"] = True

        # Recurse children
        for v in node.values():
            if isinstance(v, (dict, list)):
                _traverse_schema_node(v, extracted)

    elif isinstance(node, list):
        for item in node:
            _traverse_schema_node(item, extracted)


def reconcile_schema_against_visible_text(
    extracted_schema: Dict[str, Any],
    visible_text: str
) -> List[Dict[str, str]]:
    """
    Compares declared schema values with visible rendered page copy to detect direct factual conflicts.
    Accounts for legitimate price contexts: sale vs original (MSRP), ranges, variants, and starting-at prices.
    Returns list of discrepancies: [{"field": ..., "schema_val": ..., "visible_val": ..., "description": ...}]
    """
    discrepancies: List[Dict[str, str]] = []
    if not visible_text:
        return discrepancies

    visible_clean = visible_text.lower()

    # 1. Price Contradiction Check
    # If schema defines a price, check against visible prices and pricing contexts
    schema_prices = extracted_schema.get("prices", [])
    if schema_prices:
        # Extract all visible price matches with surrounding context
        price_patterns = list(re.finditer(
            r"(?:[\$\€\£\₹\¥]|USD|INR|EUR|GBP|CAD|AUD)\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)|\b(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)\s*(?:USD|INR|EUR|dollars|rupees)\b",
            visible_text,
            re.IGNORECASE
        ))
        
        visible_price_nums: List[float] = []
        for match in price_patterns:
            raw_num_str = (match.group(1) or match.group(2) or "").replace(",", "")
            try:
                val = float(raw_num_str)
                if val > 0 and val not in visible_price_nums:
                    visible_price_nums.append(val)
            except ValueError:
                pass

        # Check for price range pattern: e.g. "$50 - $100" or "$50 to $100"
        range_match = re.search(
            r"(?:[\$\€\£\₹\¥]|USD|INR|EUR)?\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)\s*(?:-|–|—|to)\s*(?:[\$\€\£\₹\¥]|USD|INR|EUR)?\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)",
            visible_text,
            re.IGNORECASE
        )
        price_range = None
        if range_match:
            try:
                min_p = float(range_match.group(1).replace(",", ""))
                max_p = float(range_match.group(2).replace(",", ""))
                if min_p <= max_p:
                    price_range = (min_p, max_p)
            except ValueError:
                pass

        # Check for legitimate pricing context cues
        has_sale_context = any(k in visible_clean for k in ("was ", "original price", "msrp", "regular price", "strike", "list price", "save ", "discount"))
        has_range_context = price_range is not None or any(k in visible_clean for k in ("starting at", "from ", "starting from", "starts at"))
        has_subscription_context = any(k in visible_clean for k in ("/mo", "/month", "per month", "/yr", "/year", "per year", "billed annually"))
        has_variants = len(visible_price_nums) > 1

        for schema_p in schema_prices:
            try:
                num_p = float(schema_p)
            except ValueError:
                continue

            # Check 1: Direct match with any visible price
            matches_direct = any(abs(num_p - vp) < 0.05 for vp in visible_price_nums)
            if matches_direct:
                continue

            # Check 2: Within price range
            if price_range and (price_range[0] - 0.05 <= num_p <= price_range[1] + 0.05):
                continue

            # Check 3: If multiple variant prices exist and schema matches at least one variant or starting price
            if has_variants:
                # If schema price matches starting-at price or any variant option
                if any(abs(num_p - vp) < 0.05 for vp in visible_price_nums):
                    continue
                # If sale context exists (e.g. original $120 vs sale $99), schema might represent either
                if has_sale_context and any(abs(num_p - vp) < 0.05 for vp in visible_price_nums):
                    continue

            # If there is visible price information and none matches under any valid context:
            if visible_price_nums:
                # Format friendly visible price list
                vis_str = ", ".join(f"${x:.2f}" if x.is_integer() else f"${x}" for x in visible_price_nums[:3])
                discrepancies.append({
                    "field": "price",
                    "schema_val": f"{schema_p} {extracted_schema.get('currencies', [''])[0]}".strip(),
                    "visible_val": vis_str,
                    "description": f"Structured data declares price '{schema_p}', which conflicts with the visible prices observed in page copy ({vis_str})."
                })

    # 2. Availability Contradiction Check
    for avail in extracted_schema.get("availabilities", []):
        avail_lower = avail.lower()
        if "outofstock" in avail_lower or "discontinued" in avail_lower:
            if "in stock" in visible_clean and "out of stock" not in visible_clean and "sold out" not in visible_clean:
                discrepancies.append({
                    "field": "availability",
                    "schema_val": avail.split("/")[-1],
                    "visible_val": "In Stock",
                    "description": f"Structured data specifies availability '{avail.split('/')[-1]}', while visible page copy states 'In Stock'."
                })
        elif "instock" in avail_lower:
            if ("out of stock" in visible_clean or "sold out" in visible_clean) and "in stock" not in visible_clean:
                discrepancies.append({
                    "field": "availability",
                    "schema_val": avail.split("/")[-1],
                    "visible_val": "Out of Stock / Sold Out",
                    "description": f"Structured data specifies availability 'InStock', while visible page copy states 'Out of Stock' or 'Sold Out'."
                })

    return discrepancies
