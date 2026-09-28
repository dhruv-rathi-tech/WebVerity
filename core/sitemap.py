"""
Sitemap fetcher and XML parser.
"""

import xml.etree.ElementTree as ET
from typing import List, Tuple, Optional
from core.models import SitemapSummary
from core.url_utils import normalize_url, is_same_domain, is_crawlable_web_url


def parse_sitemap_xml(xml_content: str, base_domain_url: str) -> Tuple[List[str], List[str], Optional[str]]:
    """
    Parses sitemap XML content.
    Returns: (page_urls, sub_sitemap_urls, error_message)
    """
    if not xml_content or not xml_content.strip():
        return [], [], "Empty sitemap content"

    page_urls: List[str] = []
    sub_sitemap_urls: List[str] = []

    try:
        # Strip potential namespaces for easier processing
        root = ET.fromstring(xml_content)
        
        # Strip namespace tag prefix
        for elem in root.iter():
            if "}" in elem.tag:
                elem.tag = elem.tag.split("}", 1)[1]

        # Check if sitemap index
        if root.tag == "sitemapindex":
            for sitemap in root.findall("sitemap"):
                loc = sitemap.find("loc")
                if loc is not None and loc.text:
                    sub_url = loc.text.strip()
                    if sub_url:
                        sub_sitemap_urls.append(sub_url)
        elif root.tag == "urlset":
            for url_elem in root.findall("url"):
                loc = url_elem.find("loc")
                if loc is not None and loc.text:
                    u = loc.text.strip()
                    norm_u = normalize_url(u, base_domain_url)
                    if norm_u and is_same_domain(base_domain_url, norm_u, allow_subdomains=True) and is_crawlable_web_url(norm_u):
                        if norm_u not in page_urls:
                            page_urls.append(norm_u)
        else:
            # Fallback: search all loc elements
            for loc in root.iter("loc"):
                if loc.text:
                    u = loc.text.strip()
                    if u.endswith(".xml") or "sitemap" in u:
                        sub_sitemap_urls.append(u)
                    else:
                        norm_u = normalize_url(u, base_domain_url)
                        if norm_u and is_same_domain(base_domain_url, norm_u, allow_subdomains=True) and is_crawlable_web_url(norm_u):
                            if norm_u not in page_urls:
                                page_urls.append(norm_u)

        return page_urls, sub_sitemap_urls, None

    except ET.ParseError as pe:
        return [], [], f"XML Parse Error: {pe}"
    except Exception as e:
        return [], [], f"Sitemap processing error: {e}"
