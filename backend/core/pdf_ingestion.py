"""
core/pdf_ingestion.py — PDF parsing and article chunking for ConstitutionAI.

Parses the Indian Constitution PDF using PyMuPDF (fitz).
Chunks by article using regex detection — never splits mid-article.
Also detects: Preamble, Parts, Schedules, and Amendments.
"""

from __future__ import annotations

import re
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Regex patterns for constitutional structure detection
# ---------------------------------------------------------------------------

ARTICLE_PATTERN = re.compile(r"Article\s+(\d+[A-Z]?)\b", re.IGNORECASE)
PART_PATTERN = re.compile(r"PART\s+(I{1,3}V?|V?I{0,3}|IX|X{0,3}[A-Z]?)\b", re.IGNORECASE)
SCHEDULE_PATTERN = re.compile(r"(FIRST|SECOND|THIRD|FOURTH|FIFTH|SIXTH|SEVENTH|EIGHTH|NINTH|TENTH|ELEVENTH|TWELFTH)\s+SCHEDULE", re.IGNORECASE)
AMENDMENT_PATTERN = re.compile(r"(\d+)(st|nd|rd|th)\s+Amendment\b", re.IGNORECASE)
PREAMBLE_PATTERN = re.compile(r"PREAMBLE|WE,\s+THE\s+PEOPLE\s+OF\s+INDIA", re.IGNORECASE)

PART_NAMES = {
    "I": "The Union and its Territory",
    "II": "Citizenship",
    "III": "Fundamental Rights",
    "IV": "Directive Principles of State Policy",
    "IVA": "Fundamental Duties",
    "V": "The Union",
    "VI": "The States",
    "VII": "The States in Part B of the First Schedule",
    "VIII": "The Union Territories",
    "IX": "The Panchayats",
    "IXA": "The Municipalities",
    "IXB": "The Co-operative Societies",
    "X": "The Scheduled and Tribal Areas",
    "XI": "Relations between the Union and the States",
    "XII": "Finance, Property, Contracts and Suits",
    "XIII": "Trade, Commerce and Intercourse within the Territory of India",
    "XIV": "Services under the Union and the States",
    "XIVA": "Tribunals",
    "XV": "Elections",
    "XVI": "Special Provisions relating to certain Classes",
    "XVII": "Official Language",
    "XVIII": "Emergency Provisions",
    "XIX": "Miscellaneous",
    "XX": "Amendment of the Constitution",
    "XXI": "Temporary, Transitional and Special Provisions",
    "XXII": "Short title, commencement, authoritative text in Hindi and repeals",
}

SCHEDULE_ORDINALS = {
    "FIRST": 1, "SECOND": 2, "THIRD": 3, "FOURTH": 4,
    "FIFTH": 5, "SIXTH": 6, "SEVENTH": 7, "EIGHTH": 8,
    "NINTH": 9, "TENTH": 10, "ELEVENTH": 11, "TWELFTH": 12,
}


class ArticleChunk:
    """Represents a single constitutional chunk (article, preamble, schedule, etc.)."""

    def __init__(
        self,
        article_id: str,
        article_number: int,
        title: str,
        part: str,
        raw_text: str,
        page_number: int,
        chunk_type: str = "article",  # "article" | "preamble" | "schedule" | "amendment"
    ):
        self.article_id = article_id
        self.article_number = article_number
        self.title = title
        self.part = part
        self.raw_text = raw_text.strip()
        self.page_number = page_number
        self.chunk_type = chunk_type

    def to_dict(self) -> dict:
        return {
            "article_id": self.article_id,
            "article_number": self.article_number,
            "title": self.title,
            "part": self.part,
            "raw_text": self.raw_text,
            "page_number": self.page_number,
            "chunk_type": self.chunk_type,
        }


