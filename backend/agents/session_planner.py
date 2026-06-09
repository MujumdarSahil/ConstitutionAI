"""
agents/session_planner.py — Plans daily study sessions for ConstitutionAI.

Determines what to study next based on MongoDB progress data,
generates motivational messages, and handles revision mode.
"""

from __future__ import annotations

import logging
from typing import Optional

from core.llm_provider import LLMProvider
from core.session_manager import get_session_manager

logger = logging.getLogger(__name__)

PLANNER_SYSTEM_PROMPT = """You are an encouraging UPSC study coach. Generate a SHORT (2-3 sentences) motivational opening message for a student starting their constitutional law study session today.

Be warm, specific to the Indian Constitution, and include one practical tip or encouraging fact. Keep it under 60 words. Be natural and genuine — not generic."""


class SessionPlanner:
    """
    Determines what the student should study next and generates session plans.
    """

    def __init__(self):
        self._llm = LLMProvider()
        self._session_manager = get_session_manager()

    async def plan_session(self) -> dict:
        """
        Generate today's study plan.

        Returns:
        {
            next_article: dict | None,
            estimated_duration_mins: int,
            is_revision: bool,
            message: str,
            today_session_count: int,
            has_completed_today: bool
        }
        """
        sm = self._session_manager
        has_completed_today = await sm.has_completed_session_today()
        today_count = await sm.get_today_session_count()

        next_article = await sm.get_next_article()
        is_revision = False
        estimated_duration = 30

        if next_article:
            is_revision = next_article.get("needs_review", False)
            # Revisions are shorter
            estimated_duration = 20 if is_revision else 35

        # Generate motivational message
        message = await self._generate_message(
            next_article=next_article,
            is_revision=is_revision,
            has_completed_today=has_completed_today,
        )

        return {
            "next_article": next_article,
            "estimated_duration_mins": estimated_duration,
            "is_revision": is_revision,
            "message": message,
            "today_session_count": today_count,
            "has_completed_today": has_completed_today,
        }

    async def _generate_message(
        self,
        next_article: Optional[dict],
        is_revision: bool,
        has_completed_today: bool,
    ) -> str:
        """Generate a personalized motivational message for the session."""
        article_label = ""
        if next_article:
            article_label = (
                next_article.get("title")
                or next_article.get("article_id", "").replace("_", " ").title()
            )

        context_parts = []
        if has_completed_today:
            context_parts.append("The student has already completed a session today and is doing bonus study.")
        if is_revision:
            context_parts.append(f"This is a revision session for {article_label}.")
        elif article_label:
            context_parts.append(f"The student is about to learn about {article_label} of the Indian Constitution.")
        else:
            context_parts.append("The student has completed all available articles — encourage them!")

        context = " ".join(context_parts)
        user_prompt = f"Context: {context}\n\nGenerate the motivational message:"

        try:
            return await self._llm.complete(PLANNER_SYSTEM_PROMPT, user_prompt)
        except Exception as exc:
            logger.warning("Failed to generate motivational message: %s", exc)
            if is_revision:
                return f"Time to strengthen your understanding of {article_label}. Revision is where real mastery is built!"
            elif article_label:
                return f"Ready to explore {article_label}? Every article brings you one step closer to cracking UPSC!"
            else:
                return "Outstanding dedication! Keep pushing — your mastery of the Constitution is growing every day."


# Singleton
_planner_instance: Optional[SessionPlanner] = None


def get_session_planner() -> SessionPlanner:
    global _planner_instance
    if _planner_instance is None:
        _planner_instance = SessionPlanner()
    return _planner_instance
