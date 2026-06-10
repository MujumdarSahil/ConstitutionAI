"""
config.py — Central configuration for ConstitutionAI backend.
Loads environment variables from .env via python-dotenv.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from the backend directory
_env_path = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=_env_path)


class Config:
    """Typed configuration object for all environment variables."""

    # API Keys
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")

    # MongoDB
    MONGODB_URI: str = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
    DB_NAME: str = os.getenv("DB_NAME", "jarvis")

    # Storage paths
    CHROMA_DB_PATH: str = os.getenv("CHROMA_DB_PATH", "./chroma_db")
    PDF_PATH: str = os.getenv("PDF_PATH", "./data/constitution.pdf")

    # AI Model settings
    GROQ_MODEL: str = "llama-3.3-70b-versatile"
    GEMINI_MODEL: str = "gemini-1.5-flash"

    # LLM retry settings
    MAX_RETRIES_PER_PROVIDER: int = 3
    RETRY_BASE_DELAY: float = 1.0  # seconds

    # Session settings
    REVIEW_THRESHOLD_SCORE: int = 60       # Below this → needs review
    REVIEW_INTERVAL_DAYS: int = 3          # Days until re-review
    LESSON_CACHE_DAYS: int = 7             # Days before regenerating cached lesson

    # Embedding model
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"
    CHROMA_COLLECTION: str = "constitution_articles"

    @classmethod
    def validate(cls) -> list[str]:
        """Return list of missing critical configuration keys."""
        warnings = []
        if not cls.GROQ_API_KEY:
            warnings.append("GROQ_API_KEY is not set — Groq provider will be unavailable")
        if not cls.GEMINI_API_KEY:
            warnings.append("GEMINI_API_KEY is not set — Gemini fallback will be unavailable")
        if not cls.GROQ_API_KEY and not cls.GEMINI_API_KEY:
            warnings.append("CRITICAL: No AI provider keys configured. The app will not function.")
        return warnings


config = Config()
