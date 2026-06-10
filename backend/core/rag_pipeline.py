"""
core/rag_pipeline.py — ChromaDB vector store for ConstitutionAI.

Embeds constitutional article chunks using sentence-transformers (all-MiniLM-L6-v2)
and stores them in a local persistent ChromaDB collection.
Provides semantic retrieval and exact article context lookup.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class RAGPipeline:
    """
    Manages vector embeddings and retrieval for the Indian Constitution.

    Usage:
        rag = RAGPipeline()
        await rag.initialize()                          # Connect to ChromaDB
        await rag.ingest_articles(article_list)         # Embed + store
        context = await rag.retrieve("right to equality")
    """

    def __init__(self):
        from config import config
        self._config = config
        self._client = None
        self._collection = None
        self._embedding_model = None
        self._is_ready = False
        self._init_lock = asyncio.Lock()

    async def initialize(self) -> None:
        """Set up ChromaDB client and embedding model (idempotent, concurrency-safe)."""
        if self._is_ready:
            return
        async with self._init_lock:
            # Double-checked locking: another coroutine may have finished while we waited
            if self._is_ready:
                return
            await asyncio.get_event_loop().run_in_executor(None, self._sync_initialize)

    def _sync_initialize(self) -> None:
        """Synchronous initialization (run in thread executor)."""
        import chromadb
        from sentence_transformers import SentenceTransformer

        logger.info("Initializing ChromaDB at: %s", self._config.CHROMA_DB_PATH)
        self._client = chromadb.PersistentClient(path=self._config.CHROMA_DB_PATH)
        self._collection = self._client.get_or_create_collection(
            name=self._config.CHROMA_COLLECTION,
            metadata={"hnsw:space": "cosine"},
        )

        logger.info("Loading embedding model: %s", self._config.EMBEDDING_MODEL)
        self._embedding_model = SentenceTransformer(self._config.EMBEDDING_MODEL)
        self._is_ready = True
        logger.info(
            "RAG pipeline ready. Collection '%s' has %d documents.",
            self._config.CHROMA_COLLECTION,
            self._collection.count(),
        )

    @property
    def is_indexed(self) -> bool:
        """True if the ChromaDB collection has any documents."""
        if self._collection is None:
            return False
        return self._collection.count() > 0

    @property
    def document_count(self) -> int:
        """Number of indexed documents."""
        if self._collection is None:
            return 0
        return self._collection.count()

    async def ingest_articles(self, articles: list[dict], batch_size: int = 32) -> int:
        """
        Embed and store article chunks in ChromaDB.
        Skips articles already indexed (by ID).
        Returns number of new articles added.
        """
        if not self._is_ready:
            await self.initialize()

        # Filter out already-indexed articles
        existing_ids = set()
        try:
            existing = self._collection.get(include=[])
            existing_ids = set(existing["ids"])
        except Exception:
            pass

        # Also deduplicate within the incoming list itself (guard against duplicate IDs
        # that can arise if the same heading appears multiple times in the PDF).
        seen_new: set[str] = set()
        deduped_articles: list[dict] = []
        for a in articles:
            aid = a["article_id"]
            if aid not in existing_ids and aid not in seen_new:
                seen_new.add(aid)
                deduped_articles.append(a)

        new_articles = deduped_articles
        if not new_articles:
            logger.info("All %d articles already indexed. Skipping.", len(articles))
            return 0

        logger.info("Embedding %d new articles...", len(new_articles))
        total_added = 0

        for i in range(0, len(new_articles), batch_size):
            batch = new_articles[i:i + batch_size]
            added = await asyncio.get_event_loop().run_in_executor(
                None, self._embed_and_store_batch, batch
            )
            total_added += added
            logger.info(
                "Embedded batch %d/%d (%d articles)",
                i // batch_size + 1,
                (len(new_articles) + batch_size - 1) // batch_size,
                len(batch),
            )

        logger.info("Ingestion complete. Added %d articles.", total_added)
        return total_added

    def _embed_and_store_batch(self, batch: list[dict]) -> int:
        """Embed a batch of articles and upsert into ChromaDB (sync)."""
        ids = [a["article_id"] for a in batch]
        texts = [self._make_embedding_text(a) for a in batch]
        metadatas = [
            {
                "article_number": a.get("article_number", 0),
                "title": a.get("title", ""),
                "part": a.get("part", ""),
                "chunk_type": a.get("chunk_type", "article"),
                "page_number": a.get("page_number", 0),
            }
            for a in batch
        ]

        embeddings = self._embedding_model.encode(texts, show_progress_bar=False).tolist()

        self._collection.upsert(
            ids=ids,
            embeddings=embeddings,
            documents=texts,
            metadatas=metadatas,
        )
        return len(batch)

    def _make_embedding_text(self, article: dict) -> str:
        """Build a rich text representation for embedding."""
        parts = []
        if article.get("title"):
            parts.append(f"Title: {article['title']}")
        if article.get("article_id"):
            parts.append(f"ID: {article['article_id']}")
        if article.get("part"):
            parts.append(f"Part: {article['part']}")
        raw = article.get("raw_text", "")
        parts.append(raw[:3000])  # cap embedding text
        return "\n".join(parts)

    async def retrieve(self, query: str, n_results: int = 3) -> list[str]:
        """
        Semantic retrieval: find the most relevant article texts for a query.
        Returns list of raw article texts.
        """
        if not self._is_ready:
            await self.initialize()
        if self._collection.count() == 0:
            logger.warning("ChromaDB is empty — retrieval will return empty results.")
            return []

        return await asyncio.get_event_loop().run_in_executor(
            None, self._sync_retrieve, query, n_results
        )

    def _sync_retrieve(self, query: str, n_results: int) -> list[str]:
        query_embedding = self._embedding_model.encode([query]).tolist()[0]
        results = self._collection.query(
            query_embeddings=[query_embedding],
            n_results=min(n_results, self._collection.count()),
            include=["documents", "metadatas", "distances"],
        )
        docs = results.get("documents", [[]])[0]
        return docs

    async def get_article_context(self, article_id: str) -> str:
        """
        Retrieve a specific article's stored text by ID.
        Returns empty string if not found.
        """
        if not self._is_ready:
            await self.initialize()

        return await asyncio.get_event_loop().run_in_executor(
            None, self._sync_get_article, article_id
        )

    def _sync_get_article(self, article_id: str) -> str:
        try:
            result = self._collection.get(
                ids=[article_id],
                include=["documents"],
            )
            docs = result.get("documents", [])
            return docs[0] if docs else ""
        except Exception as exc:
            logger.warning("Error fetching article '%s' from ChromaDB: %s", article_id, exc)
            return ""

    async def get_all_article_ids(self) -> list[str]:
        """Return all stored article IDs."""
        if not self._is_ready:
            await self.initialize()
        result = self._collection.get(include=[])
        return result.get("ids", [])


# Singleton
_rag_instance: Optional[RAGPipeline] = None


def get_rag_pipeline() -> RAGPipeline:
    global _rag_instance
    if _rag_instance is None:
        _rag_instance = RAGPipeline()
    return _rag_instance
