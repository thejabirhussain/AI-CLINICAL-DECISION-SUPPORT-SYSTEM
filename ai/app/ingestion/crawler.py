"""Respectful web crawler for IRS.gov."""

import logging
import time
from datetime import datetime
from typing import Optional
from urllib.robotparser import RobotFileParser

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.config import settings
from app.core.utils import normalize_url
from app.ingestion.models import ContentType, CrawledPage

logger = logging.getLogger(__name__)


class RespectfulCrawler:
    """Respectful crawler that follows robots.txt and rate limits."""

    def __init__(
        self,
        base_url: str,
        rate_limit_rps: float = 0.5,
        user_agent: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        ignore_robots: bool = False,
    ):
        self.base_url = base_url
        self.rate_limit_rps = rate_limit_rps
        self.user_agent = user_agent
        self.ignore_robots = ignore_robots
        self.last_request_time = 0.0
        self.robots_parser = None
        self.seen_urls = set()
        self.client = httpx.Client(
            timeout=30.0,
            follow_redirects=True,
            headers={"User-Agent": user_agent},
        )

    def _check_robots_txt(self) -> None:
        """Check and parse robots.txt."""
        if self.ignore_robots:
            return
        try:
            robots_url = f"{self.base_url}/robots.txt"
            self.robots_parser = RobotFileParser()
            self.robots_parser.set_url(robots_url)
            self.robots_parser.read()
            logger.info("Robots.txt parsed successfully")
        except Exception as e:
            logger.warning(f"Could not parse robots.txt: {e}")
            self.robots_parser = None

    def _can_fetch(self, url: str) -> bool:
        """Check if URL can be fetched according to robots.txt."""
        if self.ignore_robots:
            return True
        if self.robots_parser is None:
            return True
        try:
            return self.robots_parser.can_fetch(self.user_agent, url)
        except Exception:
            return True

    def _rate_limit(self) -> None:
        """Apply rate limiting."""
        elapsed = time.time() - self.last_request_time
        min_interval = 1.0 / self.rate_limit_rps
        if elapsed < min_interval:
            time.sleep(min_interval - elapsed)
        self.last_request_time = time.time()

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def fetch(self, url: str) -> Optional[CrawledPage]:
        """Fetch a single URL."""
        url = normalize_url(url, self.base_url)

        # Check if already seen
        if url in self.seen_urls:
            logger.debug(f"Skipping already seen URL: {url}")
            return None

        # Check robots.txt
        if not self.ignore_robots and not self._can_fetch(url):
            logger.info(f"Skipping URL (robots.txt): {url}")
            return None

        # Rate limit
        self._rate_limit()

        try:
            response = self.client.get(url)
            response.raise_for_status()

            # Determine content type
            content_type = ContentType.HTML
            content_type_header = response.headers.get("content-type", "").lower()
            if "application/pdf" in content_type_header or url.lower().endswith(".pdf"):
                content_type = ContentType.PDF

            # Parse last-modified
            last_modified = None
            if "last-modified" in response.headers:
                try:
                    last_modified = datetime.strptime(
                        response.headers["last-modified"], "%a, %d %b %Y %H:%M:%S %Z"
                    )
                except Exception:
                    pass

            # Extract ETag
            etag = response.headers.get("etag")

            # Extract title (basic, will be improved in parser)
            title = url.split("/")[-1] or "Untitled"

            self.seen_urls.add(url)

            return CrawledPage(
                url=url,
                title=title,
                crawl_timestamp=datetime.utcnow(),
                last_modified=last_modified,
                content_type=content_type,
                raw_content=response.content,
                cleaned_text="",  # Will be filled by parser
                content_hash="",  # Will be computed
                etag=etag,
                status_code=response.status_code,
            )

        except httpx.HTTPStatusError as e:
            logger.warning(f"HTTP error for {url}: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error fetching {url}: {e}")
            return None

    def close(self) -> None:
        """Close HTTP client."""
        self.client.close()


def create_crawler(base_url: str, rate_limit_rps: float = None, ignore_robots: bool = False) -> RespectfulCrawler:
    """Create a configured crawler."""
    if rate_limit_rps is None:
        rate_limit_rps = settings.rate_limit_rps

    crawler = RespectfulCrawler(
        base_url=base_url, 
        rate_limit_rps=rate_limit_rps,
        ignore_robots=ignore_robots
    )
    if not ignore_robots:
        crawler._check_robots_txt()
    return crawler


