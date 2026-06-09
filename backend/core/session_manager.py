"""
core/session_manager.py — Session and progress management for ConstitutionAI.

Manages study sessions, tracks per-article progress, implements spaced repetition,
and computes streak/progress summaries. All DB ops are async via Motor.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from bson import ObjectId

from db.mongodb import sessions_col, article_progress_col
from config import config

logger = logging.getLogger(__name__)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _today_start() -> datetime:
    now = _utcnow()
    return datetime(now.year, now.month, now.day)


class SessionManager:
    """
    Manages study sessions and article progress tracking.

    All methods are async and interact with MongoDB via Motor.
    """

    # ------------------------------------------------------------------
    # Session lifecycle
    # ------------------------------------------------------------------

    async def start_session(self) -> dict:
        """Create a new session document in MongoDB and return it."""
        doc = {
            "date": _utcnow(),
            "articles_covered": [],
            "duration_mins": 0.0,
            "provider_used": "unknown",
            "session_summary": "",
            "completed": False,
        }
        result = await sessions_col().insert_one(doc)
        doc["_id"] = str(result.inserted_id)
        logger.info("Session started: %s", doc["_id"])
        return doc

    async def end_session(
        self,
        session_id: str,
        articles_covered: list[str],
        duration_mins: float = 0.0,
        provider_used: str = "groq",
        session_summary: str = "",
    ) -> None:
        """Mark a session as completed and store final data."""
        await sessions_col().update_one(
            {"_id": ObjectId(session_id)},
            {
                "$set": {
                    "articles_covered": articles_covered,
                    "duration_mins": duration_mins,
                    "provider_used": provider_used,
                    "session_summary": session_summary,
                    "completed": True,
                }
            },
        )
        logger.info("Session %s ended, covered: %s", session_id, articles_covered)

    # ------------------------------------------------------------------
    # Article progress
    # ------------------------------------------------------------------

    async def get_next_article(self) -> Optional[dict]:
        """
        Determine the next article to teach.
        Priority:
          1. Untaught articles (first_taught_date is null), ordered by article_number
          2. Articles needing review where review_due_date <= today
        """
        col = article_progress_col()

        # Priority 1: untaught articles
        untaught = await col.find_one(
            {"first_taught_date": None},
            sort=[("article_number", 1)],
        )
        if untaught:
            untaught["_id"] = str(untaught["_id"])
            return untaught

        # Priority 2: due for review
        review_due = await col.find_one(
            {
                "needs_review": True,
                "review_due_date": {"$lte": _utcnow()},
            },
            sort=[("review_due_date", 1)],
        )
        if review_due:
            review_due["_id"] = str(review_due["_id"])
            return review_due

        return None

    async def mark_article_taught(self, article_id: str, session_id: str) -> None:
        """Record that an article was taught in a session."""
        col = article_progress_col()
        now = _utcnow()

        existing = await col.find_one({"article_id": article_id})
        if existing is None:
            logger.warning("Article %s not found in article_progress — skipping mark.", article_id)
            return

        update = {
            "$set": {"first_taught_date": now},
            "$inc": {"times_reviewed": 1},
        }
        await col.update_one({"article_id": article_id}, update)
        logger.info("Article %s marked as taught in session %s", article_id, session_id)

    async def update_score(self, article_id: str, score: int) -> None:
        """
        Update the score for an article and set review flag based on threshold.
        score < 60 → needs_review=True, review_due_date = today + 3 days
        score >= 60 → needs_review=False
        """
        col = article_progress_col()
        needs_review = score < config.REVIEW_THRESHOLD_SCORE
        review_due = (
            _utcnow() + timedelta(days=config.REVIEW_INTERVAL_DAYS)
            if needs_review
            else None
        )

        await col.update_one(
            {"article_id": article_id},
            {
                "$set": {
                    "last_score": score,
                    "needs_review": needs_review,
                    "review_due_date": review_due,
                }
            },
        )
        logger.info(
            "Score updated for %s: %d (needs_review=%s)", article_id, score, needs_review
        )

    async def cache_lesson(self, article_id: str, lesson_text: str) -> None:
        """Store generated lesson text in MongoDB to avoid redundant API calls."""
        await article_progress_col().update_one(
            {"article_id": article_id},
            {
                "$set": {
                    "cached_lesson": lesson_text,
                    "cached_lesson_date": _utcnow(),
                }
            },
        )

    async def get_cached_lesson(self, article_id: str) -> Optional[str]:
        """
        Return cached lesson if it was generated within LESSON_CACHE_DAYS.
        Returns None if no valid cache exists.
        """
        doc = await article_progress_col().find_one({"article_id": article_id})
        if not doc:
            return None

        cached_lesson = doc.get("cached_lesson", "")
        cached_date = doc.get("cached_lesson_date")

        if not cached_lesson or not cached_date:
            return None

        age_days = (_utcnow() - cached_date).days
        if age_days > config.LESSON_CACHE_DAYS:
            return None

        return cached_lesson

    # ------------------------------------------------------------------
    # Revision mode
    # ------------------------------------------------------------------

    async def jump_to_article(self, article_id: str) -> Optional[dict]:
        """Return an article's progress record for revision mode."""
        doc = await article_progress_col().find_one({"article_id": article_id})
        if doc:
            doc["_id"] = str(doc["_id"])
        return doc

    # ------------------------------------------------------------------
    # Progress summary
    # ------------------------------------------------------------------

    async def get_progress_summary(self) -> dict:
        """
        Compute an aggregated progress summary:
        - total articles taught vs available
        - average score
        - study streak in days
        - weak topics (score < 60)
        - articles needing review
        - recent sessions
        """
        col = article_progress_col()
        session_col = sessions_col()

        # Totals
        total = await col.count_documents({})
        taught = await col.count_documents({"first_taught_date": {"$ne": None}})

        # Average score
        pipeline = [
            {"$match": {"first_taught_date": {"$ne": None}}},
            {"$group": {"_id": None, "avg_score": {"$avg": "$last_score"}}},
        ]
        avg_result = await col.aggregate(pipeline).to_list(1)
        avg_score = round(avg_result[0]["avg_score"], 1) if avg_result else 0.0

        # Weak topics
        weak_cursor = col.find(
            {"last_score": {"$gt": 0, "$lt": config.REVIEW_THRESHOLD_SCORE}},
            sort=[("last_score", 1)],
            limit=10,
        )
        weak_topics = []
        async for doc in weak_cursor:
            doc["_id"] = str(doc["_id"])
            weak_topics.append(doc)

        # Needs review
        review_cursor = col.find(
            {"needs_review": True},
            sort=[("review_due_date", 1)],
            limit=10,
        )
        needs_review = []
        async for doc in review_cursor:
            doc["_id"] = str(doc["_id"])
            needs_review.append(doc)

        # Streak calculation
        streak = await self._calculate_streak()

        # Recent sessions (last 10)
        session_cursor = session_col.find(
            {"completed": True},
            sort=[("date", -1)],
            limit=10,
        )
        recent_sessions = []
        async for doc in session_cursor:
            doc["_id"] = str(doc["_id"])
            recent_sessions.append(doc)

        return {
            "total_articles_taught": taught,
            "total_articles_available": total,
            "percent_complete": round(taught / total * 100, 1) if total > 0 else 0.0,
            "average_score": avg_score,
            "current_streak_days": streak,
            "weak_topics": weak_topics,
            "needs_review": needs_review,
            "recent_sessions": recent_sessions,
        }

    async def _calculate_streak(self) -> int:
        """Count consecutive days with at least one completed session."""
        session_col = sessions_col()
        cursor = session_col.find(
            {"completed": True},
            sort=[("date", -1)],
            projection={"date": 1},
        )
        dates = set()
        async for doc in cursor:
            d = doc["date"]
            dates.add(datetime(d.year, d.month, d.day))

        streak = 0
        check_date = _today_start()
        while check_date in dates:
            streak += 1
            check_date -= timedelta(days=1)
        return streak

    async def get_today_session_count(self) -> int:
        """How many sessions have been started today."""
        today = _today_start()
        tomorrow = today + timedelta(days=1)
        return await sessions_col().count_documents(
            {"date": {"$gte": today, "$lt": tomorrow}}
        )

    async def has_completed_session_today(self) -> bool:
        """True if at least one session was completed today."""
        today = _today_start()
        tomorrow = today + timedelta(days=1)
        count = await sessions_col().count_documents(
            {"date": {"$gte": today, "$lt": tomorrow}, "completed": True}
        )
        return count > 0

    async def get_all_articles(self) -> list[dict]:
        """Return all article progress records, sorted by article_number."""
        cursor = article_progress_col().find({}, sort=[("article_number", 1)])
        articles = []
        async for doc in cursor:
            doc["_id"] = str(doc["_id"])
            articles.append(doc)
        return articles

    async def seed_articles_from_chunks(self, chunks: list[dict]) -> int:
        """
        Pre-populate article_progress with stub records for all ingested articles.
        Uses upsert to avoid duplicates.
        Returns number of new records inserted.
        """
        col = article_progress_col()
        inserted = 0
        for chunk in chunks:
            article_id = chunk["article_id"]
            existing = await col.find_one({"article_id": article_id})
            if existing is None:
                await col.insert_one(
                    {
                        "article_id": article_id,
                        "article_number": chunk.get("article_number", 0),
                        "title": chunk.get("title", ""),
                        "part": chunk.get("part", ""),
                        "first_taught_date": None,
                        "times_reviewed": 0,
                        "last_score": 0,
                        "needs_review": False,
                        "review_due_date": None,
                        "cached_lesson": "",
                        "cached_lesson_date": None,
                    }
                )
                inserted += 1
        logger.info("Seeded %d new article_progress records.", inserted)
        return inserted


# Singleton
_session_manager_instance: Optional[SessionManager] = None


def get_session_manager() -> SessionManager:
    global _session_manager_instance
    if _session_manager_instance is None:
        _session_manager_instance = SessionManager()
    return _session_manager_instance
