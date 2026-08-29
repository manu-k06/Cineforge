from typing import Dict

from fastapi import APIRouter, HTTPException, Query, status

from app.models.delivery import (
    TestDeliveryRequest,
    TestDeliveryResponse,
    TestMediaDetectionRequest,
    TestMediaDetectionResponse,
)
from app.models.search import TelegramDebugSearchResponse
from app.services.telegram import telegram_service

router = APIRouter()


@router.get("/status", summary="Check Telegram Connection Status")
async def get_telegram_status() -> Dict[str, bool]:
    """Check if the Telethon user client is connected and authenticated without exposing secrets."""
    return await telegram_service.get_status()


@router.get(
    "/test-search",
    response_model=TelegramDebugSearchResponse,
    summary="[Development] Test Bot Search and Inspect Response & Buttons",
)
async def test_telegram_search(
    q: str = Query(..., min_length=1, description="Movie search query term to send to the bot"),
) -> TelegramDebugSearchResponse:
    """Development-only endpoint: Sends query to bot in private chat and returns comprehensive metadata including raw button structure and latency."""
    query_str = q.strip()
    if not query_str:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Query parameter 'q' cannot be empty or only whitespace.",
        )

    try:
        data = await telegram_service.test_search_bot(query=query_str)
        return TelegramDebugSearchResponse(**data)
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
            detail=f"Error interacting with Telegram bot: {str(e)}",
        )


@router.post(
    "/test-media-detection",
    response_model=TestMediaDetectionResponse,
    summary="[Development] Test Waiting and Detecting Incoming Media Message",
)
async def test_media_detection(
    request: TestMediaDetectionRequest = TestMediaDetectionRequest(),
) -> TestMediaDetectionResponse:
    """Development-only endpoint: Registers an isolated waiter and waits for the next incoming private media message."""
    try:
        result = await telegram_service.wait_for_media(
            from_chat_id=request.from_chat_id,
            timeout=request.timeout,
        )
        return TestMediaDetectionResponse(**result)
    except RuntimeError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed during media detection test: {str(e)}",
        )


@router.post(
    "/test-delivery",
    response_model=TestDeliveryResponse,
    summary="[Development] Test Full Telegram Deep Link Delivery Flow",
)
async def test_delivery_flow(
    request: TestDeliveryRequest,
) -> TestDeliveryResponse:
    """Development-only endpoint: Initiates Telegram deep link interaction with target bot and captures media or action response."""
    try:
        result = await telegram_service.test_delivery(
            source_url=request.source_url,
            timeout=request.timeout,
        )
        return TestDeliveryResponse(**result)
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
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed during delivery test: {str(e)}",
        )
