"""
Diff analyzer for Raw HTML vs Rendered DOM comparison.
Isolates genuine missing factual entities (pricing, availability, contact, specs, core copy)
while filtering out harmless dynamic JavaScript noise, tracking scripts, and UI widgets.
"""

import re
from typing import List, Tuple, Set, Dict, Any
from bs4 import BeautifulSoup, Comment


def analyze_raw_vs_rendered_dom(
    raw_html: str,
    rendered_dom: str,
    raw_text: str,
    rendered_text: str
) -> Tuple[List[str], float, bool]:
    """
    Compares raw HTML against rendered DOM.
    Returns: (missing_facts_in_raw, text_ratio, is_meaningful_content_loss)
    """
    if not rendered_dom or not rendered_text.strip():
        return [], 1.0, False

    raw_len = len(raw_text.strip())
    rendered_len = len(rendered_text.strip())
    ratio = round(raw_len / max(rendered_len, 1), 3)

    # 1. Extract Candidate Factual Entities from Rendered Text
    candidate_entities: List[str] = []

    # A. Prices & Currencies (e.g., $3,999, ₹8,999, 49.99 USD, €120)
    price_matches = re.findall(
        r"(?:[\$\€\£\₹\¥]|USD|INR|EUR|GBP|AUD|CAD)\s*\d{1,3}(?:[,\.]\d{3})*(?:\.\d{2})?|\b\d{1,3}(?:[,\.]\d{3})*(?:\.\d{2})?\s*(?:USD|INR|EUR|GBP|AUD|CAD|dollars|rupees|cents)\b",
        rendered_text,
        re.IGNORECASE
    )
    for p in price_matches:
        clean_p = p.strip()
        if clean_p and clean_p not in candidate_entities:
            candidate_entities.append(clean_p)

    # B. Stock & Availability Status
    avail_matches = re.findall(
        r"\b(in stock|out of stock|temporarily unavailable|backorder|pre-order|ships in \d+ days|available now)\b",
        rendered_text,
        re.IGNORECASE
    )
    for a in avail_matches:
        clean_a = a.strip().title()
        if clean_a and clean_a not in candidate_entities:
            candidate_entities.append(clean_a)

    # C. Phone numbers & Contact Emails
    phone_matches = re.findall(
        r"(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}",
        rendered_text
    )
    for ph in phone_matches:
        clean_ph = ph.strip()
        if len(clean_ph) >= 10 and clean_ph not in candidate_entities:
            candidate_entities.append(clean_ph)

    # D. Operating Hours
    hours_matches = re.findall(
        r"\b(?:mon|tue|wed|thu|fri|sat|sun)[a-z]*\s*[-–—to]+\s*(?:mon|tue|wed|thu|fri|sat|sun)[a-z]*\s*[:\s]+\d{1,2}(?::\d{2})?\s*(?:am|pm)?\s*[-–—to]+\s*\d{1,2}(?::\d{2})?\s*(?:am|pm)?",
        rendered_text,
        re.IGNORECASE
    )
    for h in hours_matches:
        clean_h = h.strip()
        if clean_h and clean_h not in candidate_entities:
            candidate_entities.append(clean_h)

    # E. Technical Specifications / SKUs (e.g., SKU-1234, 16GB RAM, 8K Full-Frame)
    sku_matches = re.findall(
        r"\b(?:SKU|Model|Part Number|MPN)[:\s]+[A-Za-z0-9\-_]{3,20}\b",
        rendered_text,
        re.IGNORECASE
    )
    for s in sku_matches:
        clean_s = s.strip()
        if clean_s and clean_s not in candidate_entities:
            candidate_entities.append(clean_s)

    # F. Substantive sentences in Rendered DOM absent in Raw HTML
    # Tokenize rendered sentences
    rendered_sentences = [
        s.strip() for s in re.split(r"[.!?\n]+", rendered_text) 
        if len(s.strip().split()) >= 8
    ]
    
    # Filter out boilerplate noise (cookies, login, copyright, navigation)
    boilerplate_filter = re.compile(
        r"cookie|consent|privacy policy|terms of service|all rights reserved|sign in|log in|subscribe|newsletter|javascript is disabled",
        re.IGNORECASE
    )

    # Check which candidate facts are genuinely missing in raw HTML
    missing_facts: List[str] = []
    raw_lower = raw_html.lower()

    for fact in candidate_entities:
        fact_clean = fact.lower()
        if fact_clean not in raw_lower:
            missing_facts.append(fact)

    # Check substantive paragraphs if raw text is severely depleted (ratio < 0.40)
    if ratio < 0.40:
        substantive_missing_count = 0
        sample_missing_snippet = None
        for sent in rendered_sentences:
            if boilerplate_filter.search(sent):
                continue
            # Check if majority of words in this sentence exist in raw HTML
            sent_words = [w.lower() for w in sent.split() if len(w) > 3]
            if not sent_words:
                continue
            matches_in_raw = sum(1 for w in sent_words if w in raw_lower)
            if (matches_in_raw / len(sent_words)) < 0.40:
                substantive_missing_count += 1
                if not sample_missing_snippet:
                    sample_missing_snippet = sent[:80]

        if substantive_missing_count >= 2 and sample_missing_snippet:
            missing_facts.append(f"Substantive content paragraph: '{sample_missing_snippet}...'")

    is_meaningful = len(missing_facts) > 0
    return missing_facts, ratio, is_meaningful
