import json
import logging
import re
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query, status
from fastapi.responses import HTMLResponse

from app.models.delivery import SelectedResultRequest, SelectedResultResponse
from app.models.delivery_flow import CandidateDeliveryRequest, CandidateDeliveryResponse
from app.models.search import (
    ButtonInfo,
    SearchCandidate,
    SearchPaginationInfo,
    SearchResponse,
    SearchResultItem,
)
from app.services.compatibility import compatibility_service
from app.services.search_aggregator import search_aggregator
from app.services.stream_session import session_manager
from app.services.telegram import telegram_service

logger = logging.getLogger("cineforge.api.search")
router = APIRouter()


@router.get("/search", response_model=SearchResponse, summary="Search Movies via Telegram Bot")
async def search_movies(
    q: Optional[str] = Query(None, description="Movie search query term"),
    query: Optional[str] = Query(None, description="Alias for 'q'"),
    page: int = Query(1, ge=1, description="Page number to inspect"),
    max_pages: int = Query(2, ge=1, le=10, description="Max pages to aggregate progressively"),
    callback_data: Optional[str] = Query(None, description="Callback data for next page navigation"),
    source_message_id: Optional[int] = Query(None, description="Search message ID containing pagination button"),
    mock: bool = Query(False, description="Simulate multi-file candidate list for compatibility testing"),
) -> SearchResponse:
    """Send a search query to the Telegram bot, aggregate candidates across pages,

    rank results by browser compatibility, and group by movie title.
    """
    search_term = (q or query or "").strip()
    if not search_term and not callback_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Query parameter 'q' or 'query' cannot be empty or only whitespace.",
        )
    query_str = search_term or "Search Results"

    # Mock mode for Phase 14/15 automated & manual verification
    if mock or query_str.lower() in ("mock", "test", "test_movie"):
        page_1_candidates = [
            SearchCandidate(
                candidate_id="mock_mp4_1080",
                source_bot="Spoty_xbot",
                source_message_id=9763,
                start_payload="mock_mp4_1080_payload",
                display_text="Movie (2025) 1080p Web-DL - x264 .mp4",
                title="Movie (2025)",
                size="2.1 GB",
                size_bytes=2254857830,
                quality="1080P",
                language="Malayalam",
                extension="mp4",
                browser_playable=True,
                container="mp4",
                playback_mode="browser",
                compatibility_reason="browser_supported",
                page_number=1,
            ),
            SearchCandidate(
                candidate_id="mock_mp4_720",
                source_bot="Spoty_xbot",
                source_message_id=9763,
                start_payload="mock_mp4_720_payload",
                display_text="Movie (2025) 720p Web - x264 .mp4",
                title="Movie (2025)",
                size="1.1 GB",
                size_bytes=1181116006,
                quality="720P",
                language="Malayalam",
                extension="mp4",
                browser_playable=True,
                container="mp4",
                playback_mode="browser",
                compatibility_reason="browser_supported",
                page_number=1,
            ),
            SearchCandidate(
                candidate_id="mock_mkv_1080",
                source_bot="Spoty_xbot",
                source_message_id=9763,
                start_payload="mock_mkv_1080_payload",
                display_text="Movie (2025) 1080p HQ HDRip - x264 .mkv",
                title="Movie (2025)",
                size="1.8 GB",
                size_bytes=1932735283,
                quality="1080P",
                language="Malayalam",
                extension="mkv",
                browser_playable=False,
                container="mkv",
                playback_mode="external",
                compatibility_reason="container_not_supported",
                page_number=1,
            ),
            SearchCandidate(
                candidate_id="mock_mkv_720",
                source_bot="Spoty_xbot",
                source_message_id=9763,
                start_payload="mock_mkv_720_payload",
                display_text="Movie (2025) 720p HQ HDRip - x264 .mkv",
                title="Movie (2025)",
                size="900 MB",
                size_bytes=943718400,
                quality="720P",
                language="Malayalam",
                extension="mkv",
                browser_playable=False,
                container="mkv",
                playback_mode="external",
                compatibility_reason="container_not_supported",
                page_number=1,
            ),
        ]

        page_2_candidates = [
            SearchCandidate(
                candidate_id="mock_mp4_4k",
                source_bot="Spoty_xbot",
                source_message_id=9763,
                start_payload="mock_mp4_4k_payload",
                display_text="Movie (2025) 2160p 4K UHD - x265 .mp4",
                title="Movie (2025)",
                size="4.2 GB",
                size_bytes=4509715660,
                quality="4K",
                language="Malayalam",
                extension="mp4",
                browser_playable=True,
                container="mp4",
                playback_mode="browser",
                compatibility_reason="browser_supported",
                page_number=2,
            ),
            SearchCandidate(
                candidate_id="mock_mp4_480",
                source_bot="Spoty_xbot",
                source_message_id=9763,
                start_payload="mock_mp4_480_payload",
                display_text="Movie (2025) 480p Web - x264 .mp4",
                title="Movie (2025)",
                size="450 MB",
                size_bytes=471859200,
                quality="480P",
                language="Malayalam",
                extension="mp4",
                browser_playable=True,
                container="mp4",
                playback_mode="browser",
                compatibility_reason="browser_supported",
                page_number=2,
            ),
            SearchCandidate(
                candidate_id="mock_mkv_4k",
                source_bot="Spoty_xbot",
                source_message_id=9763,
                start_payload="mock_mkv_4k_payload",
                display_text="Movie (2025) 4K UHD Remux - HEVC .mkv",
                title="Movie (2025)",
                size="6.8 GB",
                size_bytes=7301444403,
                quality="4K",
                language="Malayalam",
                extension="mkv",
                browser_playable=False,
                container="mkv",
                playback_mode="external",
                compatibility_reason="container_not_supported",
                page_number=2,
            ),
        ]

        # If requesting page 2 specifically via callback/page=2
        if page >= 2 or callback_data:
            mock_candidates = page_2_candidates
            cur_page = page if page > 1 else 2
        else:
            mock_candidates = page_1_candidates
            cur_page = 1

        legacy_results = [
            SearchResultItem(
                message_id=c.source_message_id,
                text=c.display_text,
                title=f"{c.title}.{c.extension}",
                size=c.size,
                quality=c.quality,
                language=c.language,
                has_media=True,
                media_type=f"video/{c.container}",
                browser_playable=c.browser_playable,
                container=c.container,
                playback_mode=c.playback_mode,
                compatibility_reason=c.compatibility_reason,
            )
            for c in mock_candidates
        ]

        pagination = SearchPaginationInfo(
            current_page=cur_page,
            total_pages=220,
            total_results=2200,
            has_next=True,
            has_prev=cur_page > 1,
            next_callback_data=f"mock_next_page_{cur_page + 1}",
            source_message_id=9763,
        )
        title_groups = search_aggregator.group_candidates_by_title(mock_candidates)

        return SearchResponse(
            query=query_str,
            results=legacy_results,
            candidates=mock_candidates,
            pagination=pagination,
            title_groups=title_groups,
        )

    try:
        if callback_data and source_message_id:
            data = await telegram_service.load_next_search_page(
                source_message_id=source_message_id,
                callback_data=callback_data,
                page_number=page,
                pages_to_fetch=1,
            )
        else:
            data = await telegram_service.search_bot_paginated(
                query=query_str,
                max_pages=max_pages,
            )

        candidates = data.get("candidates", [])
        # Build legacy results representation if needed
        legacy_results = [
            SearchResultItem(
                message_id=c.source_message_id,
                text=c.display_text,
                title=f"{c.title}.{c.extension}" if c.extension else c.title,
                size=c.size,
                quality=c.quality,
                language=c.language,
                has_media=False,
                browser_playable=c.browser_playable,
                container=c.container,
                playback_mode=c.playback_mode,
                compatibility_reason=c.compatibility_reason,
            )
            for c in candidates
        ]

        return SearchResponse(
            query=query_str,
            results=legacy_results,
            candidates=candidates,
            pagination=data.get("pagination"),
            title_groups=data.get("title_groups", {}),
        )
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
            detail=f"An error occurred while searching: {str(e)}",
        )


