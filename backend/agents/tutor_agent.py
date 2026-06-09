"""
agents/tutor_agent.py — AI tutor for the Indian Constitution.

Generates rich, UPSC-focused lessons for each constitutional article.
Checks MongoDB for a cached lesson (within 7 days) before calling the LLM.
Uses RAG pipeline for accurate article text retrieval.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional, AsyncIterator

from core.llm_provider import LLMProvider, ProviderUnavailableError
from core.rag_pipeline import get_rag_pipeline
from core.session_manager import get_session_manager

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# System prompt for the tutor agent
# ---------------------------------------------------------------------------

TUTOR_SYSTEM_PROMPT = """You are a brilliant, engaging constitutional law professor and UPSC expert tutor specializing in the Indian Constitution. Your teaching style combines legal precision with accessible storytelling. You are teaching a UPSC Civil Services aspirant.

For each article or constitutional provision, you MUST cover ALL of the following sections in order. Use clear section headers exactly as shown below.

## Article [NUMBER]: [TITLE]

### What it says
Plain English explanation of the article text. Be precise but accessible. Quote the actual constitutional language where helpful.

### Historical context
Why was this article included? What debates happened in the Constituent Assembly? Who championed or opposed it? Reference Dr. B.R. Ambedkar, Jawaharlal Nehru, Sardar Patel, or other framers where relevant. Include the year and political circumstances.

### Landmark judgements
List 3–5 real Supreme Court or High Court cases that interpreted or defined this article. For each case give: case name, year, bench size/composition, and what it decided. CRITICAL: Only cite real, verifiable cases. If uncertain about a case name or year, add "(verify this case)" after it. Never fabricate case citations.

### Key amendments
Which constitutional amendments changed this article, when, and why? What was the political context? How did it affect the balance of power? If no amendments apply, state that clearly.

### Evolution (1947–2026)
How has the interpretation or application of this article evolved from independence to today? Include significant shifts in jurisprudence, executive action, and parliamentary practice. Include recent developments up to 2026.

### UPSC angle
What aspects of this article are most commonly asked in UPSC Prelims, Mains, and Interview? What concepts, keywords, and distinctions must the aspirant master? Include typical question patterns and how to answer them.

### Connected articles
Which other articles must be read alongside this one? Why are they related? Provide specific article numbers and their titles.

Write in a warm, intellectual tone. Use bullet points within sections for clarity. Each section should be 3–8 sentences or bullet points minimum. This is a comprehensive lesson, not a summary."""


class TutorAgent:
    """
    Generates comprehensive constitutional lessons for UPSC aspirants.

    Caches lessons in MongoDB to avoid redundant LLM calls.
    """

    def __init__(self):
        self._llm = LLMProvider()
        self._rag = get_rag_pipeline()
        self._session_manager = get_session_manager()

    async def teach_article(self, article_id: str) -> dict:
        """
        Generate or retrieve a cached lesson for an article.

        Returns a dict with:
        - article_id
        - lesson_text (full markdown)
        - from_cache (bool)
        - provider_used (str)
        """
        # Check cache first
        cached = await self._session_manager.get_cached_lesson(article_id)
        if cached:
            logger.info("Returning cached lesson for %s", article_id)
            return {
                "article_id": article_id,
                "lesson_text": cached,
                "from_cache": True,
                "provider_used": "cache",
            }

        # Retrieve article context from RAG
        article_context = await self._rag.get_article_context(article_id)
        if not article_context:
            # Fallback: semantic search by article_id
            results = await self._rag.retrieve(
                f"Indian Constitution {article_id.replace('_', ' ')}", n_results=2
            )
            article_context = "\n\n".join(results) if results else ""
            logger.warning(
                "Direct context not found for %s, using semantic search fallback.", article_id
            )

        # Build user prompt
        user_prompt = self._build_user_prompt(article_id, article_context)

        # Call LLM
        try:
            lesson_text = await self._llm.complete(TUTOR_SYSTEM_PROMPT, user_prompt)
        except ProviderUnavailableError as exc:
            logger.error("LLM unavailable for article %s: %s", article_id, exc)
            raise

        # Cache in MongoDB
        await self._session_manager.cache_lesson(article_id, lesson_text)
        logger.info(
            "Lesson generated for %s using %s", article_id, self._llm.last_provider
        )

        return {
            "article_id": article_id,
            "lesson_text": lesson_text,
            "from_cache": False,
            "provider_used": self._llm.last_provider,
        }

    async def teach_article_stream(self, article_id: str) -> AsyncIterator[str]:
        """
        Stream the lesson generation token by token for SSE delivery.
        If a cached lesson exists, streams it word by word.
        """
        import asyncio

        cached = await self._session_manager.get_cached_lesson(article_id)
        if cached:
            logger.info("Streaming cached lesson for %s", article_id)
            words = cached.split(" ")
            for i, word in enumerate(words):
                sep = " " if i < len(words) - 1 else ""
                yield word + sep
                await asyncio.sleep(0.005)
            return

        # Get article context
        article_context = await self._rag.get_article_context(article_id)
        if not article_context:
            results = await self._rag.retrieve(
                f"Indian Constitution {article_id.replace('_', ' ')}", n_results=2
            )
            article_context = "\n\n".join(results) if results else ""

        user_prompt = self._build_user_prompt(article_id, article_context)

        # Collect full text while streaming (for caching)
        full_text_parts = []
        async for chunk in self._llm.complete_stream(TUTOR_SYSTEM_PROMPT, user_prompt):
            full_text_parts.append(chunk)
            yield chunk

        # Cache after stream completes
        full_text = "".join(full_text_parts)
        if full_text.strip():
            await self._session_manager.cache_lesson(article_id, full_text)
            logger.info(
                "Streamed and cached lesson for %s (%d chars)", article_id, len(full_text)
            )

    def _build_user_prompt(self, article_id: str, article_context: str) -> str:
        """Build the user prompt for lesson generation."""
        article_label = article_id.replace("_", " ").title()
        context_section = (
            f"\n\nHere is the actual constitutional text for reference:\n\n```\n{article_context[:3000]}\n```"
            if article_context
            else ""
        )
        return (
            f"Teach me about {article_label} of the Indian Constitution for my UPSC Civil Services preparation."
            f"{context_section}\n\n"
            f"Follow the exact section structure from your instructions. Be comprehensive and accurate."
        )


# Singleton
_tutor_agent_instance: Optional[TutorAgent] = None


def get_tutor_agent() -> TutorAgent:
    global _tutor_agent_instance
    if _tutor_agent_instance is None:
        _tutor_agent_instance = TutorAgent()
    return _tutor_agent_instance
