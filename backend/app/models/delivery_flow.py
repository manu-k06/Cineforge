from typing import Optional
from pydantic import BaseModel, Field


class CandidateDeliveryRequest(BaseModel):
    candidate_id: str = Field(..., description="Unique ID of the candidate to deliver")
    source_bot: str = Field(..., description="Target bot username to trigger delivery from")
    start_payload: Optional[str] = Field(None, description="Start payload if deep-link delivery")
    callback_data: Optional[str] = Field(None, description="Callback data if callback delivery")
    source_message_id: Optional[int] = Field(None, description="Original search message ID containing button")


class CandidateDeliveryResponse(BaseModel):
    success: bool = Field(..., description="Whether delivery and document resolution succeeded")
    delivered_chat_id: str = Field(..., description="Chat ID where document was received or canonicalized")
    delivered_message_id: int = Field(..., description="Message ID of the delivered Telegram Document")
    file_name: str = Field(..., description="Actual document filename extracted from MTProto attributes")
    mime_type: str = Field(..., description="Actual authoritative MIME type from MTProto")
    file_size: int = Field(..., description="Actual document file size in bytes")
    browser_playable: bool = Field(..., description="Whether actual document is browser-playable (MP4/WebM)")
    container: str = Field(..., description="Actual media container (e.g. mp4, mkv)")
    playback_mode: str = Field("browser", description="Playback mode: 'browser' or 'external'")
    session_id: str = Field(..., description="Active session ID or reference")
    stream_url: str = Field(..., description="Direct media streaming link from Streamer Bot")
    player_url: str = Field(..., description="Web player URL (Watch Online)")
    watch_url: Optional[str] = Field(None, description="Direct web player URL from Streamer Bot")
    download_url: Optional[str] = Field(None, description="Direct download link from Streamer Bot")
    elapsed_seconds: float = Field(..., description="Time taken to deliver and extract stream link")
    error: Optional[str] = Field(None, description="Error message if delivery failed")
