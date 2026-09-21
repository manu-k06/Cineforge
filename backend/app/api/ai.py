from fastapi import APIRouter, Body, HTTPException, Query, status

from app.config import settings
from app.models.ai import (
    AiCompanionAskRequest,
    AiCompanionAskResponse,
    AiQueryInterpretation,
    AiRecommendationRequest,
    AiRecommendationResponse,
)
from app.services.ai_service import ai_service

router = APIRouter()


@router.get("/status", summary="Check CineAI Service Status")
async def get_ai_status():
    """Returns the operational status and model configured for CineAI."""
    return {
        "status": "ready" if ai_service._is_api_ready() else "unconfigured",
        "model": settings.GEMINI_MODEL,
        "ai_search_enabled": settings.AI_SEARCH_ENABLED,
        "has_api_key": bool(settings.GEMINI_API_KEY),
    }


@router.post("/refine", response_model=AiQueryInterpretation, summary="Refine and Normalize Search Query")
async def refine_query(
    query: str = Query(..., description="Raw search query or natural language plot description")
) -> AiQueryInterpretation:
    """Interprets vague descriptions, corrects typos, and outputs a canonical search query."""
    if not query.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Query cannot be empty.",
        )
    return await ai_service.refine_movie_query(query)


@router.post("/recommend", response_model=AiRecommendationResponse, summary="Get Thematic Movie Recommendations")
async def get_recommendations(request: AiRecommendationRequest) -> AiRecommendationResponse:
    """Generate movie or show recommendations matching a theme, mood, or natural prompt."""
    return await ai_service.recommend_movies(prompt=request.prompt, count=request.count)


@router.post("/ask", response_model=AiCompanionAskResponse, summary="Ask CineAI Movie Companion")
async def ask_companion(request: AiCompanionAskRequest) -> AiCompanionAskResponse:
    """Ask trivia, plot questions, or lore about a specific movie/show."""
    return await ai_service.ask_companion(movie_title=request.movie_title, question=request.question)
