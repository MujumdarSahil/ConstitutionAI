"""
main.py — FastAPI application entrypoint for ConstitutionAI.

Startup checks:
  1. MongoDB connectivity
  2. PDF existence
  3. ChromaDB indexed state (auto-triggers ingestion if empty)
  4. CORS configured for Vue frontend (localhost:5173)
"""

from __future__ import annotations

import asyncio
import logging
import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------
# Force UTF-8 on the stdout stream so emoji/unicode in log messages
# don't crash on Windows cp1252 consoles.
_log_handler = logging.StreamHandler(sys.stdout)
_log_handler.stream = open(sys.stdout.fileno(), mode="w", encoding="utf-8", buffering=1, closefd=False)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[_log_handler],
)
logger = logging.getLogger("constitutionai")

# ---------------------------------------------------------------------------
# Lifespan: startup/shutdown checks
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Run startup checks and cleanup on shutdown."""
    logger.info("=" * 60)
    logger.info("  ConstitutionAI Backend Starting Up")
    logger.info("=" * 60)

    # --- Config validation ---
    from config import config
    warnings = config.validate()
    for w in warnings:
        logger.warning("[WARN] %s", w)

    # --- MongoDB check ---
    from db.mongodb import check_connection, close_connection
    mongo_ok = await check_connection()
    if not mongo_ok:
        logger.error(
            "\n" + "=" * 60 +
            "\n  [ERROR] MongoDB is NOT running!\n" +
            "  Please start MongoDB with: mongod --dbpath /path/to/data\n" +
            "  Or install MongoDB: https://www.mongodb.com/try/download/community\n" +
            "=" * 60
        )
        # Don't exit — let the app start so the user sees the error via API
    else:
        logger.info("[OK] MongoDB connected at %s", config.MONGODB_URI)

    # --- PDF check ---
    pdf_path = Path(config.PDF_PATH)
    if not pdf_path.exists():
        logger.warning(
            "\n" + "=" * 60 +
            f"\n  [WARN] Constitution PDF not found at: {config.PDF_PATH}\n" +
            "  Please place your PDF at that path, then call POST /api/setup\n" +
            "  You can download the Constitution from:\n" +
            "  https://legislative.gov.in/constitution-of-india/\n" +
            "=" * 60
        )
    else:
        logger.info("[OK] Constitution PDF found at %s", config.PDF_PATH)

        # --- Schedule ingestion as a background task so startup isn't blocked ---
        asyncio.create_task(_background_ingest(pdf_path))

    logger.info("=" * 60)
    logger.info("  ConstitutionAI ready at http://localhost:8000")
    logger.info("  API docs at http://localhost:8000/docs")
    logger.info("=" * 60)

    yield  # Application runs here

    # Shutdown
    logger.info("Shutting down ConstitutionAI...")
    await close_connection()


async def _background_ingest(pdf_path: Path) -> None:
    """
    Initialize ChromaDB + embedding model and ingest the constitution PDF in the
    background so the server starts accepting requests immediately.
    """
    try:
        from core.rag_pipeline import get_rag_pipeline
        rag = get_rag_pipeline()
        await rag.initialize()

        if not rag.is_indexed:
            logger.info("ChromaDB is empty — starting background ingestion...")
            from core.pdf_ingestion import get_ingestion
            from core.session_manager import get_session_manager

            ingestion = get_ingestion()
            chunks = await asyncio.get_event_loop().run_in_executor(
                None, ingestion.ingest, str(pdf_path)
            )
            added = await rag.ingest_articles(chunks)
            sm = get_session_manager()
            await sm.seed_articles_from_chunks(chunks)
            logger.info(
                "[OK] Background ingestion complete: %d articles embedded, %d MongoDB records seeded.",
                added, len(chunks)
            )
        else:
            logger.info(
                "[OK] ChromaDB already indexed: %d documents ready.", rag.document_count
            )
    except Exception as exc:
        logger.error(
            "Background ingestion failed: %s — Use POST /api/setup to retry.", exc, exc_info=True
        )


# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------

app = FastAPI(
    title="ConstitutionAI",
    description="AI-powered personal tutor for the Indian Constitution — UPSC preparation",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS — allow Vue dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------

from routers.session import router as session_router
from routers.teach import router as teach_router
from routers.test import router as test_router
from routers.progress import router as progress_router

app.include_router(session_router)
app.include_router(teach_router)
app.include_router(test_router)
app.include_router(progress_router)


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

@app.get("/api/health")
async def health():
    """Basic health check endpoint."""
    from db.mongodb import check_connection
    from core.rag_pipeline import get_rag_pipeline
    from config import config

    mongo_ok = await check_connection()
    rag = get_rag_pipeline()

    return {
        "status": "ok",
        "mongodb": "connected" if mongo_ok else "disconnected",
        "chromadb_documents": rag.document_count if rag._is_ready else 0,
        "groq_configured": bool(config.GROQ_API_KEY),
        "gemini_configured": bool(config.GEMINI_API_KEY),
        "pdf_present": Path(config.PDF_PATH).exists(),
    }


@app.get("/")
async def root():
    return {
        "app": "ConstitutionAI",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/api/health",
    }
