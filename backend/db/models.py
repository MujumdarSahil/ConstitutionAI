"""
db/models.py — Pydantic models for all MongoDB collections in ConstitutionAI.
Handles ObjectId serialization for FastAPI JSON responses.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional
from bson import ObjectId
from pydantic import BaseModel, Field, field_validator, model_validator
from pydantic.functional_validators import BeforeValidator
from typing import Annotated


# ---------------------------------------------------------------------------
# ObjectId helper — converts BSON ObjectId to string for JSON serialization
# ---------------------------------------------------------------------------

def _validate_object_id(v: Any) -> str:
    if isinstance(v, ObjectId):
        return str(v)
    if isinstance(v, str) and ObjectId.is_valid(v):
        return v
    raise ValueError(f"Invalid ObjectId: {v}")


PyObjectId = Annotated[str, BeforeValidator(_validate_object_id)]


class MongoBaseModel(BaseModel):
    """Base model with MongoDB _id handling."""
    id: Optional[PyObjectId] = Field(default=None, alias="_id")

    model_config = {
        "populate_by_name": True,
        "arbitrary_types_allowed": True,
    }


# ---------------------------------------------------------------------------
# Session model
# ---------------------------------------------------------------------------

class Session(MongoBaseModel):
    """Represents a study session."""
    date: datetime = Field(default_factory=datetime.utcnow)
    articles_covered: list[str] = Field(default_factory=list)
    duration_mins: float = 0.0
    provider_used: str = "unknown"
    session_summary: str = ""
    completed: bool = False


class SessionCreate(BaseModel):
    """Input for creating a new session."""
    pass  # session is auto-created with defaults


class SessionEnd(BaseModel):
    """Input for ending a session."""
    session_id: str
    articles_covered: list[str]
    duration_mins: float = 0.0
    provider_used: str = "groq"
    session_summary: str = ""


# ---------------------------------------------------------------------------
# ArticleProgress model
# ---------------------------------------------------------------------------

class ArticleProgress(MongoBaseModel):
    """Tracks a student's progress through a constitutional article."""
    article_id: str                          # e.g. "article_21"
    article_number: int = 0                  # numeric sort key
    title: str = ""
    part: str = ""
    first_taught_date: Optional[datetime] = None
    times_reviewed: int = 0
    last_score: int = 0                      # 0–100
    needs_review: bool = False
    review_due_date: Optional[datetime] = None
    cached_lesson: str = ""
    cached_lesson_date: Optional[datetime] = None


class ArticleProgressUpdate(BaseModel):
    """Fields that can be updated on ArticleProgress."""
    last_score: Optional[int] = None
    needs_review: Optional[bool] = None
    review_due_date: Optional[datetime] = None
    cached_lesson: Optional[str] = None
    cached_lesson_date: Optional[datetime] = None
    times_reviewed: Optional[int] = None
    first_taught_date: Optional[datetime] = None


# ---------------------------------------------------------------------------
# TestResult model
# ---------------------------------------------------------------------------

class TestResult(MongoBaseModel):
    """Represents a single quiz question result within a session."""
    session_id: str
    article_id: str
    question: str
    question_type: str                       # "mcq" | "match" | "short_answer"
    options: Optional[list[str]] = None      # for MCQ
    user_answer: Optional[str] = None
    correct_answer: str = ""
    is_correct: Optional[bool] = None
    score: int = 0
    ai_explanation: str = ""


class AnswerSubmission(BaseModel):
    """Input for submitting a test answer."""
    test_result_id: str
    user_answer: str


class AnswerResponse(BaseModel):
    """Response after grading a submitted answer."""
    test_result_id: str
    is_correct: bool
    score: int
    correct_answer: str
    ai_explanation: str


# ---------------------------------------------------------------------------
# Progress summary model
# ---------------------------------------------------------------------------

class ProgressSummary(BaseModel):
    """Aggregated progress across all articles and sessions."""
    total_articles_taught: int = 0
    total_articles_available: int = 0
    percent_complete: float = 0.0
    average_score: float = 0.0
    current_streak_days: int = 0
    weak_topics: list[dict] = Field(default_factory=list)
    needs_review: list[dict] = Field(default_factory=list)
    recent_sessions: list[dict] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Session plan model
# ---------------------------------------------------------------------------

class SessionPlan(BaseModel):
    """Plan for today's study session."""
    next_article: Optional[dict] = None
    estimated_duration_mins: int = 30
    is_revision: bool = False
    message: str = ""
    today_session_count: int = 0
    has_completed_today: bool = False
