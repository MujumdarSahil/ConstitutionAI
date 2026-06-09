"""
core/llm_provider.py — Unified LLM provider for ConstitutionAI.

Primary:  Groq (llama-3.3-70b-versatile)
Fallback: Google Gemini (gemini-1.5-flash)

Implements exponential backoff (3 attempts per provider) and
automatic failover. Raises ProviderUnavailableError if both fail.
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Optional

import httpx

logger = logging.getLogger(__name__)


class ProviderUnavailableError(Exception):
    """Raised when both Groq and Gemini providers are unavailable."""

    def __init__(self, message: str = "All AI providers are currently unavailable. Please check your API keys and try again."):
        super().__init__(message)
        self.user_message = message


class LLMProvider:
    """
    Unified async LLM provider with automatic failover.

    Usage:
        provider = LLMProvider()
        response = await provider.complete(system_prompt, user_prompt)
    """

    def __init__(self):
        from config import config
        self._config = config
        self._last_provider: str = "none"
        self._groq_client = None
        self._gemini_model = None
        self._initialize_clients()

    def _initialize_clients(self):
        """Lazily initialize API clients only if keys are available."""
        if self._config.GROQ_API_KEY:
            try:
                from groq import Groq, AsyncGroq
                self._groq_client = AsyncGroq(api_key=self._config.GROQ_API_KEY)
                logger.info("Groq client initialized.")
            except ImportError:
                logger.warning("groq package not installed — Groq provider disabled.")
        else:
            logger.warning("GROQ_API_KEY not set — Groq provider disabled.")

        if self._config.GEMINI_API_KEY:
            try:
                import google.generativeai as genai
                genai.configure(api_key=self._config.GEMINI_API_KEY)
                self._gemini_model = genai.GenerativeModel(self._config.GEMINI_MODEL)
                logger.info("Gemini client initialized.")
            except ImportError:
                logger.warning("google-generativeai package not installed — Gemini provider disabled.")
        else:
            logger.warning("GEMINI_API_KEY not set — Gemini fallback disabled.")

    @property
    def last_provider(self) -> str:
        """Name of the provider used in the most recent call."""
        return self._last_provider

    async def complete(self, system_prompt: str, user_prompt: str) -> str:
        """
        Run an LLM completion with automatic failover.

        Tries Groq first (3 attempts with exponential backoff),
        then falls back to Gemini (3 attempts), then raises.
        """
        errors: list[str] = []

        # --- Try Groq ---
        if self._groq_client is not None:
            result, error = await self._try_groq(system_prompt, user_prompt)
            if result is not None:
                return result
            errors.append(f"Groq: {error}")
            logger.warning("Groq failed, attempting Gemini fallback. Error: %s", error)

        # --- Try Gemini ---
        if self._gemini_model is not None:
            result, error = await self._try_gemini(system_prompt, user_prompt)
            if result is not None:
                return result
            errors.append(f"Gemini: {error}")
            logger.error("Gemini also failed. Error: %s", error)

        # --- Both failed ---
        combined = " | ".join(errors)
        logger.critical("All LLM providers failed: %s", combined)
        raise ProviderUnavailableError(
            f"All AI providers are currently unavailable. Details: {combined}"
        )

    async def _try_groq(self, system_prompt: str, user_prompt: str) -> tuple[Optional[str], Optional[str]]:
        """Attempt Groq completion with exponential backoff. Returns (result, error)."""
        max_retries = self._config.MAX_RETRIES_PER_PROVIDER
        base_delay = self._config.RETRY_BASE_DELAY

        for attempt in range(max_retries):
            try:
                logger.debug("Groq attempt %d/%d", attempt + 1, max_retries)
                response = await self._groq_client.chat.completions.create(
                    model=self._config.GROQ_MODEL,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    temperature=0.7,
                    max_tokens=4096,
                )
                content = response.choices[0].message.content
                self._last_provider = "groq"
                logger.info("Groq completion succeeded on attempt %d", attempt + 1)
                return content, None

            except Exception as exc:
                error_name = type(exc).__name__
                logger.warning("Groq attempt %d failed: %s — %s", attempt + 1, error_name, exc)

                # Check if it's a rate limit or server error that warrants retry
                is_retryable = any(
                    keyword in error_name.lower()
                    for keyword in ["ratelimit", "timeout", "server", "connection", "service"]
                ) or "429" in str(exc) or "500" in str(exc) or "503" in str(exc)

                if not is_retryable or attempt == max_retries - 1:
                    return None, str(exc)

                delay = base_delay * (2 ** attempt)
                logger.info("Waiting %.1fs before Groq retry...", delay)
                await asyncio.sleep(delay)

        return None, "Max retries exceeded"

    async def _try_gemini(self, system_prompt: str, user_prompt: str) -> tuple[Optional[str], Optional[str]]:
        """Attempt Gemini completion with exponential backoff. Returns (result, error)."""
        max_retries = self._config.MAX_RETRIES_PER_PROVIDER
        base_delay = self._config.RETRY_BASE_DELAY

        combined_prompt = f"{system_prompt}\n\n---\n\n{user_prompt}"

        for attempt in range(max_retries):
            try:
                logger.debug("Gemini attempt %d/%d", attempt + 1, max_retries)
                # Gemini's generate_content is synchronous — run in executor
                response = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: self._gemini_model.generate_content(combined_prompt)
                )
                content = response.text
                self._last_provider = "gemini"
                logger.info("Gemini completion succeeded on attempt %d", attempt + 1)
                return content, None

            except Exception as exc:
                error_name = type(exc).__name__
                logger.warning("Gemini attempt %d failed: %s — %s", attempt + 1, error_name, exc)

                is_retryable = any(
                    keyword in error_name.lower()
                    for keyword in ["ratelimit", "quota", "timeout", "server", "resource"]
                ) or "429" in str(exc) or "500" in str(exc) or "503" in str(exc)

                if not is_retryable or attempt == max_retries - 1:
                    return None, str(exc)

                delay = base_delay * (2 ** attempt)
                logger.info("Waiting %.1fs before Gemini retry...", delay)
                await asyncio.sleep(delay)

        return None, "Max retries exceeded"

    async def complete_stream(self, system_prompt: str, user_prompt: str):
        """
        Yield text chunks for streaming SSE responses.
        Falls back to chunking a regular completion if streaming fails.
        """
        # Try Groq streaming first
        if self._groq_client is not None:
            try:
                stream = await self._groq_client.chat.completions.create(
                    model=self._config.GROQ_MODEL,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    temperature=0.7,
                    max_tokens=4096,
                    stream=True,
                )
                self._last_provider = "groq"
                async for chunk in stream:
                    delta = chunk.choices[0].delta.content
                    if delta:
                        yield delta
                return
            except Exception as exc:
                logger.warning("Groq streaming failed, falling back: %s", exc)

        # Fallback: regular completion then chunk by words
        try:
            full_text = await self.complete(system_prompt, user_prompt)
            words = full_text.split(" ")
            for i, word in enumerate(words):
                separator = " " if i < len(words) - 1 else ""
                yield word + separator
                await asyncio.sleep(0.01)  # tiny delay for effect
        except ProviderUnavailableError:
            yield "[Error: AI providers unavailable. Please check your API keys.]"