@router.get("/search/versions", response_model=SearchResponse, summary="Find All Versions for Selected Title")
async def find_title_versions(
    title: str = Query(..., min_length=1, description="Selected title to discover all versions for"),
    max_pages: int = Query(3, ge=1, le=5, description="Max focused pages to aggregate"),
) -> SearchResponse:
    """Targeted search refinement: discovers all versions (1080p, 720p, MP4, MKV) of a specific movie

    without crawling 220 general search pages.
    """
    try:
        data = await telegram_service.find_all_versions_for_title(
            title=title,
            max_pages=max_pages,
        )
        candidates = data.get("candidates", [])
        legacy_results = [
            SearchResultItem(
                message_id=c.source_message_id,
                text=c.display_text,
                title=f"{c.title}.{c.extension}" if c.extension else c.title,
                size=c.size,
                quality=c.quality,
                language=c.language,
                has_media=False,
                browser_playable=c.browser_playable,
                container=c.container,
                playback_mode=c.playback_mode,
            )
            for c in candidates
        ]
        return SearchResponse(
            query=title,
            results=legacy_results,
            candidates=candidates,
            pagination=data.get("pagination"),
            title_groups=data.get("title_groups", {}),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to discover versions for '{title}': {str(e)}",
        )


@router.post("/search/deliver", response_model=CandidateDeliveryResponse, summary="Trigger Candidate Delivery and Session Creation")
async def deliver_candidate_file(
    request: CandidateDeliveryRequest,
) -> CandidateDeliveryResponse:
    """Trigger bot delivery for a candidate button, forward document to 'me',

    verify actual media attributes, and create an active PlaybackSession.
    """
    # Mock delivery support for tests and offline validation
    if request.candidate_id.startswith("mock_") or request.source_bot == "mock_bot":
        is_mp4 = "mp4" in request.candidate_id.lower()
        mock_file_name = f"Movie (2025).{'mp4' if is_mp4 else 'mkv'}"
        mock_mime = "video/mp4" if is_mp4 else "video/x-matroska"
        session = await session_manager.create_playback_session(
            chat_id="me",
            message_id=9763,
            file_name=mock_file_name,
            mime_type=mock_mime,
            file_size=744246327,
        )
        return CandidateDeliveryResponse(
            success=True,
            delivered_chat_id="me",
            delivered_message_id=9763,
            file_name=mock_file_name,
            mime_type=mock_mime,
            file_size=744246327,
            browser_playable=is_mp4,
            container="mp4" if is_mp4 else "mkv",
            playback_mode="browser" if is_mp4 else "external",
            session_id=session.session_id,
            stream_url=session.stream_url,
            player_url=f"/api/media/session/{session.session_id}/player",
            elapsed_seconds=0.75,
        )

    try:
        return await telegram_service.deliver_candidate(request)
    except TimeoutError as e:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Candidate delivery failed: {str(e)}",
        )


