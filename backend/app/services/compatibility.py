import os
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class MediaCompatibilityResult:
    browser_playable: bool
    container: Optional[str]
    playback_mode: str  # "browser", "external", or "remux"
    reason: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "browser_playable": self.browser_playable,
            "container": self.container,
            "playback_mode": self.playback_mode,
            "reason": self.reason,
        }


class MediaCompatibilityService:
    """Centralized service to evaluate browser media compatibility and rank search results.

    Browser-preferred containers: MP4, WebM
    Browser-incompatible / external-player containers: MKV, AVI, FLV, WMV, TS, MPG, MPEG, MOV, etc.
    """

    # Browser natively demuxes these over HTML5 <video> / progressive HTTP
    BROWSER_COMPATIBLE_CONTAINERS = {"mp4", "webm", "m4v"}
    BROWSER_COMPATIBLE_MIMES = {
        "video/mp4",
        "video/webm",
        "video/x-m4v",
    }

    # External player preferred containers (cannot be natively demuxed by Chromium HTML5 <video>)
    EXTERNAL_CONTAINERS = {
        "mkv", "avi", "flv", "wmv", "ts", "m2ts", "mpeg", "mpg", "vob", "iso", "rmvb", "mov"
    }
    EXTERNAL_MIMES = {
        "video/x-matroska",
        "video/x-msvideo",
        "video/x-flv",
        "video/x-ms-wmv",
        "video/mp2t",
        "video/mpeg",
        "video/quicktime",
    }

    # Common quality priority ranks (higher score = better rank)
    QUALITY_RANKS = {
        "2160P": 400,
        "4K": 400,
        "1080P": 300,
        "720P": 200,
        "480P": 100,
        "HDRIP": 80,
        "WEBRIP": 75,
        "WEBDL": 75,
        "BLURAY": 70,
        "DVDRIP": 60,
        "CAMRIP": 10,
    }

    def detect_container_from_filename(self, filename: Optional[str]) -> Optional[str]:
        """Extracts container extension strictly from file suffix to prevent substring false-positives."""
        if not filename:
            return None

        clean_name = filename.strip()
        # Find file extension using os.path.splitext
        _, ext = os.path.splitext(clean_name)
        if ext:
            clean_ext = ext.lstrip(".").lower()
            if clean_ext in self.BROWSER_COMPATIBLE_CONTAINERS or clean_ext in self.EXTERNAL_CONTAINERS:
                return clean_ext

        # Regex fallback for names with trailing tags or dots (e.g. "movie - x264 .mkv")
        ext_match = re.search(r"\.([a-zA-Z0-9]{2,5})\s*$", clean_name)
        if ext_match:
            candidate = ext_match.group(1).lower()
            if candidate in self.BROWSER_COMPATIBLE_CONTAINERS or candidate in self.EXTERNAL_CONTAINERS:
                return candidate

        return None

    def detect_container_from_mime(self, mime_type: Optional[str]) -> Optional[str]:
        """Maps standard MIME types to normalized container names."""
        if not mime_type:
            return None

        clean_mime = mime_type.strip().lower()
        if "mp4" in clean_mime:
            return "mp4"
        if "webm" in clean_mime:
            return "webm"
        if "matroska" in clean_mime:
            return "mkv"
        if "msvideo" in clean_mime or "avi" in clean_mime:
            return "avi"
        if "quicktime" in clean_mime:
            return "mov"
        if "flv" in clean_mime:
            return "flv"
        if "wmv" in clean_mime:
            return "wmv"
        if "mp2t" in clean_mime:
            return "ts"
        if "mpeg" in clean_mime:
            return "mpg"

        return None

    def detect_container_from_text(self, text: Optional[str]) -> Optional[str]:
        """Detects container tokens in title or button text using bounded word boundaries."""
        if not text:
            return None

        # Look for explicit format tags like "[MP4]", ".mp4", "1080p MP4", "x264.mkv"
        for candidate in ["mp4", "webm", "mkv", "avi", "flv", "wmv", "ts"]:
            pattern = rf"(?:\b|\.|\_|\-){re.escape(candidate)}(?:\b|\.|\_|\-)"
            if re.search(pattern, text, re.IGNORECASE):
                return candidate.lower()

        return None

    def get_media_compatibility(
        self,
        filename: Optional[str] = None,
        mime_type: Optional[str] = None,
        text_hint: Optional[str] = None,
    ) -> MediaCompatibilityResult:
        """Determines whether a media file is natively browser-playable or requires an external player.

        Evaluation precedence:
        1. MIME type (if specific video MIME)
        2. Filename extension (strict suffix match)
        3. Text hint regex (word boundary)
        """
        # Step 1: MIME evaluation
        mime_container = self.detect_container_from_mime(mime_type)

        # Step 2: Strict filename extension
        file_container = self.detect_container_from_filename(filename)

        # Step 3: Text hint fallback
        text_container = self.detect_container_from_text(text_hint)

        # Priority resolution
        container = file_container or mime_container or text_container

        # Case A: Explicitly browser-compatible MIME
        if mime_type and mime_type.strip().lower() in self.BROWSER_COMPATIBLE_MIMES:
            return MediaCompatibilityResult(
                browser_playable=True,
                container=container or "mp4",
                playback_mode="browser",
                reason="browser_supported_mime",
            )

        # Case B: Incompatible MIME (e.g. video/x-matroska)
        if mime_type and mime_type.strip().lower() in self.EXTERNAL_MIMES:
            return MediaCompatibilityResult(
                browser_playable=False,
                container=container or "mkv",
                playback_mode="external",
                reason="container_not_supported",
            )

        # Case C: Container extension evaluation
        if container in self.BROWSER_COMPATIBLE_CONTAINERS:
            return MediaCompatibilityResult(
                browser_playable=True,
                container=container,
                playback_mode="browser",
                reason="browser_supported",
            )

        if container in self.EXTERNAL_CONTAINERS:
            return MediaCompatibilityResult(
                browser_playable=False,
                container=container,
                playback_mode="external",
                reason="container_not_supported",
            )

        # Case D: Unknown or unclassified
        return MediaCompatibilityResult(
            browser_playable=False,
            container=container or "unknown",
            playback_mode="external",
            reason="unknown_container",
        )

    def is_browser_playable(
        self,
        filename: Optional[str] = None,
        mime_type: Optional[str] = None,
        text_hint: Optional[str] = None,
    ) -> bool:
        """Convenience boolean check."""
        return self.get_media_compatibility(filename, mime_type, text_hint).browser_playable

    def rank_search_results(self, items: List[Any]) -> List[Any]:
        """Ranks a list of SearchResultItem objects.

        Prioritizes:
        1. Browser-compatible media first (MP4/WebM > MKV/AVI)
        2. Quality score (2160p/4K > 1080p > 720p > 480p)
        3. File size rationality (favors reasonable file sizes over empty or excessive sizes)
        """
        if not items:
            return []

        def sort_key(item: Any):
            # 1. Compatibility priority (1 for browser playable, 0 for external)
            is_playable = getattr(item, "browser_playable", False)
            compat_score = 1 if is_playable else 0

            # 2. Quality rank score
            quality_str = (getattr(item, "quality", "") or "").upper()
            quality_score = self.QUALITY_RANKS.get(quality_str, 50)

            # 3. Size score (parse size string like "1.8 GB" into approximate MB)
            size_mb = 0.0
            size_str = getattr(item, "size", "") or ""
            size_match = re.search(r"(\d+(?:\.\d+)?)\s*(GB|MB|GIB|MIB)", size_str, re.IGNORECASE)
            if size_match:
                val = float(size_match.group(1))
                unit = size_match.group(2).upper()
                size_mb = val * 1024.0 if "G" in unit else val

            # Normalize size score to favor files between 500 MB and 4000 MB (sweet spot for movies)
            size_score = min(size_mb / 1000.0, 5.0)

            # Return tuple for Python descending sort:
            # (compat_score, quality_score, size_score)
            return (compat_score, quality_score, size_score)

        return sorted(items, key=sort_key, reverse=True)


compatibility_service = MediaCompatibilityService()
