"""
routers/progress.py — Progress tracking endpoints for ConstitutionAI.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from core.session_manager import get_session_manager

router = APIRouter(prefix="/api", tags=["progress"])


class MarkTaughtRequest(BaseModel):
    article_id: str
    session_id: str


class UpdateScoreRequest(BaseModel):
    article_id: str
    score: int


@router.get("/progress")
async def get_progress():
    """
    Returns comprehensive progress summary:
    - articles taught vs total
    - average score
    - study streak
    - weak topics (score < 60)
    - articles needing review
    - recent sessions
    """
    try:
        sm = get_session_manager()
        summary = await sm.get_progress_summary()
        return summary
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/articles")
async def get_all_articles():
    """
    Returns list of all articles with their progress status.
    Sorted by article_number ascending.
    """
    try:
        sm = get_session_manager()
        articles = await sm.get_all_articles()
        return {"articles": articles, "total": len(articles)}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/articles/{article_id}")
async def get_article_progress(article_id: str):
    """Return progress record for a specific article."""
    try:
        sm = get_session_manager()
        doc = await sm.jump_to_article(article_id)
        if not doc:
            raise HTTPException(status_code=404, detail=f"Article '{article_id}' not found.")
        return doc
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/articles/{article_id}/jump")
async def jump_to_article(article_id: str):
    """
    Revision mode: fetch article progress for direct navigation.
    Returns the article progress record for display in LearnView.
    """
    try:
        sm = get_session_manager()
        doc = await sm.jump_to_article(article_id)
        if not doc:
            raise HTTPException(
                status_code=404,
                detail=f"Article '{article_id}' not found. Run /api/setup first."
            )
        return {"article_id": article_id, "progress": doc, "revision_mode": True}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/articles/mark-taught")
async def mark_article_taught(req: MarkTaughtRequest):
    """Mark an article as taught in the current session."""
    try:
        sm = get_session_manager()
        await sm.mark_article_taught(req.article_id, req.session_id)
        return {"status": "ok", "article_id": req.article_id}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/articles/score")
async def update_article_score(req: UpdateScoreRequest):
    """Update the score for an article (triggers spaced repetition logic)."""
    if not 0 <= req.score <= 100:
        raise HTTPException(status_code=400, detail="Score must be between 0 and 100.")
    try:
        sm = get_session_manager()
        await sm.update_score(req.article_id, req.score)
        return {"status": "ok", "article_id": req.article_id, "score": req.score}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
