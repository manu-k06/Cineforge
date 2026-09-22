from typing import Optional
from fastapi import APIRouter, Query, Response, status

from app.models.subtitles import SubtitleTrackListResponse
from app.services.subtitle_service import subtitle_service

router = APIRouter()


@router.get("/tracks", response_model=SubtitleTrackListResponse, summary="Discover Subtitle Tracks for Media Stream")
async def get_subtitle_tracks(
    stream_url: str = Query(..., description="Target media streaming URL"),
    title: Optional[str] = Query(None, description="Movie or series title"),
    year: Optional[int] = Query(None, description="Optional release year"),
):
    """Detect and return all embedded and external WebVTT subtitle tracks for a media stream."""
    tracks = await subtitle_service.get_all_tracks(stream_url=stream_url, title=title, year=year)
    return SubtitleTrackListResponse(
        stream_url=stream_url,
        title=title,
        tracks=tracks,
    )


@router.get("/embedded", summary="Stream Extracted WebVTT Subtitle Track")
async def get_embedded_vtt(
    stream_url: str = Query(..., description="Media stream URL containing the subtitle track"),
    track_index: int = Query(0, ge=0, description="Embedded subtitle stream index"),
):
    """Extract embedded soft subtitles on-the-fly and return as standard WebVTT."""
    vtt_content = await subtitle_service.extract_embedded_vtt(stream_url=stream_url, track_index=track_index)
    return Response(
        content=vtt_content,
        media_type="text/vtt; charset=utf-8",
        headers={
            "Content-Type": "text/vtt; charset=utf-8",
            "Cache-Control": "public, max-age=86400",
            "Content-Disposition": f'inline; filename="track_{track_index}.vtt"',
        },
    )


@router.get("/demo.vtt", summary="Stream Demo WebVTT Track for Playback Testing")
async def get_demo_vtt(
    title: Optional[str] = Query("Movie", description="Title for caption display"),
):
    """Return synchronized test WebVTT captions."""
    demo_content = subtitle_service.generate_demo_vtt(title=title)
    return Response(
        content=demo_content,
        media_type="text/vtt; charset=utf-8",
        headers={
            "Content-Type": "text/vtt; charset=utf-8",
            "Cache-Control": "public, max-age=86400",
            "Content-Disposition": 'inline; filename="demo.vtt"',
        },
    )
