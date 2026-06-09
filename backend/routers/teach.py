"""
routers/teach.py — Lesson delivery endpoints for ConstitutionAI.

Provides SSE streaming for live typing effect and setup/ingestion endpoints.
"""

from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from sse_starlette.sse import EventSourceResponse

from agents.tutor_agent import get_tutor_agent
from core.llm_provider import ProviderUnavailableError
from core.pdf_ingestion import get_ingestion
from core.rag_pipeline import get_rag_pipeline
from core.session_manager import get_session_manager
from config import config

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["teach"])


@router.post("/setup")
async def setup(background: bool = False):
    """
    Trigger PDF ingestion + ChromaDB indexing.
    Returns a StreamingResponse with real-time progress updates (newline-delimited JSON).
    """
    async def progress_stream():
        def send(msg: str, step: int = 0, total: int = 0, done: bool = False, error: str = ""):
            return json.dumps({
                "message": msg,
                "step": step,
                "total": total,
                "done": done,
                "error": error,
            }) + "\n"

        # Step 1: Check PDF
        pdf_path = config.PDF_PATH
        yield send("Checking for constitution PDF...", step=1, total=5)
        await asyncio.sleep(0.1)

        if not Path(pdf_path).exists():
            yield send(
                f"PDF not found at {pdf_path}. Please place your constitution PDF at this path.",
                step=1, total=5, done=True,
                error=f"PDF missing: {pdf_path}"
            )
            return

        yield send("PDF found. Starting ingestion...", step=2, total=5)
        await asyncio.sleep(0.1)

        # Step 2: Parse PDF
        try:
            ingestion = get_ingestion()
            chunks = await asyncio.get_event_loop().run_in_executor(
                None, ingestion.ingest, pdf_path
            )
            yield send(f"Parsed {len(chunks)} constitutional chunks from PDF.", step=3, total=5)
            await asyncio.sleep(0.1)
        except Exception as exc:
            logger.exception("PDF ingestion failed")
            yield send(f"PDF parsing failed: {exc}", done=True, error=str(exc))
            return

        # Step 3: Initialize RAG
        try:
            rag = get_rag_pipeline()
            await rag.initialize()
            yield send("ChromaDB initialized. Embedding articles...", step=4, total=5)
        except Exception as exc:
            logger.exception("RAG initialization failed")
            yield send(f"ChromaDB setup failed: {exc}", done=True, error=str(exc))
            return

        # Step 4: Ingest into ChromaDB
        try:
            added = await rag.ingest_articles(chunks)
            yield send(
                f"Indexed {added} new articles into ChromaDB "
                f"(total: {rag.document_count}).",
                step=4, total=5
            )
        except Exception as exc:
            logger.exception("ChromaDB ingestion failed")
            yield send(f"Embedding failed: {exc}", done=True, error=str(exc))
            return

        # Step 5: Seed MongoDB article_progress
        try:
            sm = get_session_manager()
            seeded = await sm.seed_articles_from_chunks(chunks)
            yield send(
                f"Seeded {seeded} article progress records in MongoDB.",
                step=5, total=5
            )
        except Exception as exc:
            logger.exception("MongoDB seeding failed")
            yield send(f"MongoDB seeding failed: {exc}", done=True, error=str(exc))
            return

        yield send(
            f"Setup complete! {len(chunks)} articles ready to study.",
            step=5, total=5, done=True
        )

    return StreamingResponse(progress_stream(), media_type="application/x-ndjson")


@router.get("/teach/{article_id}")
async def teach_article(article_id: str, stream: bool = True):
    """
    Deliver a constitutional lesson via SSE (Server-Sent Events).
    The lesson streams token by token for a live typing effect.
    Set ?stream=false to get the full lesson as JSON.
    """
    tutor = get_tutor_agent()

    if not stream:
        # Non-streaming: return full lesson as JSON
        try:
            result = await tutor.teach_article(article_id)
            return result
        except ProviderUnavailableError as exc:
            raise HTTPException(status_code=503, detail=exc.user_message)
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc))

    # Streaming via SSE
    async def event_generator():
        provider_sent = False
        try:
            async for chunk in tutor.teach_article_stream(article_id):
                # Send provider info on first chunk
                if not provider_sent:
                    provider_info = json.dumps({
                        "type": "provider",
                        "provider": tutor._llm.last_provider or "groq",
                    })
                    yield {"event": "meta", "data": provider_info}
                    provider_sent = True

                yield {"event": "token", "data": chunk}

            # Done event
            yield {"event": "done", "data": json.dumps({"type": "done"})}

        except ProviderUnavailableError as exc:
            yield {"event": "error", "data": json.dumps({"error": exc.user_message})}
        except Exception as exc:
            logger.exception("Error streaming lesson for %s", article_id)
            yield {"event": "error", "data": json.dumps({"error": str(exc)})}

    return EventSourceResponse(event_generator())
