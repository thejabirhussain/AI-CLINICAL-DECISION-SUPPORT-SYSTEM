"""Utility functions."""

import hashlib
import re
from datetime import datetime
from typing import Optional
from urllib.parse import urljoin, urlparse

import tldextract


def normalize_url(url: str, base_url: Optional[str] = None) -> str:
    """Normalize and canonicalize URL."""
    parsed = urlparse(url)
    if base_url:
        url = urljoin(base_url, url)
        parsed = urlparse(url)

    # Remove fragment
    normalized = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
    if parsed.query:
        normalized += f"?{parsed.query}"

    # Remove trailing slash (except for root)
    if normalized.endswith("/") and len(parsed.path) > 1:
        normalized = normalized[:-1]

    return normalized.lower()


def compute_content_hash(content: str | bytes) -> str:
    """Compute SHA256 hash of content."""
    if isinstance(content, str):
        content = content.encode("utf-8")
    return hashlib.sha256(content).hexdigest()


def estimate_tokens(text: str) -> int:
    """Estimate token count (rough approximation: ~4 chars per token)."""
    return len(text) // 4


def format_iso8601(dt: Optional[datetime]) -> Optional[str]:
    """Format datetime as ISO8601 string."""
    if dt is None:
        return None
    return dt.isoformat()


def parse_iso8601(s: Optional[str]) -> Optional[datetime]:
    """Parse ISO8601 string to datetime."""
    if s is None:
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except Exception:
        return None


def normalize_text(text: str) -> str:
    """Normalize whitespace in text."""
    # Replace multiple whitespace with single space
    text = re.sub(r"\s+", " ", text)
    # Remove leading/trailing whitespace
    return text.strip()


def truncate_text(text: str, max_length: int, suffix: str = "...") -> str:
    """Truncate text to max length with suffix."""
    if len(text) <= max_length:
        return text
    return text[: max_length - len(suffix)] + suffix


