"""
routers/session.py — Session lifecycle endpoints for ConstitutionAI.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from agents.session_planner import get_session_planner
from core.session_manager import get_session_manager

router = APIRouter(prefix="/api/session", tags=["session"])


class EndSessionRequest(BaseModel):
    session_id: str
    articles_covered: list[str]
    duration_mins: float = 0.0
    provider_used: str = "groq"
    session_summary: str = ""


@router.get("/plan")
async def get_session_plan():
    """
    Returns today's session plan including next article, estimated duration,
    motivational message, and revision/new status.
    """
    try:
        planner = get_session_planner()
        plan = await planner.plan_session()
        return plan
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/start")
async def start_session():
    """
    Creates a new study session in MongoDB.
    Returns the session document with its ID.
    """
    try:
        sm = get_session_manager()
        session = await sm.start_session()
        return session
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/end")
async def end_session(req: EndSessionRequest):
    """
    Marks a session as completed, saves all progress.
    """
    try:
        sm = get_session_manager()
        await sm.end_session(
            session_id=req.session_id,
            articles_covered=req.articles_covered,
            duration_mins=req.duration_mins,
            provider_used=req.provider_used,
            session_summary=req.session_summary,
        )
        return {"status": "ok", "session_id": req.session_id, "message": "Session completed successfully."}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
