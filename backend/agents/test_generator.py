"""
agents/test_generator.py — Quiz generation and grading for ConstitutionAI.

Generates 3 MCQ + 2 match-the-following + 1 short answer per session.
Stores questions in MongoDB, grades submitted answers, and provides AI explanations.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Optional

from bson import ObjectId

from core.llm_provider import LLMProvider, ProviderUnavailableError
from core.rag_pipeline import get_rag_pipeline
from db.mongodb import test_results_col

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# System prompt for test generation
# ---------------------------------------------------------------------------

TEST_GENERATOR_SYSTEM_PROMPT = """You are an expert UPSC Civil Services examination question setter specializing in the Indian Constitution.

Generate exactly 6 questions based on the provided constitutional articles:
- 3 Multiple Choice Questions (MCQ) with 4 options each, exactly 1 correct answer
- 2 Match-the-Following questions (presented as MCQ with 4 options showing different match combinations)
- 1 Short Answer reasoning question requiring a 3–4 sentence analytical response

CRITICAL RULES:
1. Return ONLY valid JSON — no markdown code blocks, no preamble, no explanation outside the JSON
2. The JSON must be a valid array of exactly 6 question objects
3. Never fabricate case names or amendment numbers — if uncertain, omit the reference
4. Questions must test genuine understanding, not just memory
5. MCQ options must be plausible distractors, not obviously wrong

REQUIRED JSON SCHEMA (return exactly this structure):
[
  {
    "question": "string — the full question text",
    "type": "mcq",
    "options": ["Option A text", "Option B text", "Option C text", "Option D text"],
    "correct_answer": "Option A text",
    "explanation": "string — 2-3 sentences explaining why this is correct and why others are wrong"
  },
  {
    "question": "string — match the following question text listing items to match",
    "type": "match",
    "options": [
      "A-1, B-2, C-3, D-4",
      "A-2, B-1, C-4, D-3",
      "A-3, B-4, C-1, D-2",
      "A-1, B-3, C-2, D-4"
    ],
    "correct_answer": "A-1, B-2, C-3, D-4",
    "explanation": "string — explaining each match"
  },
  {
    "question": "string — analytical short answer question (e.g., Analyze how Article X has evolved...)",
    "type": "short_answer",
    "options": null,
    "correct_answer": "string — model answer in 3-4 sentences with key points",
    "explanation": "string — evaluation criteria and key concepts that should be mentioned"
  }
]

Make all questions relevant to UPSC Prelims and Mains preparation."""


GRADING_SYSTEM_PROMPT = """You are a strict but fair UPSC examiner grading a student's answer.

Evaluate the student's answer against the correct answer and provide:
1. is_correct: boolean — true only if the answer demonstrates clear understanding of the correct concept
2. score: integer 0–100 — partial credit allowed for partially correct answers
3. explanation: 2-3 sentences explaining what was right, what was missing, and key learning points

Return ONLY valid JSON in this exact format:
{
  "is_correct": true/false,
  "score": 0-100,
  "explanation": "string"
}