@router.post(
    "/search/select",
    response_model=SelectedResultResponse,
    summary="Resolve and Validate a Selected Search Result",
)
async def select_search_result(
    request: SelectedResultRequest,
) -> SelectedResultResponse:
    """Validate and resolve a selected search result reference for upcoming delivery."""
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


@router.get(
    "/search/ui",
    response_class=HTMLResponse,
    summary="[Phase 15] Paginated Search, Multi-Format Grouping & Real Delivery UI",
)
async def get_search_ui():
    """Renders the CineForge Search, Multi-Format Discovery & Real Delivery UI."""
    html_content = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>CineForge — Movie Search & Browser Playback</title>
    <style>
        :root {
            --bg-primary: #0a0e17;
            --bg-card: rgba(18, 26, 43, 0.85);
            --border-card: rgba(255, 255, 255, 0.08);
            --accent-blue: #3b82f6;
            --accent-cyan: #06b6d4;
            --accent-green: #10b981;
            --accent-amber: #f59e0b;
            --accent-rose: #f43f5e;
            --text-main: #f8fafc;
            --text-muted: #94a3b8;
        }
        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
        }
        body {
            background: radial-gradient(circle at top right, #111827, #030712);
            color: var(--text-main);
            min-height: 100vh;
            padding: 32px 16px;
            display: flex;
            flex-direction: column;
            align-items: center;
        }
        .container {
            width: 100%;
            max-width: 960px;
        }
        header {
            text-align: center;
            margin-bottom: 28px;
        }
        .logo {
            font-size: 2.2rem;
            font-weight: 800;
            background: linear-gradient(135deg, #60a5fa, #34d399);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 8px;
        }
        .subtitle {
            color: var(--text-muted);
            font-size: 0.95rem;
        }
        .search-box-card {
            background: var(--bg-card);
            border: 1px solid var(--border-card);
            backdrop-filter: blur(12px);
            border-radius: 16px;
            padding: 24px;
            margin-bottom: 24px;
            box-shadow: 0 12px 30px rgba(0, 0, 0, 0.4);
        }
        .search-form {
            display: flex;
            gap: 12px;
        }
        .search-input {
            flex: 1;
            background: rgba(10, 14, 23, 0.75);
            border: 1px solid rgba(255, 255, 255, 0.12);
            border-radius: 10px;
            padding: 14px 18px;
            color: #fff;
            font-size: 1rem;
            outline: none;
            transition: border-color 0.2s;
        }
        .search-input:focus {
            border-color: var(--accent-blue);
        }
        .btn {
            background: linear-gradient(135deg, #2563eb, #1d4ed8);
            color: #fff;
            border: none;
            border-radius: 10px;
            padding: 14px 24px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s;
            display: inline-flex;
            align-items: center;
            gap: 8px;
        }
        .btn:hover {
            transform: translateY(-1px);
            box-shadow: 0 4px 14px rgba(37, 99, 235, 0.4);
        }
        .btn-play {
            background: linear-gradient(135deg, #059669, #10b981);
        }
        .btn-play:hover {
            box-shadow: 0 4px 14px rgba(16, 185, 129, 0.4);
        }
        .btn-vlc {
            background: rgba(245, 158, 11, 0.15);
            color: #fbbf24;
            border: 1px solid rgba(245, 158, 11, 0.3);
        }
        .btn-vlc:hover {
            background: rgba(245, 158, 11, 0.25);
            color: #fef3c7;
        }
        .btn-versions {
            background: rgba(59, 130, 246, 0.15);
            color: #93c5fd;
            border: 1px solid rgba(59, 130, 246, 0.3);
            font-size: 0.8rem;
            padding: 6px 12px;
            border-radius: 6px;
        }
        .btn-versions:hover {
            background: rgba(59, 130, 246, 0.25);
            color: #dbeafe;
        }
        .quick-tags {
            display: flex;
            gap: 10px;
            margin-top: 14px;
            flex-wrap: wrap;
            align-items: center;
        }
        .quick-tag {
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid rgba(255, 255, 255, 0.1);
            color: #cbd5e1;
            padding: 6px 12px;
            border-radius: 20px;
            font-size: 0.82rem;
            cursor: pointer;
            transition: all 0.2s;
        }
        .quick-tag:hover {
            background: rgba(255, 255, 255, 0.1);
            color: #fff;
        }
        .results-section {
            display: flex;
            flex-direction: column;
            gap: 16px;
            width: 100%;
        }
        .title-group-card {
            background: var(--bg-card);
            border: 1px solid var(--border-card);
            border-radius: 14px;
            padding: 18px 20px;
            margin-bottom: 12px;
        }
        .title-group-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 1px solid rgba(255, 255, 255, 0.06);
            padding-bottom: 12px;
            margin-bottom: 12px;
        }
        .group-title-text {
            font-size: 1.15rem;
            font-weight: 700;
            color: #f1f5f9;
        }
        .candidate-row {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 10px 14px;
            margin-bottom: 8px;
            border-radius: 8px;
            background: rgba(0, 0, 0, 0.25);
            border-left: 3px solid transparent;
            transition: all 0.15s;
        }
        .candidate-row.compatible {
            border-left-color: var(--accent-green);
        }
        .candidate-row.incompatible {
            border-left-color: var(--accent-amber);
        }
        .candidate-meta {
            display: flex;
            align-items: center;
            gap: 12px;
            flex-wrap: wrap;
        }
        .badge {
            font-size: 0.75rem;
            font-weight: 700;
            padding: 3px 8px;
            border-radius: 6px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        .badge-compat {
            background: rgba(16, 185, 129, 0.2);
            color: #34d399;
            border: 1px solid rgba(16, 185, 129, 0.3);
        }
        .badge-external {
            background: rgba(245, 158, 11, 0.15);
            color: #fbbf24;
            border: 1px solid rgba(245, 158, 11, 0.25);
        }
        .badge-quality {
            background: rgba(59, 130, 246, 0.2);
            color: #60a5fa;
        }
        .status-box {
            text-align: center;
            padding: 40px;
            color: var(--text-muted);
            font-size: 1.1rem;
        }
        .pagination-bar {
            display: flex;
            justify-content: center;
            align-items: center;
            gap: 16px;
            margin-top: 16px;
            padding: 16px;
        }
        /* Progress Delivery Modal */
        .modal-backdrop {
            display: none;
            position: fixed;
            top: 0; left: 0; right: 0; bottom: 0;
            background: rgba(0, 0, 0, 0.75);
            backdrop-filter: blur(8px);
            z-index: 9999;
            justify-content: center;
            align-items: center;
        }
        .modal-card {
            background: #111827;
            border: 1px solid rgba(255, 255, 255, 0.15);
            border-radius: 16px;
            padding: 32px;
            width: 90%;
            max-width: 440px;
            text-align: center;
            box-shadow: 0 20px 40px rgba(0, 0, 0, 0.6);
        }
        .modal-spinner {
            width: 44px;
            height: 44px;
            border: 4px solid rgba(255, 255, 255, 0.1);
            border-top-color: var(--accent-blue);
            border-radius: 50%;
            animation: spin 0.8s linear infinite;
            margin: 0 auto 18px;
        }
        @keyframes spin {
            to { transform: rotate(360deg); }
        }
        .modal-step {
            font-size: 0.95rem;
            color: var(--text-muted);
            margin-top: 8px;
        }
        .modal-step.active {
            color: #34d399;
            font-weight: 600;
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <div class="logo">🎬 CineForge Search</div>
            <div class="subtitle">Search Telegram movies, discover all format tiers, and stream via native Go engine</div>
        </header>

        <div class="search-box-card">
            <form class="search-form" id="search-form" onsubmit="handleSearch(event)">
                <input
                    id="search-input"
                    type="text"
                    class="search-input"
                    placeholder="Search movie title (e.g. Detective Ujjwalan, DC, Hotelier)..."
                    value="Movie"
                    required
                />
                <button type="submit" class="btn" id="btn-search">
                    🔍 Search
                </button>
            </form>
            <div class="quick-tags">
                <span style="font-size: 0.85rem; color: var(--text-muted);">Quick Test:</span>
                <button type="button" class="quick-tag" onclick="quickSearch('Movie', true)">🧪 Multi-Format Simulation</button>
                <button type="button" class="quick-tag" onclick="quickSearch('Detective Ujjwalan', false)">🎬 Real Bot: Detective Ujjwalan</button>
                <button type="button" class="quick-tag" onclick="quickSearch('DC', false)">⚡ Real Bot: DC</button>
            </div>
        </div>

        <div id="results-container" class="results-section">
            <div class="status-box">Enter a movie title or click a quick test button above.</div>
        </div>

        <div id="pagination-container" class="pagination-bar" style="display: none;"></div>
    </div>

    <!-- Delivery Progress Modal -->
    <div id="delivery-modal" class="modal-backdrop">
        <div class="modal-card">
            <div class="modal-spinner"></div>
            <h3 id="modal-title" style="margin-bottom: 12px;">Delivering Movie Document</h3>
            <div id="modal-step1" class="modal-step active">⏳ Step 1/3: Requesting file from Telegram bot...</div>
            <div id="modal-step2" class="modal-step">⏳ Step 2/3: Forwarding to Saved Messages & validating document...</div>
            <div id="modal-step3" class="modal-step">⏳ Step 3/3: Initializing /api/media/session & Go streamer...</div>
        </div>
    </div>

    <script>
        let allCandidates = [];
        let lastPagination = null;
        let currentSearchQuery = '';
        let currentMock = false;

        async function handleSearch(e) {
            if (e) e.preventDefault();
            const query = document.getElementById('search-input').value.trim();
            if (!query) return;
            await executeSearch(query, query.toLowerCase() === 'movie', 2, false);
        }

        async function quickSearch(query, mock) {
            document.getElementById('search-input').value = query;
            await executeSearch(query, mock, 2, false);
        }

        function deduplicateCandidates(list) {
            const seen = new Set();
            const unique = [];
            for (const c of list) {
                const key = c.start_payload || `${(c.title || '').toLowerCase()}:${c.size}:${c.quality}:${c.container}`;
                if (!seen.has(key)) {
                    seen.add(key);
                    unique.push(c);
                }
            }
            return unique;
        }

        function groupAndRankCandidates(candidates) {
            const groups = {};
            for (const c of candidates) {
                let normKey = (c.title || 'Unknown').replace(/\\b(1080p|720p|480p|4k|2160p|hdrip|bluray|x264|x265)\\b/gi, '').replace(/\\s+/g, ' ').trim();
                if (!normKey) normKey = c.title || 'Unknown';
                if (!groups[normKey]) groups[normKey] = [];
                groups[normKey].push(c);
            }
            // Sort each group: browser_playable first, then 4K > 1080p > 720p > 480p, then reasonable size
            for (const k of Object.keys(groups)) {
                groups[k].sort((a, b) => {
                    const compatA = a.browser_playable ? 100 : 0;
                    const compatB = b.browser_playable ? 100 : 0;
                    if (compatA !== compatB) return compatB - compatA;

                    const qScore = (q) => {
                        q = (q || '').toUpperCase();
                        if (q.includes('2160P') || q.includes('4K')) return 40;
                        if (q.includes('1080P')) return 30;
                        if (q.includes('720P')) return 20;
                        if (q.includes('480P')) return 10;
                        return 5;
                    };
                    const diff = qScore(b.quality) - qScore(a.quality);
                    if (diff !== 0) return diff;

                    return (b.size_bytes || 0) - (a.size_bytes || 0);
                });
            }
            return groups;
        }

        async function executeSearch(query, mock, maxPages, append = false) {
            currentSearchQuery = query;
            currentMock = mock;
            const container = document.getElementById('results-container');
            const pagContainer = document.getElementById('pagination-container');

            if (!append) {
                allCandidates = [];
                lastPagination = null;
                pagContainer.style.display = 'none';
                container.innerHTML = '<div class="status-box">Searching Telegram movies & aggregating format candidates...</div>';
            } else {
                pagContainer.innerHTML = '<span style="color: var(--text-muted);">Fetching next candidate page...</span>';
            }

            try {
                let url;
                if (append && lastPagination && lastPagination.next_callback_data && lastPagination.source_message_id) {
                    const nextPage = (lastPagination.current_page || 1) + 1;
                    url = `/api/search?q=${encodeURIComponent(query)}&callback_data=${encodeURIComponent(lastPagination.next_callback_data)}&source_message_id=${lastPagination.source_message_id}&page=${nextPage}${mock ? '&mock=true' : ''}`;
                } else {
                    url = `/api/search?q=${encodeURIComponent(query)}&max_pages=${maxPages}${mock ? '&mock=true' : ''}`;
                }

                const res = await fetch(url);
                if (!res.ok) {
                    const err = await res.json();
                    if (!append) {
                        container.innerHTML = `<div class="status-box" style="color: #fb7185;">Search Error: ${err.detail || 'Failed to fetch results'}</div>`;
                    } else {
                        alert('Load More Error: ' + (err.detail || 'Failed to fetch next page'));
                    }
                    return;
                }

                const data = await res.json();
                lastPagination = data.pagination || lastPagination;

                const incoming = data.candidates || [];
                allCandidates = deduplicateCandidates(allCandidates.concat(incoming));
                renderResults(allCandidates, lastPagination, query, mock);
            } catch (err) {
                if (!append) {
                    container.innerHTML = `<div class="status-box" style="color: #fb7185;">Network Error: ${err.message}</div>`;
                } else {
                    alert('Network Error: ' + err.message);
                }
            }
        }

        async function findTitleVersions(title) {
            const container = document.getElementById('results-container');
            container.innerHTML = `<div class="status-box">Discovering all versions for "${title}" without crawling 220 pages...</div>`;

            try {
                const url = `/api/search/versions?title=${encodeURIComponent(title)}&max_pages=3`;
                const res = await fetch(url);
                if (!res.ok) {
                    const err = await res.json();
                    container.innerHTML = `<div class="status-box" style="color: #fb7185;">Error: ${err.detail || 'Could not fetch versions'}</div>`;
                    return;
                }

                const data = await res.json();
                allCandidates = deduplicateCandidates(data.candidates || []);
                lastPagination = data.pagination;
                renderResults(allCandidates, lastPagination, title, false);
            } catch (err) {
                container.innerHTML = `<div class="status-box" style="color: #fb7185;">Network Error: ${err.message}</div>`;
            }
        }

        function renderResults(candidates, pagination, query, mock) {
            const container = document.getElementById('results-container');
            const pagContainer = document.getElementById('pagination-container');

            if (!candidates || candidates.length === 0) {
                container.innerHTML = `<div class="status-box">No candidate media files found for "${query}".</div>`;
                pagContainer.style.display = 'none';
                return;
            }

            container.innerHTML = '';
            const titleGroups = groupAndRankCandidates(candidates);

            // Render Title Groups
            for (const [titleName, groupCandidates] of Object.entries(titleGroups)) {
                const groupCard = document.createElement('div');
                groupCard.className = 'title-group-card';

                const groupHeader = document.createElement('div');
                groupHeader.className = 'title-group-header';
                groupHeader.innerHTML = `
                    <div class="group-title-text">📁 ${titleName} (${groupCandidates.length} version${groupCandidates.length > 1 ? 's' : ''})</div>
                    <button class="btn btn-versions" onclick="findTitleVersions('${titleName.replace(/'/g, "\\'")}')">
                        🔍 Find all versions
                    </button>
                `;
                groupCard.appendChild(groupHeader);

                groupCandidates.forEach(c => {
                    const row = document.createElement('div');
                    const isBrowser = c.browser_playable === true;
                    row.className = `candidate-row ${isBrowser ? 'compatible' : 'incompatible'}`;

                    const badge = isBrowser
                        ? `<span class="badge badge-compat">✨ Browser Playable (MP4)</span>`
                        : `<span class="badge badge-external">⚡ Auto fMP4 Remux (External Player)</span>`;

                    const actionBtn = `<button class="btn btn-play" onclick='deliverAndPlay(${JSON.stringify(c)})'>▶ Play</button>`;

                    row.innerHTML = `
                        <div class="candidate-meta">
                            ${badge}
                            <span class="badge badge-quality">${c.quality || 'HD'}</span>
                            <span style="font-weight: 600;">${(c.container || 'mkv').toUpperCase()}</span>
                            <span>${c.size || 'Unknown size'}</span>
                            ${c.language ? `<span style="color: var(--text-muted);">${c.language}</span>` : ''}
                        </div>
                        <div>${actionBtn}</div>
                    `;
                    groupCard.appendChild(row);
                });

                container.appendChild(groupCard);
            }

            // Pagination Controls: Show Page 1/220 and Load More
            if (pagination) {
                pagContainer.style.display = 'flex';
                const curP = pagination.current_page || 1;
                const totP = pagination.total_pages || 1;
                const totR = pagination.total_results || (totP * 10);
                const hasNext = pagination.has_next;

                pagContainer.innerHTML = `
                    <span style="color: var(--text-muted); font-size: 0.95rem; font-weight: 500;">
                        Page ${curP}/${totP} (${totR} total results) — ${candidates.length} candidates loaded
                    </span>
                    ${hasNext ? `
                        <button class="btn btn-versions" id="btn-load-more" onclick="loadMore()">
                            ⬇ Load More
                        </button>
                    ` : `
                        <span style="color: #34d399; font-size: 0.85rem; font-weight: 600;">✓ All Available Pages Loaded</span>
                    `}
                `;
            } else {
                pagContainer.style.display = 'none';
            }
        }

        async function loadMore() {
            const btn = document.getElementById('btn-load-more');
            if (btn) {
                btn.disabled = true;
                btn.textContent = '⏳ Loading...';
            }
            await executeSearch(currentSearchQuery, currentMock, 4, true);
        }

        async function deliverAndPlay(candidate) {
            showModal();
            updateModalStep(1, true);

            try {
                const reqBody = {
                    candidate_id: candidate.candidate_id,
                    source_bot: candidate.source_bot,
                    start_payload: candidate.start_payload,
                    callback_data: candidate.callback_data,
                    source_message_id: candidate.source_message_id
                };

                // Candidate delivery flow fetches document, forwards to 'me', and creates /api/media/session
                const res = await fetch('/api/search/deliver', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(reqBody)
                });

                updateModalStep(2, true);

                if (!res.ok) {
                    const err = await res.json();
                    hideModal();
                    alert('Delivery Failed: ' + (err.detail || 'Could not deliver document from Telegram'));
                    return;
                }

                const deliveryData = await res.json();
                updateModalStep(3, true);

                // Seamless automatic routing: navigate straight to player_url for both MP4 and MKV
                setTimeout(() => {
                    hideModal();
                    window.location.href = deliveryData.player_url;
                }, 400);

            } catch (err) {
                hideModal();
                alert('Delivery Error: ' + err.message);
            }
        }

        function showModal() {
            document.getElementById('delivery-modal').style.display = 'flex';
            document.getElementById('modal-step1').className = 'modal-step active';
            document.getElementById('modal-step2').className = 'modal-step';
            document.getElementById('modal-step3').className = 'modal-step';
        }

        function hideModal() {
            document.getElementById('delivery-modal').style.display = 'none';
        }

        function updateModalStep(step, active) {
            const el = document.getElementById(`modal-step${step}`);
            if (el) el.className = `modal-step ${active ? 'active' : ''}`;
        }

        // Auto-run mock simulation on initial load
        window.addEventListener('DOMContentLoaded', () => {
            quickSearch('Movie', true);
        });
    </script>
</body>
</html>
"""
    return HTMLResponse(content=html_content, status_code=200)
