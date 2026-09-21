import json
import logging
import re
from typing import Any, Dict, List, Optional

import httpx

from app.config import settings
from app.models.ai import (
    AiCompanionAskResponse,
    AiQueryInterpretation,
    AiRecommendationItem,
    AiRecommendationResponse,
)

logger = logging.getLogger("cineforge.ai")


class AiService:
    """CineAI service utilizing Google Gemini for query refinement,

    thematic recommendations, and movie companion lore.
    """

    def __init__(self):
        self.api_url = "https://generativelanguage.googleapis.com/v1beta/models"

    def _is_api_ready(self) -> bool:
        return bool(settings.GEMINI_API_KEY and settings.AI_SEARCH_ENABLED)

    def _should_bypass_ai(self, query: str) -> bool:
        """Heuristic check to bypass LLM for queries that are clearly exact titles

        to maintain sub-10ms latency when AI refinement is unnecessary.
        """
        trimmed = query.strip()
        # Empty or very short
        if not trimmed:
            return True

        # Words indicator
        words = trimmed.split()
        lower = trimmed.lower()

        # Complex / descriptive query triggers: question words, plot descriptions, etc.
        triggers = [
            "movie", "film", "show", "series", "where", "with", "about",
            "actor", "actress", "ending", "scene", "character", "recommend",
            "like", "similar", "director", "directed", "who", "what"
        ]
        if any(t in lower for t in triggers):
            return False

        # If it has more than 3 words, it is likely a phrase or description
        if len(words) > 3:
            return False

        # If it's 1-3 words and contains a 4-digit year e.g. "Inception 2010", it's already specific
        if len(words) <= 3 and re.search(r"\b(19\d\d|20\d\d)\b", trimmed):
            return True

        # If it's a short 1-2 word query with no numbers or weird characters,
        # we can still refine it if it might be a typo, but bypass if very standard.
        return False

    async def refine_movie_query(self, query: str) -> AiQueryInterpretation:
        """Interpret, correct typos, and resolve natural language/vague descriptions

        into canonical movie titles and optimized search queries.
        """
        cleaned_query = query.strip()
        fallback = AiQueryInterpretation(
            original_query=cleaned_query,
            is_refined=False,
            canonical_title=cleaned_query,
            year=None,
            search_query=cleaned_query,
            confidence=1.0,
            explanation=None,
            suggested_queries=[],
        )

        if not self._is_api_ready():
            return fallback

        if self._should_bypass_ai(cleaned_query):
            logger.debug("Bypassing AI query refinement for clean query: %s", cleaned_query)
            return fallback

        system_prompt = (
            "You are CineAI, an expert movie and television search query interpreter.\n"
            "Your task is to analyze the user's raw query and determine if it is:\n"
            "1. A vague plot description (e.g. 'movie where cooper travels into a wormhole' -> Interstellar)\n"
            "2. An actor/scene description (e.g. 'dicaprio spinning top dream' -> Inception)\n"
            "3. A misspelled title (e.g. 'shawshank redemtion' -> The Shawshank Redemption)\n"
            "4. Or already an exact, correctly spelled title.\n\n"
            "Rules:\n"
            "- If it's already a clean, correctly spelled title, set is_refined: false.\n"
            "- If it's a plot description, scene recall, or typo, set is_refined: true and resolve to canonical_title & release year.\n"
            "- 'search_query' should be the clean canonical title plus release year (e.g. 'Interstellar 2014') for optimal database/Telegram bot matching.\n"
            "- Provide confidence between 0.0 and 1.0.\n"
            "- Return ONLY a JSON object matching this exact schema:\n"
            "{\n"
            '  "is_refined": boolean,\n'
            '  "canonical_title": string or null,\n'
            '  "year": string or null,\n'
            '  "search_query": string,\n'
            '  "confidence": float,\n'
            '  "explanation": string or null,\n'
            '  "suggested_queries": [string]\n'
            "}"
        )

        model = settings.GEMINI_MODEL
        endpoint = f"{self.api_url}/{model}:generateContent?key={settings.GEMINI_API_KEY}"

        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": f"{system_prompt}\n\nUser search query: \"{cleaned_query}\""}
                    ]
                }
            ],
            "generationConfig": {
                "response_mime_type": "application/json",
                "temperature": 0.1,
            },
        }

        try:
            async with httpx.AsyncClient(timeout=settings.AI_REQUEST_TIMEOUT) as client:
                response = await client.post(endpoint, json=payload)
                if response.status_code != 200:
                    logger.warning("Gemini API error (%d): %s", response.status_code, response.text[:200])
                    return fallback

                data = response.json()
                candidates = data.get("candidates", [])
                if not candidates:
                    return fallback

                content_parts = candidates[0].get("content", {}).get("parts", [])
                if not content_parts:
                    return fallback

                raw_json = content_parts[0].get("text", "{}")
                parsed = json.loads(raw_json)

                canonical = parsed.get("canonical_title") or cleaned_query
                year = str(parsed.get("year")) if parsed.get("year") else None
                search_query = parsed.get("search_query") or (f"{canonical} {year}".strip() if year else canonical)

                return AiQueryInterpretation(
                    original_query=cleaned_query,
                    is_refined=bool(parsed.get("is_refined", False)),
                    canonical_title=canonical,
                    year=year,
                    search_query=search_query,
                    confidence=float(parsed.get("confidence", 0.9)),
                    explanation=parsed.get("explanation"),
                    suggested_queries=parsed.get("suggested_queries", []),
                )

        except Exception as e:
            logger.warning("Failed to refine query with CineAI: %s. Falling back to original query.", str(e))
            return fallback

    async def recommend_movies(self, prompt: str, count: int = 5) -> AiRecommendationResponse:
        """Produce curated movie/series recommendations matching a mood, theme, or prompt."""
        if not self._is_api_ready():
            return AiRecommendationResponse(prompt=prompt, recommendations=[])

        system_prompt = (
            "You are CineAI, an expert film and television curator.\n"
            f"The user wants up to {count} recommendations matching their request.\n"
            "Return ONLY a JSON object matching this schema:\n"
            "{\n"
            '  "recommendations": [\n'
            "    {\n"
            '      "title": string,\n'
            '      "year": string,\n'
            '      "reason": string,\n'
            '      "search_query": string (title + year)\n'
            "    }\n"
            "  ]\n"
            "}"
        )

        model = settings.GEMINI_MODEL
        endpoint = f"{self.api_url}/{model}:generateContent?key={settings.GEMINI_API_KEY}"

        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": f"{system_prompt}\n\nUser prompt: \"{prompt}\""}
                    ]
                }
            ],
            "generationConfig": {
                "response_mime_type": "application/json",
                "temperature": 0.4,
            },
        }

        try:
            async with httpx.AsyncClient(timeout=settings.AI_REQUEST_TIMEOUT + 2.0) as client:
                response = await client.post(endpoint, json=payload)
                if response.status_code != 200:
                    logger.warning("Gemini recommendation error (%d): %s", response.status_code, response.text[:200])
                    return AiRecommendationResponse(prompt=prompt, recommendations=[])

                data = response.json()
                raw_json = data["candidates"][0]["content"]["parts"][0]["text"]
                parsed = json.loads(raw_json)

                items = [
                    AiRecommendationItem(
                        title=r.get("title", ""),
                        year=str(r.get("year", "")),
                        reason=r.get("reason", ""),
                        search_query=r.get("search_query", f"{r.get('title')} {r.get('year', '')}".strip()),
                    )
                    for r in parsed.get("recommendations", [])
                    if r.get("title")
                ]
                return AiRecommendationResponse(prompt=prompt, recommendations=items)
        except Exception as e:
            logger.warning("Failed to generate recommendations with CineAI: %s", str(e))
            return AiRecommendationResponse(prompt=prompt, recommendations=[])

    async def ask_companion(self, movie_title: str, question: str) -> AiCompanionAskResponse:
        """Answer lore, plot breakdown, trivia, or cast questions about a specific movie/show."""
        if not self._is_api_ready():
            return AiCompanionAskResponse(
                movie_title=movie_title,
                question=question,
                answer="CineAI is currently not configured with an API key. Please configure GEMINI_API_KEY in .env.",
            )

        system_prompt = (
            "You are CineAI, an engaging and knowledgeable cinema companion.\n"
            f"The user is watching or discussing the film/show '{movie_title}'.\n"
            "Provide a concise, entertaining, and informative answer to their question.\n"
            "IMPORTANT: Avoid accidental spoilers for major twists or endings unless explicitly requested.\n"
        )

        model = settings.GEMINI_MODEL
        endpoint = f"{self.api_url}/{model}:generateContent?key={settings.GEMINI_API_KEY}"

        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": f"{system_prompt}\n\nQuestion: \"{question}\""}
                    ]
                }
            ],
            "generationConfig": {
                "temperature": 0.5,
                "maxOutputTokens": 400,
            },
        }

        try:
            async with httpx.AsyncClient(timeout=settings.AI_REQUEST_TIMEOUT + 2.0) as client:
                response = await client.post(endpoint, json=payload)
                if response.status_code != 200:
                    return AiCompanionAskResponse(
                        movie_title=movie_title,
                        question=question,
                        answer="Sorry, CineAI encountered a service issue. Please try again shortly.",
                    )

                data = response.json()
                answer_text = data["candidates"][0]["content"]["parts"][0]["text"].strip()
                return AiCompanionAskResponse(
                    movie_title=movie_title,
                    question=question,
                    answer=answer_text,
                )
        except Exception as e:
            logger.warning("CineAI companion ask error: %s", str(e))
            return AiCompanionAskResponse(
                movie_title=movie_title,
                question=question,
                answer="Sorry, CineAI could not answer at this moment. Please try again.",
            )


ai_service = AiService()