class PDFIngestion:
    """
    Parses the Indian Constitution PDF and returns article-level chunks.

    Usage:
        ingestion = PDFIngestion()
        articles = ingestion.ingest("./data/constitution.pdf")
        article = ingestion.get_article("article_21")
    """

    def __init__(self):
        self._chunks: dict[str, ArticleChunk] = {}

    def ingest(self, pdf_path: str) -> list[dict]:
        """
        Parse the constitution PDF and chunk by article.
        Returns a list of article dicts.
        """
        import fitz  # PyMuPDF

        path = Path(pdf_path)
        if not path.exists():
            raise FileNotFoundError(f"Constitution PDF not found at: {pdf_path}")

        logger.info("Opening PDF: %s", pdf_path)
        doc = fitz.open(str(path))

        # Step 1: Extract all text with page numbers
        pages: list[tuple[int, str]] = []
        for page_num, page in enumerate(doc, start=1):
            text = page.get_text("text")
            pages.append((page_num, text))

        doc.close()
        logger.info("Extracted %d pages from PDF", len(pages))

        # Step 2: Combine all text into one stream with page markers
        full_text_parts: list[str] = []
        page_offsets: list[tuple[int, int]] = []  # (char_offset, page_num)
        offset = 0
        for page_num, text in pages:
            page_offsets.append((offset, page_num))
            full_text_parts.append(text)
            offset += len(text)

        full_text = "\n".join(full_text_parts)

        # Step 3: Parse into chunks
        chunks = self._parse_chunks(full_text, page_offsets)
        logger.info("Parsed %d constitutional chunks", len(chunks))

        # Step 4: Store and return
        self._chunks = {c.article_id: c for c in chunks}
        return [c.to_dict() for c in chunks]

    def _parse_chunks(self, text: str, page_offsets: list[tuple[int, int]]) -> list[ArticleChunk]:
        """Parse the full text into structured chunks."""
        chunks: list[ArticleChunk] = []
        current_part = "I"

        # Find preamble first
        preamble_match = PREAMBLE_PATTERN.search(text)
        if preamble_match:
            preamble_start = preamble_match.start()
            # Find the first article after preamble
            first_article = ARTICLE_PATTERN.search(text)
            preamble_end = first_article.start() if first_article else preamble_start + 2000
            preamble_text = text[preamble_start:preamble_end].strip()
            if len(preamble_text) > 50:
                chunks.append(ArticleChunk(
                    article_id="preamble",
                    article_number=0,
                    title="Preamble to the Constitution of India",
                    part="Preamble",
                    raw_text=preamble_text[:5000],  # cap preamble
                    page_number=self._get_page_for_offset(preamble_start, page_offsets),
                    chunk_type="preamble",
                ))

        # Find all article positions
        article_matches = list(ARTICLE_PATTERN.finditer(text))
        schedule_matches = list(SCHEDULE_PATTERN.finditer(text))
        part_matches = list(PART_PATTERN.finditer(text))

        logger.info(
            "Found %d article references, %d schedules, %d part headers",
            len(article_matches), len(schedule_matches), len(part_matches)
        )

        # Deduplicate articles (keep first occurrence per article number)
        seen_articles: dict[str, int] = {}  # article_id -> index in article_matches
        unique_article_matches = []
        for match in article_matches:
            art_num = match.group(1).upper()
            art_id = f"article_{art_num.lower()}"
            if art_id not in seen_articles:
                seen_articles[art_id] = len(unique_article_matches)
                unique_article_matches.append(match)

        # Build article chunks from unique article positions
        for i, match in enumerate(unique_article_matches):
            art_num_str = match.group(1).upper()
            art_id = f"article_{art_num_str.lower()}"

            # Determine end of this article's text
            if i + 1 < len(unique_article_matches):
                end_pos = unique_article_matches[i + 1].start()
            else:
                end_pos = len(text)

            # Check for schedule boundaries
            for sched_match in schedule_matches:
                if match.start() < sched_match.start() < end_pos:
                    end_pos = sched_match.start()
                    break

            art_text = text[match.start():end_pos].strip()

            # Update current part tracker
            for part_match in part_matches:
                if part_match.start() <= match.start():
                    current_part = part_match.group(1).upper()

            # Extract title from first line after article number
            title = self._extract_title(art_text, art_num_str)

            # Convert article number (handle letters like 21A, 370)
            try:
                art_number = int(re.sub(r"[A-Z]", "", art_num_str))
            except ValueError:
                art_number = 0

            page_num = self._get_page_for_offset(match.start(), page_offsets)
            part_name = f"Part {current_part}"

            chunks.append(ArticleChunk(
                article_id=art_id,
                article_number=art_number,
                title=title,
                part=part_name,
                raw_text=art_text[:8000],  # cap at ~8000 chars
                page_number=page_num,
                chunk_type="article",
            ))

        # Add schedule chunks
        for i, sched_match in enumerate(schedule_matches):
            ordinal = sched_match.group(1).upper()
            sched_num = SCHEDULE_ORDINALS.get(ordinal, i + 1)
            sched_id = f"schedule_{sched_num}"

            end_pos = schedule_matches[i + 1].start() if i + 1 < len(schedule_matches) else len(text)
            sched_text = text[sched_match.start():end_pos].strip()

            chunks.append(ArticleChunk(
                article_id=sched_id,
                article_number=1000 + sched_num,
                title=f"{ordinal.title()} Schedule",
                part="Schedules",
                raw_text=sched_text[:8000],
                page_number=self._get_page_for_offset(sched_match.start(), page_offsets),
                chunk_type="schedule",
            ))

        # Sort by article_number (preamble=0, articles 1-395, schedules 1001+)
        chunks.sort(key=lambda c: c.article_number)
        return chunks

    def _extract_title(self, text: str, article_num: str) -> str:
        """Try to extract a title from the article text."""
        lines = text.split("\n")
        for line in lines[:5]:
            line = line.strip()
            # Skip the article number line itself
            if re.search(rf"Article\s+{re.escape(article_num)}", line, re.IGNORECASE):
                continue
            # Skip very short or numeric-only lines
            if len(line) > 5 and not line.isdigit():
                # Clean up common junk
                clean = re.sub(r"^[\d\.\-—–]+\s*", "", line).strip()
                if len(clean) > 5:
                    return clean[:120]
        return f"Article {article_num}"

    def _get_page_for_offset(self, char_offset: int, page_offsets: list[tuple[int, int]]) -> int:
        """Binary search to find which page a character offset belongs to."""
        page_num = 1
        for offset, pnum in page_offsets:
            if offset <= char_offset:
                page_num = pnum
            else:
                break
        return page_num

    def get_article(self, article_id: str) -> Optional[dict]:
        """Return a single article chunk by ID, or None if not found."""
        chunk = self._chunks.get(article_id)
        return chunk.to_dict() if chunk else None

    def get_all_ids(self) -> list[str]:
        """Return all article IDs in order."""
        return [c.article_id for c in sorted(self._chunks.values(), key=lambda c: c.article_number)]


# Singleton instance (populated after ingest() is called)
_ingestion_instance: Optional[PDFIngestion] = None


def get_ingestion() -> PDFIngestion:
    global _ingestion_instance
    if _ingestion_instance is None:
        _ingestion_instance = PDFIngestion()
    return _ingestion_instance
