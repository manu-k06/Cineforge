import re
from typing import Any, Dict, List, Optional
from urllib.parse import parse_qs, urlparse
from pydantic import BaseModel, Field

from app.models.search import ButtonInfo


class DeepLinkInfo(BaseModel):
    bot_username: str = Field(..., description="Target bot username")
    start_payload: str = Field(..., description="Payload passed in ?start=")
    raw_url: str = Field(..., description="Original deep link URL")


class MediaMetadata(BaseModel):
    message_id: int = Field(..., description="Telegram message ID of the media message")
    chat_id: int = Field(..., description="ID of the chat from which the media arrived")
    date: Optional[str] = Field(None, description="ISO timestamp of the media message")
    media_type: str = Field(..., description="Type of media ('video', 'document', 'audio', 'photo', 'other')")
    file_name: Optional[str] = Field(None, description="Filename if available in document attributes")
    mime_type: Optional[str] = Field(None, description="MIME type of the media file")
    size: Optional[int] = Field(None, description="File size in bytes")
    duration: Optional[int] = Field(None, description="Video/Audio duration in seconds")
    width: Optional[int] = Field(None, description="Video/Image width in pixels")
    height: Optional[int] = Field(None, description="Video/Image height in pixels")


class SelectedResultRequest(BaseModel):
    type: str = Field(..., description="Selection type: 'callback', 'telegram_deep_link', or 'url'")
    message_id: Optional[int] = Field(None, description="Original search result message ID")
    callback_data: Optional[str] = Field(None, description="Callback payload if type is 'callback'")
    source_url: Optional[str] = Field(None, description="Target URL if type is 'telegram_deep_link' or 'url'")
    source_bot: Optional[str] = Field(None, description="Bot username if known")
    start_payload: Optional[str] = Field(None, description="Deep link start payload if pre-parsed")


class SelectedResultResponse(BaseModel):
    status: str = Field(..., description="Selection resolution status ('resolved', 'pending')")
    resolved_type: str = Field(..., description="Resolved selection type")
    target_bot: Optional[str] = Field(None, description="Target bot for the interaction")
    action_summary: str = Field(..., description="Human-readable description of the resolved selection")
    details: Dict[str, Any] = Field(default_factory=dict, description="Structured parameters for execution")


class TestMediaDetectionRequest(BaseModel):
    timeout: float = Field(60.0, ge=1.0, le=300.0, description="Max seconds to wait for incoming media")
    from_chat_id: Optional[int] = Field(None, description="Optional chat ID filter to listen for")


class TestMediaDetectionResponse(BaseModel):
    success: bool = Field(..., description="Whether a media message was captured")
    request_id: Optional[str] = Field(None, description="Unique identifier of the waiter")
    elapsed_seconds: Optional[float] = Field(None, description="Elapsed wait time in seconds")
    media: Optional[MediaMetadata] = Field(None, description="Captured media metadata")
    error: Optional[str] = Field(None, description="Error message if timed out or failed")


class TestDeliveryRequest(BaseModel):
    source_url: str = Field(..., description="Telegram deep link URL (e.g. https://t.me/Spoty_xbot?start=payload)")
    timeout: float = Field(30.0, ge=1.0, le=120.0, description="Timeout in seconds to wait for bot response/media")


class TestDeliveryResponse(BaseModel):
    success: bool = Field(..., description="Whether the delivery interaction was executed")
    request_id: str = Field(..., description="Unique tracking identifier for this delivery request")
    status: str = Field(..., description="Delivery status: 'media_received', 'action_required', 'timeout', or 'error'")
    media: Optional[MediaMetadata] = Field(None, description="Extracted media metadata if media arrived")
    message: Optional[str] = Field(None, description="Response text message from the bot if text/action is required")
    buttons: Optional[List[ButtonInfo]] = Field(None, description="Buttons returned by the bot if action is required")
    elapsed_seconds: Optional[float] = Field(None, description="Total execution time in seconds")
    error: Optional[str] = Field(None, description="Error description if status is error or timeout")


def parse_telegram_deep_link(url: str) -> Optional[DeepLinkInfo]:
    """Parse Telegram deep links like https://t.me/bot?start=payload or tg://resolve?domain=bot&start=payload."""
    if not url:
        return None

    parsed = urlparse(url.strip())
    bot_username = ""
    start_payload = ""

    if parsed.scheme in ("http", "https"):
        netloc = parsed.netloc.lower()
        if netloc in ("t.me", "telegram.me"):
            path_parts = parsed.path.strip("/").split("/")
            if path_parts and path_parts[0]:
                bot_username = path_parts[0].lstrip("@")
            query_params = parse_qs(parsed.query)
            if "start" in query_params:
                start_payload = query_params["start"][0]
    elif parsed.scheme == "tg":
        if parsed.netloc.lower() == "resolve":
            query_params = parse_qs(parsed.query)
            if "domain" in query_params:
                bot_username = query_params["domain"][0].lstrip("@")
            if "start" in query_params:
                start_payload = query_params["start"][0]

    if bot_username and start_payload:
        return DeepLinkInfo(
            bot_username=bot_username,
            start_payload=start_payload,
            raw_url=url,
        )

    return None
