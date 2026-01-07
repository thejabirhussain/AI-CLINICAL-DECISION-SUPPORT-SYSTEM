"""Sitemap parsing and URL discovery."""

import logging
from typing import Iterator, Optional
from urllib.parse import urljoin, urlparse
from xml.etree import ElementTree as ET

import httpx

from app.core.config import settings
from app.core.utils import normalize_url

logger = logging.getLogger(__name__)


def fetch_sitemap_urls(sitemap_url: str, max_urls: Optional[int] = None) -> Iterator[str]:
    """Fetch URLs from sitemap (supports sitemap index and regular sitemaps)."""
    try:
        response = httpx.get(sitemap_url, timeout=30.0, follow_redirects=True)
        response.raise_for_status()

        root = ET.fromstring(response.content)

        # Check if it's a sitemap index
        if root.tag == "{http://www.sitemaps.org/schemas/sitemap/0.9}sitemapindex":
            # It's a sitemap index, extract sitemap URLs
            for sitemap in root.findall("{http://www.sitemaps.org/schemas/sitemap/0.9}sitemap"):
                loc = sitemap.find("{http://www.sitemaps.org/schemas/sitemap/0.9}loc")
                if loc is not None and loc.text:
                    # Recursively fetch from child sitemap
                    yield from fetch_sitemap_urls(loc.text, max_urls)
        else:
            # Regular sitemap, extract URLs
            count = 0
            for url_elem in root.findall("{http://www.sitemaps.org/schemas/sitemap/0.9}url"):
                if max_urls and count >= max_urls:
                    break
                loc = url_elem.find("{http://www.sitemaps.org/schemas/sitemap/0.9}loc")
                if loc is not None and loc.text:
                    url = normalize_url(loc.text)
                    yield url
                    count += 1

    except Exception as e:
        logger.error(f"Error fetching sitemap {sitemap_url}: {e}")


def discover_sitemaps(base_url: str) -> list[str]:
    """Discover sitemap URLs from common locations."""
    sitemap_urls = [
        f"{base_url}/sitemap.xml",
        f"{base_url}/sitemap_index.xml",
        f"{base_url}/sitemap/sitemap.xml",
    ]

    found = []
    for url in sitemap_urls:
        try:
            response = httpx.head(url, timeout=10.0, follow_redirects=True)
            if response.status_code == 200:
                found.append(url)
                logger.info(f"Found sitemap: {url}")
        except Exception:
            pass

    return found


def discover_robots_txt(base_url: str) -> Optional[str]:
    """Discover robots.txt and extract sitemap URLs."""
    robots_url = f"{base_url}/robots.txt"
    try:
        response = httpx.get(robots_url, timeout=10.0, follow_redirects=True)
        if response.status_code == 200:
            sitemaps = []
            for line in response.text.splitlines():
                line = line.strip()
                if line.lower().startswith("sitemap:"):
                    sitemap_url = line.split(":", 1)[1].strip()
                    sitemaps.append(sitemap_url)
            return "\n".join(sitemaps) if sitemaps else None
    except Exception as e:
        logger.warning(f"Could not fetch robots.txt: {e}")

    return None


def get_seed_urls(base_url: str, max_urls: Optional[int] = None) -> list[str]:
    """Get seed URLs from sitemaps and robots.txt."""
    urls = set()

    # Check robots.txt first
    robots_content = discover_robots_txt(base_url)
    if robots_content:
        for line in robots_content.splitlines():
            if line.strip() and not line.startswith("#"):
                urls.add(normalize_url(line.strip()))

    # Discover sitemaps
    sitemaps = discover_sitemaps(base_url)
    for sitemap_url in sitemaps:
        for url in fetch_sitemap_urls(sitemap_url, max_urls):
            urls.add(url)
            if max_urls and len(urls) >= max_urls:
                break

    # Add base URL as fallback
    if not urls:
        urls.add(normalize_url(base_url))

    return sorted(list(urls))


