"""
URL utilities for normalization, resolution, and domain boundaries.
"""

import urllib.parse
import posixpath
import re
from typing import Optional


def normalize_url(url: str, base_url: Optional[str] = None) -> str:
    """
    Normalizes a URL string:
    - Resolves relative URLs if base_url is provided.
    - Strips fragment identifiers (#).
    - Lowercases scheme and netloc.
    - Normalizes path slashes.
    - Removes common tracking query parameters (utm_*, ref, fbclid).
    """
    if not url:
        return ""

    # Clean whitespace
    url = url.strip()

    # Resolve relative URL
    if base_url:
        url = urllib.parse.urljoin(base_url, url)

    parsed = urllib.parse.urlparse(url)
    
    # Require http/https
    scheme = parsed.scheme.lower()
    if scheme not in ("http", "https"):
        return ""

    netloc = parsed.netloc.lower()
    # Strip default ports
    if netloc.endswith(":80") and scheme == "http":
        netloc = netloc[:-3]
    elif netloc.endswith(":443") and scheme == "https":
        netloc = netloc[:-4]

    # Normalize path
    path = parsed.path
    if not path:
        path = "/"
    else:
        # Collapse double slashes
        path = re.sub(r"/+", "/", path)

    # Filter tracking query parameters
    query_params = urllib.parse.parse_qsl(parsed.query, keep_blank_values=True)
    _TRACKING_KEYS = {
        "ref", "fbclid", "gclid", "msclkid", "_ga", "mc_cid", "mc_eid",
        "pk_campaign", "pk_kwd", "yclid", "trk", "igshid", "sessionid", "sid"
    }
    filtered_params = [
        (k, v) for (k, v) in query_params 
        if not k.lower().startswith("utm_") and k.lower() not in _TRACKING_KEYS
    ]
    
    # Sort query parameters for consistent deduplication
    filtered_params.sort(key=lambda x: x[0])
    new_query = urllib.parse.urlencode(filtered_params)

    normalized = urllib.parse.urlunparse((scheme, netloc, path, "", new_query, ""))
    return normalized


def extract_domain(url: str) -> str:
    """
    Extracts the lowercase hostname/domain from a URL.
    """
    parsed = urllib.parse.urlparse(url)
    return parsed.netloc.lower().split(":")[0]


def is_same_domain(url_a: str, url_b: str, allow_subdomains: bool = False) -> bool:
    """
    Checks if two URLs share the same domain boundary.
    """
    domain_a = extract_domain(url_a)
    domain_b = extract_domain(url_b)

    if not domain_a or not domain_b:
        return False

    # Normalize www. prefix
    norm_a = domain_a[4:] if domain_a.startswith("www.") else domain_a
    norm_b = domain_b[4:] if domain_b.startswith("www.") else domain_b

    if norm_a == norm_b:
        return True

    if allow_subdomains:
        return norm_a.endswith("." + norm_b) or norm_b.endswith("." + norm_a)

    return False


def is_crawlable_web_url(url: str) -> bool:
    """
    Returns True if the URL points to an HTML/web resource, excluding media/binary assets.
    """
    if not url:
        return False

    parsed = urllib.parse.urlparse(url)
    if parsed.scheme.lower() not in ("http", "https"):
        return False

    path = parsed.path.lower()
    excluded_extensions = (
        ".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".ico", ".avif",
        ".pdf", ".zip", ".tar", ".gz", ".rar", ".7z",
        ".mp3", ".mp4", ".mov", ".avi", ".webm",
        ".css", ".js", ".json", ".xml", ".txt", ".woff", ".woff2", ".ttf", ".eot"
    )
    for ext in excluded_extensions:
        if path.endswith(ext):
            return False

    return True