Be strict but fair. Paraphrasing of the correct answer is acceptable. Completely wrong answers score 0."""


class TestGenerator:
    """
    Generates UPSC-style quizzes and grades submitted answers.
    Stores all questions and results in MongoDB.
    """

    def __init__(self):
        self._llm = LLMProvider()
        self._rag = get_rag_pipeline()

    async def generate_test(self, article_ids: list[str], session_id: str) -> list[dict]:
        """
        Generate a test for the given articles and store in MongoDB.
        Returns list of question dicts with their MongoDB IDs.
        """
        # Build context from RAG
        context_parts = []
        for article_id in article_ids[:3]:  # limit context
            ctx = await self._rag.get_article_context(article_id)
            if ctx:
                context_parts.append(f"=== {article_id.replace('_', ' ').title()} ===\n{ctx[:2000]}")

        if not context_parts:
            for article_id in article_ids[:2]:
                results = await self._rag.retrieve(
                    f"Indian Constitution {article_id.replace('_', ' ')}", n_results=1
                )
                if results:
                    context_parts.extend(results)

        context = "\n\n".join(context_parts) if context_parts else "No context available."

        articles_label = ", ".join(a.replace("_", " ").title() for a in article_ids)
        user_prompt = (
            f"Generate 6 UPSC-style questions covering: {articles_label}\n\n"
            f"Constitutional text reference:\n{context[:4000]}\n\n"
            f"Return ONLY the JSON array. No other text."
        )

        # Call LLM
        try:
            raw_response = await self._llm.complete(TEST_GENERATOR_SYSTEM_PROMPT, user_prompt)
        except ProviderUnavailableError as exc:
            logger.error("Cannot generate test — LLM unavailable: %s", exc)
            raise

        # Parse JSON
        questions = self._parse_questions(raw_response)
        if not questions:
            logger.error("Failed to parse test questions from LLM response")
            raise ValueError("LLM returned invalid JSON for test questions")

        # Store in MongoDB
        stored_questions = []
        col = test_results_col()
        for q in questions:
            doc = {
                "session_id": session_id,
                "article_id": article_ids[0] if article_ids else "",
                "question": q.get("question", ""),
                "question_type": q.get("type", "mcq"),
                "options": q.get("options"),
                "user_answer": None,
                "correct_answer": q.get("correct_answer", ""),
                "is_correct": None,
                "score": 0,
                "ai_explanation": q.get("explanation", ""),
            }
            result = await col.insert_one(doc)
            doc["_id"] = str(result.inserted_id)
            stored_questions.append(doc)

        logger.info(
            "Generated %d questions for session %s using %s",
            len(stored_questions), session_id, self._llm.last_provider
        )
        return stored_questions

    async def submit_answer(self, test_result_id: str, user_answer: str) -> dict:
        """
        Grade a submitted answer, update MongoDB, and return score + explanation.
        """
        col = test_results_col()
        doc = await col.find_one({"_id": ObjectId(test_result_id)})
        if not doc:
            raise ValueError(f"Test result {test_result_id} not found")

        question_type = doc.get("question_type", "mcq")
        correct_answer = doc.get("correct_answer", "")
        question_text = doc.get("question", "")
        existing_explanation = doc.get("ai_explanation", "")

        # Grade based on question type
        if question_type in ("mcq", "match"):
            # Exact match grading for MCQ/Match
            is_correct = user_answer.strip().lower() == correct_answer.strip().lower()
            score = 100 if is_correct else 0
            explanation = (
                f"Correct! {existing_explanation}"
                if is_correct
                else f"Incorrect. The correct answer is: {correct_answer}. {existing_explanation}"
            )
        else:
            # AI grading for short answer
            is_correct, score, explanation = await self._grade_short_answer(
                question_text, user_answer, correct_answer
            )

        # Update MongoDB
        await col.update_one(
            {"_id": ObjectId(test_result_id)},
            {
                "$set": {
                    "user_answer": user_answer,
                    "is_correct": is_correct,
                    "score": score,
                    "ai_explanation": explanation,
                }
            },
        )

        return {
            "test_result_id": test_result_id,
            "is_correct": is_correct,
            "score": score,
            "correct_answer": correct_answer,
            "ai_explanation": explanation,
        }

    async def _grade_short_answer(
        self, question: str, user_answer: str, correct_answer: str
    ) -> tuple[bool, int, str]:
        """Use LLM to grade a short answer response."""
        user_prompt = (
            f"Question: {question}\n\n"
            f"Model Answer: {correct_answer}\n\n"
            f"Student's Answer: {user_answer}\n\n"
            f"Grade the student's answer. Return ONLY the JSON object."
        )

        try:
            raw = await self._llm.complete(GRADING_SYSTEM_PROMPT, user_prompt)
            grading = self._parse_grading(raw)
            return (
                grading.get("is_correct", False),
                grading.get("score", 0),
                grading.get("explanation", ""),
            )
        except Exception as exc:
            logger.warning("AI grading failed, using keyword match fallback: %s", exc)
            # Keyword fallback
            keywords_in_answer = sum(
                1 for word in correct_answer.lower().split()
                if len(word) > 4 and word in user_answer.lower()
            )
            total_keywords = max(len([w for w in correct_answer.lower().split() if len(w) > 4]), 1)
            score = min(int(keywords_in_answer / total_keywords * 100), 100)
            is_correct = score >= 60
            return is_correct, score, f"Model answer: {correct_answer}"

    def _parse_questions(self, raw_response: str) -> list[dict]:
        """Parse and validate JSON question array from LLM response."""
        # Strip markdown code blocks if present
        cleaned = raw_response.strip()
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
        cleaned = cleaned.strip()

        # Find JSON array in response
        array_match = re.search(r"\[.*\]", cleaned, re.DOTALL)
        if array_match:
            cleaned = array_match.group(0)

        try:
            questions = json.loads(cleaned)
            if not isinstance(questions, list):
                return []

            # Validate and normalize each question
            valid = []
            for q in questions:
                if not isinstance(q, dict):
                    continue
                if not q.get("question") or not q.get("correct_answer"):
                    continue
                q_type = q.get("type", "mcq")
                if q_type not in ("mcq", "match", "short_answer"):
                    q["type"] = "mcq"
                valid.append(q)

            return valid
        except json.JSONDecodeError as exc:
            logger.error("JSON parse error in test questions: %s\nRaw: %s", exc, raw_response[:500])
            return []

    def _parse_grading(self, raw_response: str) -> dict:
        """Parse grading JSON from LLM response."""
        cleaned = raw_response.strip()
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)

        obj_match = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if obj_match:
            cleaned = obj_match.group(0)

        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            return {"is_correct": False, "score": 0, "explanation": "Grading failed."}


# Singleton
_test_generator_instance: Optional[TestGenerator] = None


def get_test_generator() -> TestGenerator:
    global _test_generator_instance
    if _test_generator_instance is None:
        _test_generator_instance = TestGenerator()
    return _test_generator_instance
