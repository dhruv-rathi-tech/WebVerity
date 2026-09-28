"""
Data models for the Crawl & Shared Evidence Foundation.
Conforms strictly to docs/architecture.md and produces immutable, serializable evidence.
"""

from __future__ import annotations
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import List, Dict, Any, Optional
import datetime


class SiteArchetype(str, Enum):
    ECOMMERCE = "ecommerce"
    B2B_SAAS = "b2b_saas"
    LOCAL_SERVICE = "local_service"
    PUBLISHER = "publisher"
    CORPORATE = "corporate"
    PORTFOLIO = "portfolio"
    UNKNOWN = "unknown"


class PageArchetype(str, Enum):
    HOMEPAGE = "homepage"
    PRODUCT_DETAIL = "product_detail"
    CATEGORY_CATALOG = "category_catalog"
    PRICING = "pricing"
    ABOUT = "about"
    CONTACT = "contact"
    ARTICLE = "article"
    LEGAL = "legal"
    FAQ = "faq"
    OTHER = "other"


@dataclass
class HeadingItem:
    tag: str  # "h1", "h2", "h3", "h4", "h5", "h6"
    level: int  # 1 to 6
    text: str
    dom_index: int


@dataclass
class LinkItem:
    url: str
    anchor_text: str
    is_internal: bool
    rel: Optional[str] = None


@dataclass
class ImageItem:
    src: str
    alt: str
    has_alt: bool
    is_content_relevant: bool
    context_keyword: Optional[str] = None


@dataclass
class JsonLdBlock:
    raw_json: str
    parsed_data: Optional[Dict[str, Any]] = None
    schema_types: List[str] = field(default_factory=list)
    has_syntax_error: bool = False
    error_message: Optional[str] = None


@dataclass
class PageEvidence:
    url: str
    normalized_url: str
    status_code: int
    response_time_ms: float
    content_type: str
    page_archetype: PageArchetype
    is_primary_page: bool
    title: str
    meta_description: str
    canonical_url: Optional[str]
    meta_tags: Dict[str, str]
    raw_html: str
    raw_text: str
    raw_text_length: int
    raw_word_count: int
    rendered_dom: Optional[str] = None
    rendered_text: Optional[str] = None
    required_rendering_trigger: bool = False
    missing_facts_in_raw: List[str] = field(default_factory=list)
    heading_tree: List[HeadingItem] = field(default_factory=list)
    json_ld: List[JsonLdBlock] = field(default_factory=list)
    images: List[ImageItem] = field(default_factory=list)
    internal_links: List[LinkItem] = field(default_factory=list)
    external_links: List[LinkItem] = field(default_factory=list)
    extracted_dates: Dict[str, str] = field(default_factory=dict)
    extracted_facts: Dict[str, Any] = field(default_factory=dict)
    language: Optional[str] = None
    canonical_chain: List[str] = field(default_factory=list)
    error_message: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["page_archetype"] = self.page_archetype.value
        return d


@dataclass
class BotRule:
    user_agent: str
    disallowed_paths: List[str] = field(default_factory=list)
    allowed_paths: List[str] = field(default_factory=list)
    is_fully_blocked: bool = False


@dataclass
class RobotsPolicy:
    exists: bool
    url: str
    raw_content: str
    bot_rules: Dict[str, BotRule] = field(default_factory=dict)
    sitemap_urls: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "exists": self.exists,
            "url": self.url,
            "raw_content": self.raw_content,
            "bot_rules": {
                k: asdict(v) for k, v in self.bot_rules.items()
            },
            "sitemap_urls": self.sitemap_urls,
        }


@dataclass
class SitemapSummary:
    exists: bool
    sitemap_urls_discovered: List[str] = field(default_factory=list)
    total_urls_in_sitemaps: int = 0
    extracted_urls: List[str] = field(default_factory=list)
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class CrawlContext:
    root_url: str
    domain: str
    audited_at: str
    site_archetype: SiteArchetype
    robots_policy: RobotsPolicy
    sitemap_summary: SitemapSummary
    pages: List[PageEvidence] = field(default_factory=list)
    total_discovered_urls: int = 0
    crawl_duration_seconds: float = 0.0
    crawl_errors: List[str] = field(default_factory=list)
    rendering_available: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "root_url": self.root_url,
            "domain": self.domain,
            "audited_at": self.audited_at,
            "site_archetype": self.site_archetype.value,
            "robots_policy": self.robots_policy.to_dict(),
            "sitemap_summary": self.sitemap_summary.to_dict(),
            "pages": [p.to_dict() for p in self.pages],
            "total_discovered_urls": self.total_discovered_urls,
            "crawl_duration_seconds": self.crawl_duration_seconds,
            "crawl_errors": self.crawl_errors,
            "rendering_available": self.rendering_available,
        }
