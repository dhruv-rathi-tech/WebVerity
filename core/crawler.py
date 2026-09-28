"""
Bounded asynchronous HTTP crawler engine.
Respects robots.txt, executes intelligent URL prioritization, limits depth/pages, and builds CrawlContext.
"""

import asyncio
import time
import datetime
import urllib.parse
from typing import List, Dict, Set, Optional, Tuple
import httpx

from core.models import (
    BotRule,
    CrawlContext,
    PageEvidence,
    RobotsPolicy,
    SitemapSummary,
    SiteArchetype,
    PageArchetype
)
from core.url_utils import normalize_url, extract_domain, is_same_domain, is_crawlable_web_url
from core.robots import parse_robots_txt, is_path_allowed_for_bot
from core.sitemap import parse_sitemap_xml
from core.extractor import extract_page_evidence
from core.classifier import classify_page_archetype, classify_site_archetype


class AsyncCrawler:
    """
    Polite, bounded asynchronous HTTP crawler.
    """

    def __init__(
        self,
        max_pages: int = 20,
        max_depth: int = 2,
        concurrency: int = 5,
        request_timeout: float = 8.0,
        user_agent: str = "Mozilla/5.0 (compatible; WebVerityBot/1.0; +https://github.com/webverity/webverity)"
    ):
        self.max_pages = max_pages
        self.max_depth = max_depth
        self.concurrency = concurrency
        self.request_timeout = request_timeout
        self.user_agent = user_agent

    async def crawl(self, seed_url: str) -> CrawlContext:
        start_time = time.perf_counter()
        now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()

        norm_seed = normalize_url(seed_url)
        if not norm_seed:
            return CrawlContext(
                root_url=seed_url,
                domain="",
                audited_at=now_iso,
                site_archetype=SiteArchetype.UNKNOWN,
                robots_policy=RobotsPolicy(exists=False, url="", raw_content=""),
                sitemap_summary=SitemapSummary(exists=False),
                pages=[],
                crawl_duration_seconds=0.0,
                crawl_errors=["Invalid seed URL provided"]
            )

        domain = extract_domain(norm_seed)
        parsed_seed = urllib.parse.urlparse(norm_seed)
        base_domain_url = f"{parsed_seed.scheme}://{parsed_seed.netloc}"

        headers = {
            "User-Agent": self.user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        }

        crawl_errors: List[str] = []
        page_evidences: List[PageEvidence] = []
        discovered_urls: Set[str] = {norm_seed}
        visited_urls: Set[str] = set()

        async with httpx.AsyncClient(
            headers=headers,
            timeout=self.request_timeout,
            follow_redirects=True,
            verify=False
        ) as client:
            # 1. Fetch & Parse robots.txt
            robots_policy = await self._fetch_robots(client, base_domain_url)

            # 2. Discover & Parse Sitemaps
            sitemap_summary, sitemap_links = await self._discover_sitemaps(client, base_domain_url, robots_policy)
            for sl in sitemap_links:
                norm_sl = normalize_url(sl, base_domain_url)
                if norm_sl:
                    discovered_urls.add(norm_sl)

            # 3. Build Prioritized Crawl Queue: (base_priority, depth, url, cluster)
            # Lower effective score = higher priority
            queue: List[Tuple[int, int, str, str]] = []
            cluster_counts: Dict[str, int] = {}
            
            # Add seed URL as priority 0
            seed_cluster = self._infer_url_cluster(norm_seed)
            queue.append((0, 0, norm_seed, seed_cluster))

            # Add sitemap links with priority
            for sl in sitemap_links:
                norm_sl = normalize_url(sl, base_domain_url)
                if norm_sl and norm_sl != norm_seed:
                    p_score = self._compute_url_priority(norm_sl)
                    cluster = self._infer_url_cluster(norm_sl)
                    queue.append((p_score, 1, norm_sl, cluster))

            semaphore = asyncio.Semaphore(self.concurrency)

            # 4. Crawl Loop
            while queue and len(visited_urls) < self.max_pages:
                # Pop next batch up to concurrency limit
                batch = []
                while queue and len(batch) < self.concurrency and (len(visited_urls) + len(batch)) < self.max_pages:
                    # Dynamically sort remaining queue based on soft diversity penalty and depth
                    queue.sort(key=lambda item: (
                        self._effective_priority(item[0], item[3], cluster_counts),
                        item[1]  # depth
                    ))
                    base_p, depth, url, cluster = queue.pop(0)
                    if url not in visited_urls:
                        visited_urls.add(url)
                        cluster_counts[cluster] = cluster_counts.get(cluster, 0) + 1
                        batch.append((depth, url))

                if not batch:
                    break

                tasks = [
                    self._fetch_and_extract(client, url, depth, base_domain_url, robots_policy, semaphore)
                    for (depth, url) in batch
                ]
                results = await asyncio.gather(*tasks, return_exceptions=True)

                for res in results:
                    if isinstance(res, Exception):
                        crawl_errors.append(str(res))
                        continue
                    if res is None:
                        continue

                    page_ev, new_internal_links, current_depth = res
                    if page_ev.error_message:
                        crawl_errors.append(f"Failed to fetch {page_ev.url}: {page_ev.error_message}")
                    page_evidences.append(page_ev)

                    # Add new discoverable internal links if within depth limit
                    if current_depth < self.max_depth:
                        for link in new_internal_links:
                            norm_link = normalize_url(link.url, base_domain_url)
                            if norm_link and norm_link not in visited_urls and norm_link not in discovered_urls:
                                discovered_urls.add(norm_link)
                                p_score = self._compute_url_priority(norm_link)
                                cluster = self._infer_url_cluster(norm_link)
                                queue.append((p_score, current_depth + 1, norm_link, cluster))

        # 5. Classify Page Archetypes & Identify Primary Page
        for p in page_evidences:
            is_root = (p.normalized_url == norm_seed or p.normalized_url == base_domain_url or p.normalized_url == f"{base_domain_url}/")
            p.page_archetype = classify_page_archetype(p, is_root=is_root)
            p.is_primary_page = is_root or (p.page_archetype in (PageArchetype.HOMEPAGE, PageArchetype.PRODUCT_DETAIL, PageArchetype.PRICING))

        # 6. Classify Overall Site Archetype
        site_archetype = classify_site_archetype(page_evidences)

        duration = round(time.perf_counter() - start_time, 3)

        return CrawlContext(
            root_url=seed_url,
            domain=domain,
            audited_at=now_iso,
            site_archetype=site_archetype,
            robots_policy=robots_policy,
            sitemap_summary=sitemap_summary,
            pages=page_evidences,
            total_discovered_urls=len(discovered_urls),
            crawl_duration_seconds=duration,
            crawl_errors=crawl_errors
        )

    async def _fetch_robots(self, client: httpx.AsyncClient, base_domain_url: str) -> RobotsPolicy:
        robots_url = f"{base_domain_url}/robots.txt"
        try:
            resp = await client.get(robots_url)
            if resp.status_code == 200:
                return parse_robots_txt(robots_url, resp.text)
            elif resp.status_code in (401, 403):
                # RFC 9309: 401/403 access denied to robots.txt -> treat site as restricted
                return RobotsPolicy(
                    exists=True,
                    url=robots_url,
                    raw_content="User-agent: *\nDisallow: /",
                    bot_rules={"*": BotRule(user_agent="*", is_fully_blocked=True, disallowed_paths=["/"])},
                    sitemap_urls=[]
                )
        except Exception:
            pass
        return RobotsPolicy(exists=False, url=robots_url, raw_content="")

    async def _discover_sitemaps(
        self,
        client: httpx.AsyncClient,
        base_domain_url: str,
        robots_policy: RobotsPolicy
    ) -> Tuple[SitemapSummary, List[str]]:
        candidate_sitemaps: List[str] = list(robots_policy.sitemap_urls)
        default_sitemap = f"{base_domain_url}/sitemap.xml"
        if default_sitemap not in candidate_sitemaps:
            candidate_sitemaps.append(default_sitemap)

        extracted_urls: List[str] = []
        discovered_sitemaps: List[str] = []
        error_msg = None

        for sm_url in candidate_sitemaps:
            try:
                resp = await client.get(sm_url)
                if resp.status_code == 200 and ("xml" in resp.headers.get("content-type", "").lower() or resp.text.startswith("<?xml") or "<urlset" in resp.text):
                    discovered_sitemaps.append(sm_url)
                    page_urls, sub_sms, err = parse_sitemap_xml(resp.text, base_domain_url)
                    for pu in page_urls:
                        if pu not in extracted_urls:
                            extracted_urls.append(pu)
                    
                    # Fetch sub-sitemaps up to limit 3
                    for sub_sm in sub_sms[:3]:
                        try:
                            sub_resp = await client.get(sub_sm)
                            if sub_resp.status_code == 200:
                                sub_p_urls, _, _ = parse_sitemap_xml(sub_resp.text, base_domain_url)
                                for spu in sub_p_urls:
                                    if spu not in extracted_urls:
                                        extracted_urls.append(spu)
                        except Exception:
                            pass
            except Exception as e:
                error_msg = str(e)

        summary = SitemapSummary(
            exists=len(discovered_sitemaps) > 0,
            sitemap_urls_discovered=discovered_sitemaps,
            total_urls_in_sitemaps=len(extracted_urls),
            extracted_urls=extracted_urls[:100],
            error=error_msg if not discovered_sitemaps else None
        )
        return summary, extracted_urls

    async def _fetch_and_extract(
        self,
        client: httpx.AsyncClient,
        url: str,
        depth: int,
        base_domain_url: str,
        robots_policy: RobotsPolicy,
        semaphore: asyncio.Semaphore
    ) -> Optional[Tuple[PageEvidence, List, int]]:
        parsed_url = urllib.parse.urlparse(url)
        path = parsed_url.path or "/"

        # Respect robots.txt for generic and AI bot crawling
        if not is_path_allowed_for_bot(robots_policy, path, bot_name="*"):
            return None

        async with semaphore:
            req_start = time.perf_counter()
            try:
                resp = await client.get(url)
                resp_ms = round((time.perf_counter() - req_start) * 1000, 2)

                # HTTP 429 Rate Limiting Handling
                if resp.status_code == 429:
                    retry_after = resp.headers.get("Retry-After")
                    retry_sec = 0.0
                    if retry_after:
                        try:
                            retry_sec = float(retry_after)
                        except ValueError:
                            pass
                    # Perform at most one bounded retry if Retry-After is small (<= 2.0s)
                    if 0 < retry_sec <= 2.0:
                        await asyncio.sleep(retry_sec)
                        resp = await client.get(url)
                        resp_ms = round((time.perf_counter() - req_start) * 1000, 2)
                    else:
                        page_ev = extract_page_evidence(
                            url=url,
                            raw_html="",
                            status_code=429,
                            response_time_ms=resp_ms,
                            content_type="text/html",
                            base_domain_url=base_domain_url
                        )
                        page_ev.error_message = f"Rate limited (HTTP 429). Retry-After: {retry_after or 'unspecified'}"
                        return page_ev, [], depth

                content_type = resp.headers.get("content-type", "")

                if "text/html" not in content_type and "application/xhtml" not in content_type:
                    return None

                page_ev = extract_page_evidence(
                    url=str(resp.url),
                    raw_html=resp.text,
                    status_code=resp.status_code,
                    response_time_ms=resp_ms,
                    content_type=content_type,
                    base_domain_url=base_domain_url
                )
                return page_ev, page_ev.internal_links, depth

            except Exception as e:
                resp_ms = round((time.perf_counter() - req_start) * 1000, 2)
                page_ev = extract_page_evidence(
                    url=url,
                    raw_html="",
                    status_code=0,
                    response_time_ms=resp_ms,
                    content_type="unknown",
                    base_domain_url=base_domain_url
                )
                page_ev.error_message = str(e)
                return page_ev, [], depth

    def _compute_url_priority(self, url: str) -> int:
        """
        Calculates priority score for crawl queue ordering.
        Lower score = Higher priority.
        """
        path = urllib.parse.urlparse(url).path.lower()
        if path in ("", "/"):
            return 0
        if any(k in path for k in ("/pricing", "/plans", "/cost")):
            return 1
        if any(k in path for k in ("/product", "/item", "/shop", "/features", "/services")):
            return 2
        if any(k in path for k in ("/about", "/company", "/contact", "/faq", "/support")):
            return 3
        return 5

    def _infer_url_cluster(self, url: str) -> str:
        """
        Infers an archetype/template cluster key for a URL to ensure soft diversity.
        Uses semantic patterns where recognizable, falling back to structural path segments.
        """
        parsed = urllib.parse.urlparse(url)
        path = parsed.path.lower().strip()
        if not path or path == "/":
            return "homepage"

        # Check semantic page families
        if any(k in path for k in ("/pricing", "/plans", "/cost", "/tiers", "/subscription")):
            return "pricing"
        if any(k in path for k in ("/product/", "/products/", "/item/", "/items/", "/p/", "/dp/", "/goods/")) or (path.startswith("/product") or path.startswith("/item")):
            return "product"
        if any(k in path for k in ("/category/", "/categories/", "/catalog/", "/collection/", "/collections/", "/shop", "/store")):
            return "catalog"
        if any(k in path for k in ("/blog", "/news", "/article", "/posts", "/insights", "/press")):
            return "article"
        if any(k in path for k in ("/about", "/team", "/company", "/our-story", "/leadership", "/who-we-are")):
            return "about"
        if any(k in path for k in ("/contact", "/support", "/get-in-touch", "/reach-us", "/help-center")):
            return "contact"
        if any(k in path for k in ("/faq", "/questions")):
            return "faq"
        if any(k in path for k in ("/services", "/service/", "/solutions", "/features")):
            return "services"
        if any(k in path for k in ("/privacy", "/terms", "/legal", "/cookie", "/disclaimer", "/tos")):
            return "legal"
        if any(k in path for k in ("/docs", "/documentation", "/guide", "/api", "/developer")):
            return "docs"
        if any(k in path for k in ("/locations", "/stores", "/branches")):
            return "locations"

        # Structural fallback: first path segment
        segments = [s for s in path.split("/") if s]
        if segments:
            return f"path:/{segments[0]}"

        return "other"

    def _effective_priority(self, base_priority: int, cluster: str, cluster_counts: Dict[str, int]) -> float:
        """
        Calculates effective priority with soft diversity demotion.
        First 2 pages of a cluster incur 0 penalty.
        Subsequent pages from the same cluster incur a progressive soft penalty (+1.5 per page),
        allowing uncovered clusters to be scheduled ahead of redundant items without hard blocking.
        """
        seen = cluster_counts.get(cluster, 0)
        penalty = max(0, seen - 1) * 1.5
        return float(base_priority) + penalty


async def crawl_site(
    root_url: str,
    max_pages: int = 20,
    max_depth: int = 2,
    concurrency: int = 5,
    timeout_seconds: float = 8.0
) -> CrawlContext:
    """
    Convenience helper function to execute bounded crawl and return CrawlContext.
    """
    crawler = AsyncCrawler(
        max_pages=max_pages,
        max_depth=max_depth,
        concurrency=concurrency,
        request_timeout=timeout_seconds
    )
    return await crawler.crawl(root_url)
