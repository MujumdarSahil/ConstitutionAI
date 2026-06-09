"""
routers/test.py — Quiz generation and grading endpoints for ConstitutionAI.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from agents.test_generator import get_test_generator

router = APIRouter(prefix="/api/test", tags=["test"])


class SubmitAnswerRequest(BaseModel):
    test_result_id: str
    user_answer: str


@router.get("/{session_id}")
async def generate_test(session_id: str, article_ids: str = ""):
    """
    Generate a quiz for the given session.
    Pass article IDs as comma-separated query param: ?article_ids=article_14,article_15
    Returns a list of question objects with their MongoDB IDs.
    """
    ids = [a.strip() for a in article_ids.split(",") if a.strip()] if article_ids else []
    if not ids:
        raise HTTPException(
            status_code=400,
            detail="Provide article_ids as comma-separated query parameter, e.g. ?article_ids=article_14,article_15"
        )

    try:
        gen = get_test_generator()
        questions = await gen.generate_test(ids, session_id)
        return {"session_id": session_id, "questions": questions, "total": len(questions)}
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/submit")
async def submit_answer(req: SubmitAnswerRequest):
    """
    Submit and grade a single answer.
    Returns: is_correct, score (0–100), correct_answer, ai_explanation.
    """
    try:
        gen = get_test_generator()
        result = await gen.submit_answer(req.test_result_id, req.user_answer)
        return result
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
