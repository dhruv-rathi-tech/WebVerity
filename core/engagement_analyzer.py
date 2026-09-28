"""
On-Site Engagement & Information Architecture Analyzer.
Evaluates page orientation, heading hierarchy integrity, buried answers,
and context-sensitive next-step pathways across varied page archetypes.
"""

import re
from typing import List, Dict, Any, Optional
from core.models import PageEvidence, PageArchetype, SiteArchetype, HeadingItem, LinkItem


def analyze_page_engagement(page: PageEvidence, site_archetype: SiteArchetype) -> List[Dict[str, Any]]:
    """
    Evaluates orientation, information hierarchy, intent continuity, and next-step paths for a single page.
    Returns list of defect/opportunity items.
    """
    issues: List[Dict[str, Any]] = []

    if page.status_code != 200:
        return issues

    arch = page.page_archetype

    # -------------------------------------------------------------------------
    # 1. ORIENTATION & PRIMARY SUBJECT CLARITY
    # -------------------------------------------------------------------------
    # Check if page has completely missing title or empty generic heading on primary pages
    has_generic_title = not page.title or page.title.strip().lower() in ("untitled", "page", "home", "document", "new page")
    h1_headings = [h for h in page.heading_tree if h.level == 1]
    
    if has_generic_title and not h1_headings and page.is_primary_page:
        issues.append({
            "check": "orientation_clarity",
            "type": "defect",
            "severity": "high",
            "title": "Primary landing page lacks descriptive orientation title and primary heading",
            "observation": "The page possesses a generic/empty title and lacks a primary descriptive <h1> heading.",
            "evidence": f"URL: {page.url}\nTitle: '{page.title}'\n<h1> Count: 0",
            "root_cause": "The page template does not establish an unambiguous document subject in either <title> or <h1> markup.",
            "impact": "Visitors landing from external links or search snippets experience immediate orientation friction, making it harder to verify that the page matches their intended query.",
            "suggested_action": "Add a descriptive <title> tag and a clear <h1> heading that concisely states the subject and value proposition.",
            "priority": "high"
        })

    # -------------------------------------------------------------------------
    # 2. INFORMATION HIERARCHY & HEADING STRUCTURE
    # -------------------------------------------------------------------------
    # Only flag heading hierarchy if it creates a genuine structural comprehension barrier
    total_headings = len(page.heading_tree)
    if total_headings > 2:
        # Check for complete absence of H1 combined with only deep headings (H4/H5)
        if not h1_headings:
            top_level = min(h.level for h in page.heading_tree)
            if top_level >= 3:
                issues.append({
                    "check": "heading_hierarchy",
                    "type": "defect",
                    "severity": "medium",
                    "title": "Severe heading level gap creates disorganized document outline",
                    "observation": f"The page omits <h1> and <h2> headers entirely, starting section markup directly at <h{top_level}>.",
                    "evidence": f"URL: {page.url}\nHeading Sequence: {[h.tag for h in page.heading_tree[:5]]}",
                    "root_cause": "Visual styling considerations were applied using deep heading tags rather than maintaining semantic document structure.",
                    "impact": "Increases cognitive friction for users skimming the document outline and degrades semantic chunking during automated content parsing.",
                    "suggested_action": "Restructure page sections to begin with a single <h1> followed logically by <h2> and <h3> headers.",
                    "priority": "medium"
                })
        elif len(h1_headings) > 3:
            # Excessive competing H1s on a single page
            h1_texts = [f"'{h.text[:30]}'" for h in h1_headings[:4]]
            issues.append({
                "check": "heading_hierarchy",
                "type": "defect",
                "severity": "low",
                "title": "Multiple competing <h1> headings fragment page subject hierarchy",
                "observation": f"The page defines {len(h1_headings)} separate <h1> headings across different sections.",
                "evidence": f"URL: {page.url}\n<h1> Texts: [{', '.join(h1_texts)}]",
                "root_cause": "Multiple independent component blocks each declare an <h1> rather than using <h2> for sub-sections.",
                "impact": "Creates ambiguity regarding the primary subject of the document when readers or automated outline parsers extract key sections.",
                "suggested_action": "Reserve <h1> for the overarching page subject and transition sub-section headings to <h2>.",
                "priority": "low"
            })

    # -------------------------------------------------------------------------
    # 3. NEXT-STEP GUIDANCE (Context-Aware by Archetype)
    # -------------------------------------------------------------------------
    # Legitimate terminal pages (Legal, Privacy, Terms, Utility) do NOT require CTAs
    is_terminal_utility_page = arch == PageArchetype.LEGAL or any(k in page.url for k in ("/privacy", "/terms", "/legal", "/cookie", "/tos"))
    
    if not is_terminal_utility_page:
        effective_text = (page.rendered_text or page.raw_text).lower()
        is_non_english = bool(page.language and page.language != "en")

        # Multilingual commercial verbs (English + Spanish, French, German, Italian, Portuguese)
        BUY_VERBS = (
            # English
            "add to cart", "buy now", "order now", "purchase", "check out", "select option", "add to bag", "pre-order",
            # Spanish
            "añadir al carrito", "agregar al carrito", "comprar ahora", "comprar", "pedir", "finalizar compra",
            # French
            "ajouter au panier", "acheter", "commander", "passer la commande",
            # German
            "in den warenkorb", "jetzt kaufen", "kaufen", "bestellen", "in den einkaufswagen",
            # Italian
            "aggiungi al carrello", "acquista ora", "compra ora", "ordina",
            # Portuguese
            "adicionar ao carrinho", "comprar agora", "finalizar compra"
        )

        CTA_VERBS = (
            # English
            "contact", "get started", "sign up", "free trial", "request demo", "call", "book", "schedule", "quote",
            # Spanish
            "contacto", "contactar", "empezar", "registrarse", "prueba gratis", "solicitar demo", "pedir cita",
            # French
            "contacter", "commencer", "s'inscrire", "essai gratuit", "demander une démo", "prendre rendez-vous",
            # German
            "kontakt", "kontaktieren", "jetzt starten", "registrieren", "kostenlos testen", "demo anfordern", "termin vereinbaren",
            # Italian
            "contattaci", "contatto", "inizia", "registrati", "prova gratuita", "richiedi demo",
            # Portuguese
            "contato", "contactar", "começar", "cadastre-se", "teste grátis", "solicitar demo"
        )

        # Check commercial conversion / next-step paths on commercial pages
        if arch == PageArchetype.PRODUCT_DETAIL or (site_archetype == SiteArchetype.ECOMMERCE and "/product/" in page.url):
            has_buy_action = any(k in effective_text for k in BUY_VERBS)
            has_related_links = len(page.internal_links) >= 2

            if not has_buy_action and not has_related_links:
                # If page is confirmed non-English, do not penalize as strong dead-end if baseline navigation exists
                if is_non_english and len(page.internal_links) >= 1:
                    pass  # Suppress false dead-end on non-English page with active internal links
                else:
                    conf = "low" if is_non_english else "high"
                    sev = "low" if is_non_english else "high"
                    issues.append({
                        "check": "next_step_guidance",
                        "type": "defect",
                        "severity": sev,
                        "confidence": conf,
                        "title": "Product detail page lacks discoverable purchase pathway or related product navigation",
                        "observation": "The product page presents product details but provides no actionable purchasing button or links to related catalog offerings.",
                        "evidence": f"URL: {page.url}\nActionable commercial verbs found: None\nInternal links from content: {len(page.internal_links)}" + (f"\nPage Language: {page.language}" if page.language else ""),
                        "root_cause": "The page template terminates after product description without rendering interactive purchasing controls or catalog pathways.",
                        "impact": "Visitors arriving with high purchase intent encounter a dead-end experience with no intuitive next step to proceed with evaluation or transaction.",
                        "suggested_action": "Implement clear call-to-action buttons (e.g. 'Add to Cart' / 'Select Options') and contextual links to related products.",
                        "priority": sev
                    })

        elif arch in (PageArchetype.PRICING, PageArchetype.HOMEPAGE) and site_archetype in (SiteArchetype.B2B_SAAS, SiteArchetype.LOCAL_SERVICE):
            # Check for contact / signup / consultation path
            has_cta = any(k in effective_text for k in CTA_VERBS)
            has_actionable_links = len(page.internal_links) >= 1

            if not has_cta and not has_actionable_links:
                if is_non_english and len(page.internal_links) >= 1:
                    pass  # Suppress false dead-end on non-English page with navigation
                else:
                    conf = "low" if is_non_english else "high"
                    sev = "low" if is_non_english else "medium"
                    issues.append({
                        "check": "next_step_guidance",
                        "type": "defect",
                        "severity": sev,
                        "confidence": conf,
                        "title": "Service pricing / landing page lacks clear engagement call-to-action",
                        "observation": "Page outlines commercial service tiers but provides no discoverable link or form to contact sales, register, or initiate an inquiry.",
                        "evidence": f"URL: {page.url}\nPage Archetype: {arch.value}\nInternal Action Links: 0" + (f"\nPage Language: {page.language}" if page.language else ""),
                        "root_cause": "Pricing information is presented statically without interactive inquiry or onboarding links.",
                        "impact": "Creates friction for prospective customers seeking to act upon pricing or service information.",
                        "suggested_action": "Add prominent next-step action links (e.g. 'Contact Sales', 'Start Free Trial', or 'Book Consultation').",
                        "priority": sev
                    })

        elif arch == PageArchetype.ARTICLE:
            # Proactive recommendation for editorial content: related articles
            if len(page.internal_links) == 0:
                issues.append({
                    "check": "intent_continuity",
                    "type": "observation",
                    "severity": "low",
                    "title": "Editorial article lacks contextual links to related topics or next reading",
                    "observation": "The article concludes without offering contextual internal links to related articles or category archives.",
                    "evidence": f"URL: {page.url}\nInternal Links in body: 0",
                    "root_cause": "Article template does not incorporate related-content widgets or contextual in-body cross-links.",
                    "impact": "Limits exploration pathways for readers interested in exploring adjacent topics after finishing the article.",
                    "suggested_action": "Add a 'Related Articles' section or curated in-body links to relevant subject guides.",
                    "priority": "low"
                })

    return issues
