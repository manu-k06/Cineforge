from typing import Optional
from fastapi import APIRouter, Query, Response, status

from app.models.subtitles import SubtitleTrackListResponse
from app.services.subtitle_service import subtitle_service

router = APIRouter()


@router.get("/tracks", response_model=SubtitleTrackListResponse, summary="Discover Subtitle Tracks for Movie")
async def get_subtitle_tracks(
    title: Optional[str] = Query(None, description="Movie or series title"),
    year: Optional[str] = Query(None, description="Optional release year"),
    imdb_id: Optional[str] = Query(None, description="Optional IMDb identifier (e.g. 'tt1375666')"),
    stream_url: Optional[str] = Query(None, description="Optional target media stream URL for compatibility"),
):
    """
    Search and return clean, multi-language subtitle tracks via API providers (OpenSubtitles & community).
    """
    parsed_year: Optional[int] = None
    if year:
        clean_y = str(year).strip()
        if clean_y.isdigit():
            parsed_year = int(clean_y)

    tracks = await subtitle_service.get_all_tracks(
        title=title,
        year=parsed_year,
        imdb_id=imdb_id,
        stream_url=stream_url,
    )
    return SubtitleTrackListResponse(
        title=title,
        year=parsed_year,
        imdb_id=imdb_id,
        stream_url=stream_url,
        tracks=tracks,
    )


@router.get("/vtt", summary="Stream Clean WebVTT Subtitle Track")
async def get_vtt_track(
    source: str = Query(..., description="Subtitle source provider: 'opensubtitles', 'yify', or 'demo'"),
    download_url: Optional[str] = Query(None, description="Subtitle download URL"),
    link: Optional[str] = Query(None, description="Community detail page link"),
    sub_id: Optional[str] = Query(None, description="Unique subtitle file ID"),
    title: Optional[str] = Query(None, description="Media title"),
    lang: Optional[str] = Query("en", description="Language code"),
):
    """
    Fetch subtitle payload from provider, convert to standard W3C WebVTT, and stream to client.
    """
    vtt_content = await subtitle_service.download_and_convert_vtt(
        source=source,
        download_url=download_url,
        link=link,
        sub_id=sub_id,
        title=title,
    )
    safe_filename = f"sub_{lang or 'track'}.vtt"
    return Response(
        content=vtt_content,
        media_type="text/vtt; charset=utf-8",
        headers={
            "Content-Type": "text/vtt; charset=utf-8",
            "Cache-Control": "public, max-age=86400",
            "Content-Disposition": f'inline; filename="{safe_filename}"',
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
