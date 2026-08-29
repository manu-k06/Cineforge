from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ButtonInfo(BaseModel):
    text: str = Field(..., description="Button display label text")
    type: str = Field("callback", description="Button type: 'callback', 'url', 'switch_inline', or 'other'")
    callback_data: Optional[str] = Field(None, description="Decoded callback payload for inline callback buttons")
    url: Optional[str] = Field(None, description="Target URL for inline URL buttons")


class SearchResultItem(BaseModel):
    message_id: int = Field(..., description="Telegram message ID of the bot's response")
    text: str = Field(..., description="Original raw text content returned by the bot")
    title: Optional[str] = Field(None, description="Extracted movie title if detected")
    size: Optional[str] = Field(None, description="Extracted media file size string if detected")
    quality: Optional[str] = Field(None, description="Extracted quality (e.g. 1080p, 720p, 4K) if detected")
    language: Optional[str] = Field(None, description="Extracted language/audio information if detected")
    source_type: Optional[str] = Field(None, description="Source delivery type: 'telegram_deep_link', 'callback', 'url', or 'direct'")
    source_url: Optional[str] = Field(None, description="Delivery URL if deep link or web link")
    source_bot: Optional[str] = Field(None, description="Target delivery bot username if detected")
    start_payload: Optional[str] = Field(None, description="Deep link start payload if detected")
    buttons: List[ButtonInfo] = Field(default_factory=list, description="Extracted inline buttons")
    has_media: bool = Field(False, description="Whether the response includes attached media")
    media_type: Optional[str] = Field(None, description="Type of media if present")
    date: Optional[str] = Field(None, description="ISO timestamp of the response message")


class SearchResponse(BaseModel):
    query: str = Field(..., description="Search query string")
    results: List[SearchResultItem] = Field(default_factory=list, description="List of search result items")


class TelegramDebugSearchResponse(BaseModel):
    query: str = Field(..., description="The query sent to the bot")
    bot_username: str = Field(..., description="Target bot username")
    elapsed_seconds: float = Field(..., description="Time taken to receive the bot response")
    response_message_id: int = Field(..., description="Message ID of the response")
    response_text: str = Field(..., description="Raw text of the response")
    has_media: bool = Field(..., description="Whether response contains media")
    media_type: Optional[str] = Field(None, description="Detected media type")
    buttons_count: int = Field(..., description="Total count of extracted buttons")
    buttons: List[ButtonInfo] = Field(default_factory=list, description="Parsed button objects")
    raw_button_rows: Optional[List[List[Dict[str, Any]]]] = Field(
        None, description="Detailed layout breakdown of buttons per row"
    )
