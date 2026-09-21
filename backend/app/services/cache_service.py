import asyncio
import logging
import re
from typing import Any, Dict, List, Optional

from app.config import settings
from app.models.ai import AiQueryInterpretation
from app.models.search import SearchCandidate
from app.services.compatibility import compatibility_service

logger = logging.getLogger("cineforge.cache")


def normalize_search_query(text: str) -> str:
    """Normalize query for consistent database indexing (lowercase, stripped, single spaced)."""
    cleaned = re.sub(r"[^\w\s]", " ", text.lower())
    return re.sub(r"\s+", " ", cleaned).strip()


class CacheService:
    """Zero-latency cache service backed by Supabase PostgreSQL."""

    def __init__(self):
        self._client = None
        self._initialized = False

    def is_ready(self) -> bool:
        """Check if Supabase caching is configured and enabled."""
        return bool(settings.SUPABASE_URL and settings.SUPABASE_KEY and settings.CACHE_ENABLED)

    def _get_client(self):
        if not self.is_ready():
            return None
        if self._client is not None:
            return self._client
        try:
            from supabase import create_client
            self._client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
            self._initialized = True
            logger.info("Connected to Supabase cache database.")
            return self._client
        except Exception as e:
            logger.warning("Failed to initialize Supabase client: %s. Continuing without cache.", str(e))
            return None

    async def get_cached_candidates(self, query: str) -> Optional[List[SearchCandidate]]:
        """Retrieve pre-resolved movie candidates from Supabase cache by normalized query or title."""
        client = self._get_client()
        if client is None:
            return None

        norm_query = normalize_search_query(query)
        if not norm_query:
            return None

        try:
            # Query by exact normalized query match or ilike canonical title
            res = (
                client.table("movies_cache")
                .select("*")
                .or_(f"query_normalized.eq.{norm_query},canonical_title.ilike.%{norm_query}%")
                .order("created_at", desc=True)
                .limit(40)
                .execute()
            )
            rows = res.data or []
            if not rows:
                return None

            candidates: List[SearchCandidate] = []
            for r in rows:
                container = r.get("container") or "mp4"
                browser_supported = container.lower() in compatibility_service.BROWSER_COMPATIBLE_CONTAINERS
                playback_mode = "browser" if browser_supported else "remux"

                cand = SearchCandidate(
                    candidate_id=r.get("candidate_id"),
                    source_bot=r.get("source_bot") or "Spoty_xbot",
                    source_message_id=r.get("source_message_id") or 0,
                    start_payload=r.get("start_payload"),
                    callback_data=r.get("callback_data"),
                    display_text=r.get("display_text") or r.get("canonical_title"),
                    title=r.get("canonical_title"),
                    size=r.get("size"),
                    size_bytes=r.get("size_bytes"),
                    quality=r.get("quality"),
                    language=r.get("language"),
                    extension=container,
                    browser_playable=browser_supported,
                    container=container,
                    playback_mode=playback_mode,
                    compatibility_reason="browser_supported" if browser_supported else "remux_supported",
                    page_number=1,
                )
                candidates.append(cand)

            logger.info("Cache HIT: Retrieved %d candidates from Supabase for '%s'", len(candidates), query)
            return candidates
        except Exception as e:
            logger.warning("Supabase cache read error for '%s': %s", query, str(e))
            return None

    async def save_candidates(
        self,
        query: str,
        candidates: List[SearchCandidate],
        canonical_title: Optional[str] = None,
    ) -> None:
        """Persist newly discovered Telegram candidates into Supabase movies_cache."""
        client = self._get_client()
        if client is None or not candidates:
            return

        norm_query = normalize_search_query(query)

        rows = []
        for c in candidates:
            title = canonical_title or c.title
            rows.append({
                "query_normalized": norm_query,
                "canonical_title": title,
                "candidate_id": c.candidate_id,
                "source_bot": c.source_bot,
                "source_message_id": c.source_message_id,
                "start_payload": c.start_payload,
                "callback_data": c.callback_data,
                "display_text": c.display_text,
                "quality": c.quality,
                "size": c.size,
                "size_bytes": c.size_bytes,
                "language": c.language,
                "container": c.container or c.extension,
            })

        try:
            # Upsert into movies_cache on unique candidate_id
            client.table("movies_cache").upsert(rows, on_conflict="candidate_id").execute()
            logger.info("Saved %d candidates to Supabase movies_cache for '%s'", len(rows), query)
        except Exception as e:
            logger.warning("Failed to save candidates to Supabase cache: %s", str(e))

    async def get_cached_ai_query(self, raw_query: str) -> Optional[AiQueryInterpretation]:
        """Check if CineAI already resolved this exact prompt/vague query."""
        client = self._get_client()
        if client is None:
            return None

        norm = normalize_search_query(raw_query)
        try:
            res = client.table("ai_query_cache").select("*").eq("raw_query", norm).limit(1).execute()
            rows = res.data or []
            if not rows:
                return None
            row = rows[0]
            logger.info("AI Query Cache HIT: '%s' -> '%s'", raw_query, row.get("canonical_title"))
            return AiQueryInterpretation(
                original_query=raw_query,
                is_refined=True,
                canonical_title=row.get("canonical_title"),
                year=row.get("year"),
                search_query=row.get("search_query"),
                confidence=float(row.get("confidence") or 1.0),
                explanation=row.get("explanation"),
                suggested_queries=[],
            )
        except Exception as e:
            logger.debug("AI query cache read error: %s", str(e))
            return None

    async def save_ai_query(self, raw_query: str, interpretation: AiQueryInterpretation) -> None:
        """Persist a CineAI resolution in ai_query_cache to avoid future LLM tokens."""
        client = self._get_client()
        if client is None or not interpretation.is_refined:
            return

        norm = normalize_search_query(raw_query)
        try:
            row = {
                "raw_query": norm,
                "canonical_title": interpretation.canonical_title or interpretation.search_query,
                "year": interpretation.year,
                "search_query": interpretation.search_query,
                "confidence": interpretation.confidence,
                "explanation": interpretation.explanation,
            }
            client.table("ai_query_cache").upsert([row], on_conflict="raw_query").execute()
            logger.info("Saved CineAI resolution to Supabase: '%s' -> '%s'", raw_query, interpretation.search_query)
        except Exception as e:
            logger.debug("Failed to save AI query resolution to Supabase: %s", str(e))

    async def save_stream_link(
        self,
        candidate_id: str,
        stream_url: str,
        watch_url: Optional[str] = None,
    ) -> None:
        """Save generated stream & player URLs in movies_cache for instant replay."""
        client = self._get_client()
        if client is None:
            return

        try:
            update_data = {"stream_url": stream_url}
            if watch_url:
                update_data["watch_url"] = watch_url

            client.table("movies_cache").update(update_data).eq("candidate_id", candidate_id).execute()
            logger.info("Updated stream URL in Supabase cache for candidate: %s", candidate_id)
        except Exception as e:
            logger.debug("Failed to update stream URL in cache: %s", str(e))

    async def get_stats(self) -> Dict[str, Any]:
        """Return cache health, status, and item counts."""
        client = self._get_client()
        if client is None:
            return {
                "status": "unconfigured",
                "cache_enabled": settings.CACHE_ENABLED,
                "cached_movies_count": 0,
                "cached_ai_queries_count": 0,
            }

        try:
            movies_count = client.table("movies_cache").select("id", count="exact").execute().count or 0
            ai_count = client.table("ai_query_cache").select("raw_query", count="exact").execute().count or 0
            return {
                "status": "ready",
                "cache_enabled": settings.CACHE_ENABLED,
                "cached_movies_count": movies_count,
                "cached_ai_queries_count": ai_count,
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "cache_enabled": settings.CACHE_ENABLED,
                "cached_movies_count": 0,
                "cached_ai_queries_count": 0,
            }


cache_service = CacheService()
