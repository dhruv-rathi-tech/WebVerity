"""
HTML feature extractor for PageEvidence construction.
Extracts clean visible text, headings, JSON-LD, links, images, metadata, and dates deterministically.
"""

import re
import json
import urllib.parse
from typing import List, Dict, Any, Tuple, Optional
from bs4 import BeautifulSoup, Comment

from core.models import (
    PageEvidence,
    HeadingItem,
    LinkItem,
    ImageItem,
    JsonLdBlock,
    PageArchetype
)
from core.url_utils import normalize_url, is_same_domain, is_crawlable_web_url


def extract_page_evidence(
    url: str,
    raw_html: str,
    status_code: int,
    response_time_ms: float,
    content_type: str = "text/html",
    base_domain_url: Optional[str] = None
) -> PageEvidence:
    """
    Extracts all deterministic evidence from raw HTML.
    """
    norm_url = normalize_url(url, base_domain_url)
    base_url = base_domain_url or url

    if not raw_html or not raw_html.strip():
        return PageEvidence(
            url=url,
            normalized_url=norm_url,
            status_code=status_code,
            response_time_ms=response_time_ms,
            content_type=content_type,
            page_archetype=PageArchetype.OTHER,
            is_primary_page=False,
            title="",
            meta_description="",
            canonical_url=None,
            meta_tags={},
            raw_html="",
            raw_text="",
            raw_text_length=0,
            raw_word_count=0,
            required_rendering_trigger=True,
            error_message="Empty HTML body"
        )

    try:
        soup = BeautifulSoup(raw_html, "html.parser")
    except Exception as e:
        return PageEvidence(
            url=url,
            normalized_url=norm_url,
            status_code=status_code,
            response_time_ms=response_time_ms,
            content_type=content_type,
            page_archetype=PageArchetype.OTHER,
            is_primary_page=False,
            title="",
            meta_description="",
            canonical_url=None,
            meta_tags={},
            raw_html=raw_html,
            raw_text="",
            raw_text_length=0,
            raw_word_count=0,
            error_message=f"HTML Parse Error: {e}"
        )

    # 1. Title, Meta, and Language
    html_tag = soup.find("html")
    page_lang = None
    if html_tag and html_tag.get("lang"):
        page_lang = html_tag.get("lang").strip().lower()

    title_tag = soup.find("title")
    title_text = title_tag.get_text().strip() if title_tag else ""

    meta_tags: Dict[str, str] = {}
    meta_description = ""
    canonical_url: Optional[str] = None

    for tag in soup.find_all("meta"):
        name = tag.get("name") or tag.get("property") or tag.get("http-equiv")
        content = tag.get("content")
        if name and content:
            clean_name = name.strip().lower()
            clean_content = content.strip()
            meta_tags[clean_name] = clean_content
            if clean_name in ("description", "og:description", "twitter:description") and not meta_description:
                meta_description = clean_content
            if clean_name in ("content-language", "language") and not page_lang:
                page_lang = clean_content.lower()

    if page_lang:
        page_lang = re.split(r"[-_]", page_lang)[0].strip()

    # Canonical
    canonical_tag = soup.find("link", rel=lambda r: r and "canonical" in r.lower())
    if canonical_tag and canonical_tag.get("href"):
        canonical_url = normalize_url(canonical_tag.get("href"), base_url)

    # 2. JSON-LD Blocks
    json_ld_blocks: List[JsonLdBlock] = []
    for script_tag in soup.find_all("script", type=lambda t: t and "ld+json" in t.lower()):
        raw_script = script_tag.string or script_tag.get_text() or ""
        raw_script_clean = raw_script.strip()
        if not raw_script_clean:
            continue

        try:
            parsed_json = json.loads(raw_script_clean)
            schema_types = _extract_schema_types(parsed_json)
            json_ld_blocks.append(JsonLdBlock(
                raw_json=raw_script_clean,
                parsed_data=parsed_json,
                schema_types=schema_types,
                has_syntax_error=False,
                error_message=None
            ))
        except json.JSONDecodeError as jde:
            json_ld_blocks.append(JsonLdBlock(
                raw_json=raw_script_clean,
                parsed_data=None,
                schema_types=[],
                has_syntax_error=True,
                error_message=str(jde)
            ))

    # 3. Headings Tree
    heading_tree: List[HeadingItem] = []
    dom_index = 0
    for h in soup.find_all(["h1", "h2", "h3", "h4", "h5", "h6"]):
        h_text = h.get_text(strip=True)
        if h_text:
            tag_name = h.name.lower()
            level = int(tag_name[1])
            heading_tree.append(HeadingItem(
                tag=tag_name,
                level=level,
                text=h_text,
                dom_index=dom_index
            ))
            dom_index += 1

    # 4. Links
    internal_links: List[LinkItem] = []
    external_links: List[LinkItem] = []
    seen_links = set()

    for a in soup.find_all("a", href=True):
        raw_href = a.get("href", "").strip()
        if not raw_href or raw_href.startswith(("#", "javascript:", "mailto:", "tel:")):
            continue

        resolved_href = normalize_url(raw_href, base_url)
        if not resolved_href or resolved_href in seen_links:
            continue

        seen_links.add(resolved_href)
        anchor_txt = a.get_text(strip=True)
        rel_attr = a.get("rel")
        rel_str = " ".join(rel_attr) if isinstance(rel_attr, list) else (rel_attr or "")

        is_int = is_same_domain(base_url, resolved_href, allow_subdomains=True)
        link_obj = LinkItem(
            url=resolved_href,
            anchor_text=anchor_txt,
            is_internal=is_int,
            rel=rel_str if rel_str else None
        )

        if is_int:
            internal_links.append(link_obj)
        else:
            external_links.append(link_obj)

    # 5. Images
    images: List[ImageItem] = []
    # Explicit data visualization and technical factual keywords
    factual_keywords = [
        "chart", "graph", "diagram", "infographic", "flowchart", "specsheet",
        "specs", "specification", "dimensions", "pricingtable", "pricelist",
        "nutrition", "comparison", "schedule", "blueprint"
    ]
    # UI, branding, and decorative indicators to exclude
    decorative_indicators = [
        "logo", "icon", "avatar", "favicon", "badge", "button", "arrow",
        "spinner", "tracker", "pixel", "1x1", "emoji", "nav-", "header-", "footer-"
    ]

    for img in soup.find_all("img"):
        src = img.get("src") or img.get("data-src") or ""
        alt = img.get("alt")
        has_alt = alt is not None
        alt_text = alt.strip() if has_alt else ""

        # Accessibility guardrail: explicitly decorative images should never be flagged as factual traps
        role = (img.get("role") or "").lower()
        aria_hidden = (img.get("aria-hidden") or "").lower()
        if role in ("presentation", "none") or aria_hidden == "true":
            images.append(ImageItem(
                src=src,
                alt=alt_text,
                has_alt=has_alt and len(alt_text) > 0,
                is_content_relevant=False,
                context_keyword=None
            ))
            continue

        src_lower = src.lower()
        
        # Guardrail: Check if image is an icon, brand logo, or tracking pixel
        is_decorative = any(dec in src_lower for dec in decorative_indicators)
        if not is_decorative and "/logos/" in src_lower:
            is_decorative = True

        # Check if inside a navigation header, footer, or menu
        if not is_decorative:
            parent_nav = img.find_parent(["nav", "header", "footer"])
            if parent_nav:
                # Images in nav/header without explicit data keyword in src are decorative logos/icons
                if not any(kw in src_lower for kw in ("chart", "diagram", "infographic", "table")):
                    is_decorative = True

        matched_kw = None

        if not is_decorative:
            # Extract clean image path/filename without host or query
            img_path = urllib.parse.urlparse(src).path.lower()
            
            # 1. Filename / path keyword cue (delimited token check, not substring of photograph/geograph/species)
            for kw in ("chart", "diagram", "infographic", "flowchart", "specs", "specification", "dimensions", "blueprint", "pricing-table", "spec-sheet", "comparison-matrix"):
                # Matches delimited keyword like /foo-chart.png, /camera_specs.jpg, /flowchart-v2.png
                pattern = rf"(?:^|[_\-\./]){re.escape(kw)}(?:$|[_\-\./0-9])"
                if re.search(pattern, img_path):
                    matched_kw = kw
                    break

            # 2. Semantic container cue (<figure> with <figcaption>)
            if not matched_kw:
                parent_figure = img.find_parent("figure")
                if parent_figure:
                    caption = parent_figure.find("figcaption")
                    if caption:
                        cap_text = caption.get_text(strip=True).lower()
                        for kw in ("pricing", "plan", "chart", "graph", "diagram", "infographic", "flowchart", "spec", "specs", "specification", "dimensions", "comparison"):
                            if re.search(rf"\b{re.escape(kw)}\b", cap_text):
                                matched_kw = f"caption:{kw}"
                                break

            # 3. Preceding section heading cue (e.g. directly under H2/H3 for "Technical Specifications", "Architecture Diagram")
            if not matched_kw:
                prev_heading = img.find_previous(["h1", "h2", "h3", "h4"])
                if prev_heading:
                    h_text = prev_heading.get_text(strip=True).lower()
                    for kw in ("spec", "specs", "specification", "pricing", "price", "architecture", "diagram", "dimension", "chart", "comparison", "flowchart"):
                        if kw in h_text:
                            matched_kw = f"heading:{kw}"
                            break

        images.append(ImageItem(
            src=src,
            alt=alt_text,
            has_alt=has_alt and len(alt_text) > 0,
            is_content_relevant=bool(matched_kw),
            context_keyword=matched_kw
        ))


    # 6. Dates & Copyright Extraction
    extracted_dates: Dict[str, str] = {}
    for k in ("article:published_time", "article:modified_time", "date", "datemodified", "datepublished"):
        if k in meta_tags:
            extracted_dates[k] = meta_tags[k]

    # Footer Copyright Regex
    copyright_match = re.search(r"(?:©|&copy;|copyright)\s*(?:(?:19|20)\d{2}\s*[-–—]\s*)?((?:19|20)\d{2})", raw_html, re.IGNORECASE)
    if copyright_match:
        extracted_dates["copyright_year"] = copyright_match.group(1)

    # 7. Clean Visible Text
    # Create clone of soup for text cleanup
    text_soup = BeautifulSoup(raw_html, "html.parser")
    for elem in text_soup(["script", "style", "noscript", "svg", "header", "footer"]):
        elem.decompose()
    for comment in text_soup.find_all(string=lambda text: isinstance(text, Comment)):
        comment.extract()

    raw_text = text_soup.get_text(separator=" ", strip=True)
    raw_text = re.sub(r"\s+", " ", raw_text)
    raw_text_len = len(raw_text)
    raw_words = len(raw_text.split())

    # 8. Selective Rendering Trigger Assessment
    framework_containers = ["root", "app", "app-root", "next", "__next", "nuxt", "__nuxt"]
    has_framework_shell = False
    for fc in framework_containers:
        if soup.find(id=fc) or soup.find(fc):
            has_framework_shell = True
            break

    # Trigger selective rendering if text is very sparse or contains empty JS framework shell
    required_render_trigger = (raw_text_len < 300) or (has_framework_shell and raw_text_len < 500)

    return PageEvidence(
        url=url,
        normalized_url=norm_url,
        status_code=status_code,
        response_time_ms=response_time_ms,
        content_type=content_type,
        page_archetype=PageArchetype.OTHER,  # Will be classified by classifier
        is_primary_page=False,
        title=title_text,
        meta_description=meta_description,
        canonical_url=canonical_url,
        meta_tags=meta_tags,
        raw_html=raw_html,
        raw_text=raw_text,
        raw_text_length=raw_text_len,
        raw_word_count=raw_words,
        rendered_dom=None,
        rendered_text=None,
        required_rendering_trigger=required_render_trigger,
        missing_facts_in_raw=[],
        heading_tree=heading_tree,
        json_ld=json_ld_blocks,
        images=images,
        internal_links=internal_links,
        external_links=external_links,
        extracted_dates=extracted_dates,
        extracted_facts={},
        language=page_lang,
        error_message=None
    )


def _extract_schema_types(data: Any) -> List[str]:
    """
    Recursively extracts all @type values from parsed JSON-LD.
    """
    types: List[str] = []
    if isinstance(data, dict):
        if "@type" in data:
            t = data["@type"]
            if isinstance(t, list):
                types.extend(str(item) for item in t)
            elif isinstance(t, str):
                types.append(t)
        for v in data.values():
            types.extend(_extract_schema_types(v))
    elif isinstance(data, list):
        for item in data:
            types.extend(_extract_schema_types(item))
    return list(set(types))
