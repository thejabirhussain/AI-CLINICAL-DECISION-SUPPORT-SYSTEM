"""Text chunking with section awareness and overlap."""

import hashlib
import logging
import re
from datetime import datetime
from typing import Optional
import uuid

from app.core.constants import (
    DEFAULT_CHUNK_MAX,
    DEFAULT_CHUNK_MIN,
    DEFAULT_OVERLAP_RATIO,
)
from app.core.utils import compute_content_hash
from app.ingestion.models import Chunk, ContentType, CrawledPage

logger = logging.getLogger(__name__)


def detect_sections(text: str) -> list[dict[str, int]]:
    """Detect section boundaries (headings, numbered sections)."""
    sections = []
    lines = text.split("\n")

    for i, line in enumerate(lines):
        line_stripped = line.strip()

        # Check for heading patterns (numbered sections, all caps, etc.)
        if re.match(r"^[A-Z][A-Z\s]{10,}$", line_stripped):  # All caps heading
            sections.append({"type": "heading", "index": i, "text": line_stripped})
        elif re.match(r"^[A-Z][a-z]+.*:?\s*$", line_stripped) and len(line_stripped) < 100:
            # Potential heading (capitalized, short)
            sections.append({"type": "heading", "index": i, "text": line_stripped})
        elif re.match(r"^\d+[\.\)]\s+[A-Z]", line_stripped):  # Numbered section
            sections.append({"type": "numbered", "index": i, "text": line_stripped})

    return sections


def chunk_by_sections(
    text: str,
    sections: list[dict[str, int]],
    min_chunk: int = DEFAULT_CHUNK_MIN,
    max_chunk: int = DEFAULT_CHUNK_MAX,
) -> list[tuple[int, int, Optional[str]]]:
    """Chunk text by sections, respecting min/max chunk sizes."""
    chunks = []
    lines = text.split("\n")
    total_chars = len(text)

    if not sections:
        # No sections detected, use sliding window
        return []

    for i, section in enumerate(sections):
        start_idx = section["index"]
        end_idx = sections[i + 1]["index"] if i + 1 < len(sections) else len(lines)

        # Extract section text
        section_lines = lines[start_idx:end_idx]
        section_text = "\n".join(section_lines)
        section_chars = len(section_text)

        heading = section.get("text")

        if section_chars <= max_chunk:
            # Section fits in one chunk
            start_char = text.find(section_text)
            if start_char >= 0:
                end_char = start_char + section_chars
                chunks.append((start_char, end_char, heading))
        else:
            # Section too large, split with overlap
            char_start = text.find(section_text)
            if char_start >= 0:
                offset = 0
                while offset < section_chars:
                    chunk_end = min(offset + max_chunk, section_chars)
                    chunk_text = section_text[offset:chunk_end]

                    # Adjust to word boundary if not at end
                    if chunk_end < section_chars:
                        last_space = chunk_text.rfind("\n")
                        if last_space > max_chunk * 0.7:  # If reasonable
                            chunk_text = chunk_text[:last_space]
                            chunk_end = offset + len(chunk_text)

                    chunks.append((char_start + offset, char_start + chunk_end, heading))
                    offset += int(max_chunk * (1 - DEFAULT_OVERLAP_RATIO))  # Overlap

    return chunks


def chunk_by_sliding_window(
    text: str,
    min_chunk: int = DEFAULT_CHUNK_MIN,
    max_chunk: int = DEFAULT_CHUNK_MAX,
    overlap_ratio: float = DEFAULT_OVERLAP_RATIO,
) -> list[tuple[int, int, Optional[str]]]:
    """Chunk text using sliding window with overlap."""
    chunks = []
    text_length = len(text)
    
    if text_length == 0:
        return []

    if text_length <= max_chunk:
        return [(0, text_length, None)]

    offset = 0
    while offset < text_length:
        chunk_end = min(offset + max_chunk, text_length)
        chunk_text = text[offset:chunk_end]

        # Adjust to word boundary if not at end
        if chunk_end < text_length:
            # Try to break at sentence or paragraph
            for break_char in ["\n\n", "\n", ". ", " "]:
                last_break = chunk_text.rfind(break_char)
                if last_break > max_chunk * 0.7:  # Reasonable break point
                    chunk_text = chunk_text[: last_break + len(break_char)]
                    chunk_end = offset + len(chunk_text)
                    break

        # Ensure minimum chunk size
        if len(chunk_text) < min_chunk and offset > 0:
            # Merge with previous chunk
            if chunks:
                prev_start, prev_end, _ = chunks[-1]
                chunks[-1] = (prev_start, chunk_end, None)
            offset = chunk_end
            continue

        chunks.append((offset, chunk_end, None))
        offset += int(max_chunk * (1 - overlap_ratio))  # Overlap

    return chunks


def chunk_page(page: CrawledPage, chunk_order_start: int = 0) -> list[Chunk]:
    """Chunk a crawled page into smaller pieces."""
    text = page.cleaned_text

    if not text or len(text.strip()) < 100:
        logger.warning(f"Page {page.url} has insufficient text for chunking")
        return []

    # Try section-aware chunking first
    sections = detect_sections(text)
    if sections:
        chunk_ranges = chunk_by_sections(text, sections)
    else:
        chunk_ranges = chunk_by_sliding_window(text)

    if not chunk_ranges:
        return []

    chunks = []
    for i, (char_start, char_end, section_heading) in enumerate(chunk_ranges):
        chunk_text = text[char_start:char_end].strip()

        if len(chunk_text) < 50:  # Skip very small chunks
            continue

        # Generate chunk ID as a UUID (Qdrant requires integer or UUID IDs)
        chunk_id_data = f"{page.url}{char_start}{char_end}{chunk_text[:100]}"
        chunk_id = str(uuid.uuid5(uuid.NAMESPACE_URL, chunk_id_data))

        # Extract HTML snippet if available (for HTML content)
        raw_html_snippet = None
        if page.content_type == ContentType.HTML:
            # Best effort to extract corresponding HTML snippet
            # This is simplified - in production, you'd track HTML positions
            raw_html_snippet = chunk_text[:200]  # Placeholder

        chunk = Chunk(
            chunk_id=chunk_id,
            page_url=page.url,
            chunk_text=chunk_text,
            chunk_order=chunk_order_start + i,
            section_heading=section_heading,
            char_offset_start=char_start,
            char_offset_end=char_end,
            crawl_timestamp=page.crawl_timestamp,
            content_type=page.content_type,
            raw_html_snippet=raw_html_snippet,
            page_number=None,  # Would be set for PDFs
        )

        chunks.append(chunk)

    logger.info(f"Created {len(chunks)} chunks from {page.url}")
    return chunks


