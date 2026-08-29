from fastapi import APIRouter, HTTPException, Query, status

from app.models.delivery import SelectedResultRequest, SelectedResultResponse
from app.models.search import SearchResponse
from app.services.telegram import telegram_service

router = APIRouter()


@router.get("/search", response_model=SearchResponse, summary="Search Movies via Telegram Bot")
async def search_movies(
    q: str = Query(..., min_length=1, description="Movie search query term"),
) -> SearchResponse:
    """Send a search query to the configured Telegram bot, wait for its response, and return structured results with parsed inline buttons."""
    query_str = q.strip()
    if not query_str:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Query parameter 'q' cannot be empty or only whitespace.",
        )

    try:
        data = await telegram_service.search_bot(query=query_str)
        return SearchResponse(**data)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except RuntimeError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e),
        )
    except TimeoutError as e:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while interacting with the Telegram bot: {str(e)}",
        )


@router.post(
    "/search/select",
    response_model=SelectedResultResponse,
    summary="Resolve and Validate a Selected Search Result",
)
async def select_search_result(
    request: SelectedResultRequest,
) -> SelectedResultResponse:
    """Validate and resolve a selected search result reference (callback button or Telegram deep link) for upcoming delivery."""
    try:
        return telegram_service.select_result(request)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to resolve selected result: {str(e)}",
        )
