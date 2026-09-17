import asyncio
import hashlib
import logging
import re
import time
from typing import Any, Dict, List, Optional, Tuple

from app.config import settings
from app.models.delivery import parse_telegram_deep_link
from app.models.search import (
    SearchCandidate,
    SearchPaginationInfo,
    SearchResultItem,
)
from app.services.compatibility import compatibility_service

logger = logging.getLogger("cineforge.search_aggregator")


class SearchAggregatorService:
    """Aggregates paginated Telegram search candidate files, normalizes metadata,

    and discovers multi-format versions of titles without blindly crawling 220 pages.
    """

    def __init__(self):
        self.max_pages_default = getattr(settings, "SEARCH_MAX_PAGES", 2)
        self.max_candidates_default = getattr(settings, "SEARCH_MAX_CANDIDATES", 25)

    def extract_pagination_info(
        self,
        raw_text: str,
        buttons: List[Any],
    ) -> SearchPaginationInfo:
        """Extract pagination indicators (e.g. 'Page: 1/220', 'Total Results: 2200', '1/10', 'Next >')

        from message text and inline buttons.
        """
        current_page = 1
        total_pages = 1
        total_results = 0
        has_next = False
        has_prev = False
        next_callback_data: Optional[str] = None
        prev_callback_data: Optional[str] = None

        # 1. Parse text for "Page: X/Y" or "Total Results: Z"
        combined_text = raw_text or ""
        total_match = re.search(r"Total\s*Results\s*:\s*(\d+)", combined_text, re.IGNORECASE)
        if total_match:
            total_results = int(total_match.group(1))

        page_match = re.search(r"Page\s*:\s*(\d+)\s*/\s*(\d+)", combined_text, re.IGNORECASE)
        if page_match:
            current_page = int(page_match.group(1))
            total_pages = int(page_match.group(2))

        # 2. Inspect buttons for pagination bars (e.g., [<< Back] [1/10] [Next >>])
        for btn in buttons:
            btn_text = (getattr(btn, "text", "") or "").strip()
            raw_data = getattr(btn, "data", None)
            cb_data = None
            if raw_data is not None:
                cb_data = raw_data.decode("utf-8", errors="ignore") if isinstance(raw_data, bytes) else str(raw_data)

            # Detect page counter button (e.g. '1/8', '2/220', 'Page 1 of 10')
            btn_page_match = re.search(r"^(\d+)\s*/\s*(\d+)$", btn_text)
            if btn_page_match:
                current_page = int(btn_page_match.group(1))
                total_pages = int(btn_page_match.group(2))

            # Detect next button
            is_next = any(kw in btn_text.lower() for kw in (">", "next", "forward", ">>")) or (
                cb_data and "next" in cb_data.lower() and not ("back" in cb_data.lower() or "prev" in cb_data.lower())
            )
            if is_next and cb_data:
                has_next = True
                next_callback_data = cb_data

            # Detect back/prev button
            is_back = any(kw in btn_text.lower() for kw in ("<", "back", "prev", "<<")) or (
                cb_data and ("back" in cb_data.lower() or "prev" in cb_data.lower())
            )
            if is_back and cb_data:
                has_prev = True
                prev_callback_data = cb_data

        if total_results == 0 and total_pages > 1:
            total_results = total_pages * 10

        return SearchPaginationInfo(
            current_page=current_page,
            total_pages=max(1, total_pages),
            total_results=total_results,
            has_next=has_next,
            has_prev=has_prev,
            next_callback_data=next_callback_data,
            prev_callback_data=prev_callback_data,
        )

    def normalize_candidate(
        self,
        btn: Any,
        source_bot: str,
        source_message_id: int,
        page_number: int = 1,
    ) -> Optional[SearchCandidate]:
        """Convert a candidate button into a rich SearchCandidate model."""
        btn_text = getattr(btn, "text", "") or ""
        btn_url = getattr(btn, "url", None)
        raw_data = getattr(btn, "data", None)
        cb_data = None
        if raw_data is not None:
            cb_data = raw_data.decode("utf-8", errors="ignore") if isinstance(raw_data, bytes) else str(raw_data)

        # Ignore filter, navigation, and page counter buttons
        lower_txt = btn_text.lower()
        if any(ign in lower_txt for kw in ("next", "back", "prev", "page", "updates", "join", "language", "quality") if (ign := kw) in lower_txt):
            return None
        if re.search(r"^\d+\s*/\s*\d+$", btn_text.strip()):
            return None
        if cb_data and any(kw in cb_data.lower() for kw in ("languages#", "quality#", "buttons", "next_", "back_", "page_counter", "counter", "page_")):
            return None

        start_payload: Optional[str] = None
        target_bot = source_bot
        if btn_url:
            deep_link = parse_telegram_deep_link(btn_url)
            if deep_link:
                start_payload = deep_link.start_payload
                if deep_link.bot_username:
                    target_bot = deep_link.bot_username
            elif "t.me/+" in btn_url or "joinchat" in btn_url:
                # Invite link, not media candidate
                return None

        # Clean display text (strip leading icons/bullets)
        cleaned_text = re.sub(r"^[\s\U00010000-\U0010ffff\?•\-\[\]\(\)]+", "", btn_text).strip()

        # Extract size
        size: Optional[str] = None
        size_bytes: Optional[int] = None
        size_match = re.search(r"(\b\d+(?:\.\d+)?\s*(?:GB|MB|GiB|MiB|KB)\b)", btn_text, re.IGNORECASE)
        if size_match:
            size = size_match.group(1).strip()
            # Calculate approx bytes
            val_str, unit = size.split()
            val = float(val_str)
            if "gb" in unit.lower() or "gib" in unit.lower():
                size_bytes = int(val * 1024 * 1024 * 1024)
            elif "mb" in unit.lower() or "mib" in unit.lower():
                size_bytes = int(val * 1024 * 1024)
            elif "kb" in unit.lower():
                size_bytes = int(val * 1024)

        # Extract quality
        quality: Optional[str] = None
        qual_match = re.search(r"\b(4k|2160p|1080p|720p|480p|360p|hdrip|bluray|web-dl|webrip|dvdrip)\b", btn_text, re.IGNORECASE)
        if qual_match:
            quality = qual_match.group(1).upper()

        # Extract language
        language: Optional[str] = None
        lang_match = re.search(r"\b(Dual Audio|Multi Audio|Hindi|English|Tamil|Telugu|Malayalam|Kannada)\b", btn_text, re.IGNORECASE)
        if lang_match:
            language = lang_match.group(1)

        # Determine container extension
        ext_match = re.search(r"\b(mp4|mkv|webm|avi|mov|ts)\b", btn_text, re.IGNORECASE)
        extension = ext_match.group(1).lower() if ext_match else None

        # Extract or derive clean title
        # Remove size, quality, extension from text to get base title
        title_candidate = btn_text
        if size:
            title_candidate = title_candidate.replace(size, " ")
        if extension:
            title_candidate = re.sub(rf"\b{extension}\b", " ", title_candidate, flags=re.IGNORECASE)
        # Strip extraneous punctuation and multiple spaces
        title_candidate = re.sub(r"[•_–—\-\[\]\(\)]", " ", title_candidate)
        title_candidate = re.sub(r"\s+", " ", title_candidate).strip()
        title = title_candidate if len(title_candidate) > 2 else cleaned_text

        # Evaluate compatibility
        compat = compatibility_service.get_media_compatibility(
            filename=f"{title}.{extension}" if extension else title,
            text_hint=btn_text,
        )

        # Unique deterministic candidate ID
        raw_key = f"{target_bot}:{start_payload or cb_data or btn_text}"
        candidate_id = hashlib.sha256(raw_key.encode("utf-8")).hexdigest()[:16]

        return SearchCandidate(
            candidate_id=candidate_id,
            source_bot=target_bot,
            source_message_id=source_message_id,
            start_payload=start_payload,
            callback_data=cb_data,
            display_text=btn_text,
            title=title,
            size=size,
            size_bytes=size_bytes,
            quality=quality or "HD",
            language=language,
            extension=extension or compat.container,
            browser_playable=compat.browser_playable,
            container=compat.container,
            playback_mode=compat.playback_mode,
            compatibility_reason=compat.reason,
            page_number=page_number,
        )

    def parse_message_candidates(
        self,
        message: Any,
        source_bot: str,
        page_number: int = 1,
    ) -> Tuple[List[SearchCandidate], SearchPaginationInfo]:
        """Extract all candidate files and pagination metadata from a bot message."""
        flat_buttons: List[Any] = []
        if hasattr(message, "buttons") and message.buttons:
            for row in message.buttons:
                for b in row:
                    flat_buttons.append(b)

        pagination = self.extract_pagination_info(message.message or "", flat_buttons)
        pagination.current_page = page_number
        pagination.source_message_id = getattr(message, "id", None)

        candidates: List[SearchCandidate] = []
        for btn in flat_buttons:
            c = self.normalize_candidate(
                btn=btn,
                source_bot=source_bot,
                source_message_id=message.id,
                page_number=page_number,
            )
            if c:
                candidates.append(c)

        return candidates, pagination

    def deduplicate_candidates(
        self,
        candidates: List[SearchCandidate],
    ) -> List[SearchCandidate]:
        """Deduplicate candidates preserving first-seen high-quality entries."""
        seen = set()
        unique: List[SearchCandidate] = []
        for c in candidates:
            # Key combines start payload or normalized title + size + quality
            dedup_key = c.start_payload or f"{c.title.lower()}:{c.size}:{c.quality}:{c.container}"
            if dedup_key not in seen:
                seen.add(dedup_key)
                unique.append(c)
        return unique

    def group_candidates_by_title(
        self,
        candidates: List[SearchCandidate],
    ) -> Dict[str, List[SearchCandidate]]:
        """Cluster candidate versions under canonical title keys."""
        groups: Dict[str, List[SearchCandidate]] = {}
        for c in candidates:
            # Normalize title key by removing resolution/year variations
            norm_key = re.sub(r"\b(1080p|720p|480p|4k|2160p|hdrip|bluray|x264|x265)\b", "", c.title, flags=re.IGNORECASE)
            norm_key = re.sub(r"\s+", " ", norm_key).strip()
            if not norm_key:
                norm_key = c.title

            if norm_key not in groups:
                groups[norm_key] = []
            groups[norm_key].append(c)

        # Sort each title group using Phase 14 ranking rules
        for k in groups:
            groups[k] = self.rank_candidates(groups[k])

        return groups

    def rank_candidates(
        self,
        candidates: List[SearchCandidate],
    ) -> List[SearchCandidate]:
        """Rank candidates prioritizing browser compatibility, then quality, then size."""
        def sort_key(c: SearchCandidate):
            compat_score = 100 if c.browser_playable else 0
            # Quality score
            q = (c.quality or "").upper()
            if "2160P" in q or "4K" in q:
                q_score = 40
            elif "1080P" in q:
                q_score = 30
            elif "720P" in q:
                q_score = 20
            elif "480P" in q:
                q_score = 10
            else:
                q_score = 5

            # Size score (prefer sizes between 700MB and 3GB)
            s_bytes = c.size_bytes or 0
            size_score = 10 if (500 * 1024 * 1024 <= s_bytes <= 3 * 1024 * 1024 * 1024) else 0

            return (compat_score, q_score, size_score)

        return sorted(candidates, key=sort_key, reverse=True)


search_aggregator = SearchAggregatorService()
