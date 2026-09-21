from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from app.models.ai import AiQueryInterpretation


class ButtonInfo(BaseModel):
    text: str = Field(..., description="Button display label text")
    type: str = Field("callback", description="Button type: 'callback', 'url', 'switch_inline', or 'other'")
    callback_data: Optional[str] = Field(None, description="Decoded callback payload for inline callback buttons")
    url: Optional[str] = Field(None, description="Target URL for inline URL buttons")
    browser_playable: bool = Field(False, description="Whether button corresponds to browser-compatible media")
    container: Optional[str] = Field(None, description="Container format if detected from button text")
    playback_mode: Optional[str] = Field("external", description="Playback mode: 'browser' or 'external'")


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
    browser_playable: bool = Field(False, description="Whether container is natively playable in HTML5 video")
    container: Optional[str] = Field(None, description="Normalized media container format (e.g. mp4, mkv, webm)")
    playback_mode: Optional[str] = Field("external", description="Playback mode: 'browser', 'external', or 'remux'")
    compatibility_reason: Optional[str] = Field(None, description="Explanation of compatibility evaluation")


class SearchCandidate(BaseModel):
    candidate_id: str = Field(..., description="Unique deterministic identifier for candidate")
    source_bot: str = Field(..., description="Telegram bot username providing the media")
    source_message_id: int = Field(..., description="Telegram message ID containing candidate button")
    start_payload: Optional[str] = Field(None, description="Deep link start payload for /start command")
    callback_data: Optional[str] = Field(None, description="Inline button callback data if callback query")
    display_text: str = Field(..., description="Original button text")
    title: str = Field(..., description="Parsed or cleaned movie/series title")
    size: Optional[str] = Field(None, description="Human readable size (e.g. 200.25 MB)")
    size_bytes: Optional[int] = Field(None, description="Estimated or parsed size in bytes")
    quality: Optional[str] = Field(None, description="Extracted quality/resolution (1080P, 720P, 4K)")
    language: Optional[str] = Field(None, description="Detected audio languages")
    extension: Optional[str] = Field(None, description="Detected container extension (mp4, mkv, webm)")
    browser_playable: bool = Field(False, description="Whether container is directly playable in browser")
    container: Optional[str] = Field(None, description="Normalized media container format")
    playback_mode: str = Field("external", description="Playback mode: 'browser' or 'external'")
    compatibility_reason: Optional[str] = Field(None, description="Explanation of compatibility evaluation")
    page_number: int = Field(1, description="Page number where candidate was discovered")


class SearchPaginationInfo(BaseModel):
    current_page: int = Field(1, description="Current page number (1-indexed)")
    total_pages: int = Field(1, description="Total pages reported by bot")
    total_results: int = Field(0, description="Total results reported by bot")
    has_next: bool = Field(False, description="Whether another page is available")
    has_prev: bool = Field(False, description="Whether previous page is available")
    next_callback_data: Optional[str] = Field(None, description="Callback payload to fetch next page")
    prev_callback_data: Optional[str] = Field(None, description="Callback payload to fetch previous page")
    source_message_id: Optional[int] = Field(None, description="Telegram message ID of the search response containing buttons")


class SearchResponse(BaseModel):
    query: str = Field(..., description="Search query string")
    results: List[SearchResultItem] = Field(default_factory=list, description="List of search result items (legacy/compatibility)")
    candidates: List[SearchCandidate] = Field(default_factory=list, description="Aggregated and ranked media candidates")
    pagination: Optional[SearchPaginationInfo] = Field(None, description="Pagination metadata")
    title_groups: Dict[str, List[SearchCandidate]] = Field(default_factory=dict, description="Candidates grouped by title")
    ai_interpretation: Optional["AiQueryInterpretation"] = Field(
        None, description="CineAI query interpretation and refinement details if applicable"
    )


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
