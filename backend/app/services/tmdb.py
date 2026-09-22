import logging
import re
import time
from typing import Any, Dict, List, Optional, Tuple
import httpx

from app.config import settings
from app.models.metadata import CastMember, CrewMember, MovieMetadata, TrendingMoviesResponse

logger = logging.getLogger("cineforge.tmdb")


def sanitize_movie_query(raw_title: str) -> Tuple[str, Optional[int]]:
    """
    Extract a clean movie title and optional release year from messy release strings.
    Example: 'Inception.2010.1080p.BluRay.x264' -> ('Inception', 2010)
    """
    if not raw_title:
        return "", None

    # Replace dots, underscores with spaces
    text = re.sub(r"[._]", " ", raw_title).strip()

    # Search for a 4-digit year between 1900 and 2099
    year_match = re.search(r"\b(19\d\d|20\d\d)\b", text)
    year: Optional[int] = None
    if year_match:
        try:
            year = int(year_match.group(1))
            # Cut off everything after the year
            text = text[: year_match.start()].strip()
        except ValueError:
            pass

    # Strip quality/audio keywords if still lingering
    junk_pattern = r"(?i)\b(1080p|720p|480p|4k|uhd|bluray|web-dl|webrip|hdrip|x264|x265|hevc|aac|dts|remux|dual\s*audio|multi\s*sub)\b.*"
    clean_title = re.sub(junk_pattern, "", text).strip(" -:[]()")

    return clean_title or raw_title.strip(), year


class TmdbService:
    """Service for enriching movies with official TMDb posters, backdrops, cast, and ratings."""

    def __init__(self):
        self._cache: Dict[str, Tuple[float, MovieMetadata]] = {}
        self._trending_cache: Dict[str, Tuple[float, TrendingMoviesResponse]] = {}

    def is_configured(self) -> bool:
        """Check if TMDb API key or token is configured."""
        return bool(settings.TMDB_API_KEY and settings.TMDB_API_KEY.strip())

    def _get_auth_headers_and_params(self) -> Tuple[Dict[str, str], Dict[str, str]]:
        """Return headers and query parameters based on key type (Bearer JWT or API Key)."""
        key = (settings.TMDB_API_KEY or "").strip()
        headers = {"Accept": "application/json"}
        params: Dict[str, str] = {}

        if key.startswith("eyJ"):
            # JWT Bearer Read Access Token
            headers["Authorization"] = f"Bearer {key}"
        elif key:
            # Standard API Key
            params["api_key"] = key

        return headers, params

    def _format_image_url(self, path: Optional[str], size: str = "w500") -> Optional[str]:
        if not path:
            return None
        clean_path = path.lstrip("/")
        return f"{settings.TMDB_IMAGE_BASE_URL}/{size}/{clean_path}"

    def _create_fallback_metadata(self, title: str, year: Optional[int] = None) -> MovieMetadata:
        """Construct fallback metadata when TMDb is not configured or title is not found."""
        clean_title, parsed_year = sanitize_movie_query(title)
        effective_year = str(year or parsed_year or "")
        return MovieMetadata(
            tmdb_id=None,
            title=clean_title,
            original_title=clean_title,
            overview=f"Stream {clean_title} in high definition via Cineforge streaming pipeline.",
            year=effective_year or None,
            rating=None,
            vote_count=None,
            runtime=None,
            genres=[],
            poster_url=None,
            backdrop_url=None,
            trailer_key=None,
            directors=[],
            cast=[],
            source="fallback",
        )

    async def search_and_get_metadata(
        self,
        title: str,
        year: Optional[int] = None,
    ) -> MovieMetadata:
        """
        Search TMDb for movie metadata, fetch full details, credits, and videos.
        Returns cached or fallback metadata if unavailable.
        """
        clean_title, parsed_year = sanitize_movie_query(title)
        effective_year = year or parsed_year

        cache_key = f"{clean_title.lower()}:{effective_year or ''}"
        now = time.time()

        # Check in-memory cache
        if cache_key in self._cache:
            cached_time, cached_meta = self._cache[cache_key]
            if now - cached_time < settings.METADATA_CACHE_TTL:
                return cached_meta

        if not self.is_configured():
            fallback = self._create_fallback_metadata(clean_title, effective_year)
            self._cache[cache_key] = (now, fallback)
            return fallback

        headers, base_params = self._get_auth_headers_and_params()

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                # 1. Search for movie
                search_params = {**base_params, "query": clean_title, "include_adult": "false"}
                if effective_year:
                    search_params["year"] = str(effective_year)

                search_url = f"{settings.TMDB_BASE_URL}/search/movie"
                search_res = await client.get(search_url, headers=headers, params=search_params)

                results = []
                if search_res.status_code == 200:
                    data = search_res.json()
                    results = data.get("results", [])

                # Retry without year if zero results were found
                if not results and effective_year:
                    search_params.pop("year", None)
                    search_res = await client.get(search_url, headers=headers, params=search_params)
                    if search_res.status_code == 200:
                        results = search_res.json().get("results", [])

                if not results:
                    fallback = self._create_fallback_metadata(clean_title, effective_year)
                    self._cache[cache_key] = (now, fallback)
                    return fallback

                # Take top result
                top_movie = results[0]
                movie_id = top_movie.get("id")
                if not movie_id:
                    fallback = self._create_fallback_metadata(clean_title, effective_year)
                    self._cache[cache_key] = (now, fallback)
                    return fallback

                # 2. Fetch full details with credits & videos
                details_url = f"{settings.TMDB_BASE_URL}/movie/{movie_id}"
                details_params = {**base_params, "append_to_response": "credits,videos"}
                details_res = await client.get(details_url, headers=headers, params=details_params)

                if details_res.status_code != 200:
                    # Parse basic fields from search result if details call fails
                    meta = self._parse_movie_dict(top_movie, None)
                    self._cache[cache_key] = (now, meta)
                    return meta

                details_data = details_res.json()
                meta = self._parse_movie_dict(details_data, details_data)
                self._cache[cache_key] = (now, meta)
                return meta

        except Exception as e:
            logger.warning("Error fetching TMDb metadata for '%s': %s", clean_title, str(e))
            fallback = self._create_fallback_metadata(clean_title, effective_year)
            return fallback

    def _parse_movie_dict(
        self,
        data: Dict[str, Any],
        extended_data: Optional[Dict[str, Any]] = None,
    ) -> MovieMetadata:
        """Parse raw TMDb API responses into MovieMetadata."""
        tmdb_id = data.get("id")
        title = data.get("title") or data.get("name") or "Unknown"
        original_title = data.get("original_title")
        overview = data.get("overview")
        release_date = data.get("release_date")
        year = release_date[:4] if release_date and len(release_date) >= 4 else None

        vote_avg = data.get("vote_average")
        rating = round(float(vote_avg), 1) if vote_avg is not None and vote_avg > 0 else None
        vote_count = data.get("vote_count")
        runtime = data.get("runtime")

        # Genres
        genres = []
        raw_genres = data.get("genres", [])
        if raw_genres and isinstance(raw_genres, list):
            genres = [g.get("name") for g in raw_genres if isinstance(g, dict) and g.get("name")]

        # Images
        poster_path = data.get("poster_path")
        backdrop_path = data.get("backdrop_path")
        poster_url = self._format_image_url(poster_path, "w500")
        backdrop_url = self._format_image_url(backdrop_path, "w1280")

        # Cast & Directors & Videos from extended response
        directors: List[str] = []
        cast_list: List[CastMember] = []
        trailer_key: Optional[str] = None

        if extended_data:
            credits = extended_data.get("credits", {})
            raw_cast = credits.get("cast", [])
            for c in raw_cast[:10]:
                if isinstance(c, dict):
                    name = c.get("name")
                    if name:
                        profile_path = c.get("profile_path")
                        cast_list.append(
                            CastMember(
                                name=name,
                                character=c.get("character") or "",
                                profile_path=profile_path,
                                profile_url=self._format_image_url(profile_path, "w185"),
                            )
                        )

            raw_crew = credits.get("crew", [])
            for cr in raw_crew:
                if isinstance(cr, dict) and cr.get("job") == "Director":
                    d_name = cr.get("name")
                    if d_name and d_name not in directors:
                        directors.append(d_name)

            # Videos / Trailer
            videos = extended_data.get("videos", {}).get("results", [])
            for v in videos:
                if isinstance(v, dict) and v.get("site") == "YouTube":
                    if v.get("type") in ["Trailer", "Teaser"]:
                        trailer_key = v.get("key")
                        break

        return MovieMetadata(
            tmdb_id=tmdb_id,
            title=title,
            original_title=original_title,
            overview=overview,
            release_date=release_date,
            year=year,
            rating=rating,
            vote_count=vote_count,
            runtime=runtime,
            genres=genres,
            poster_url=poster_url,
            backdrop_url=backdrop_url,
            trailer_key=trailer_key,
            directors=directors,
            cast=cast_list,
            source="tmdb",
        )

    async def get_trending_movies(
        self,
        time_window: str = "week",
        page: int = 1,
    ) -> TrendingMoviesResponse:
        """Retrieve trending movies list for discovery carousel."""
        cache_key = f"{time_window}:{page}"
        now = time.time()

        if cache_key in self._trending_cache:
            cached_time, cached_trending = self._trending_cache[cache_key]
            if now - cached_time < 3600:  # 1 hour cache
                return cached_trending

        if not self.is_configured():
            # Return curated fallback list
            sample_titles = [
                ("Inception", 2010),
                ("Interstellar", 2014),
                ("Dune: Part Two", 2024),
                ("The Dark Knight", 2008),
                ("Avengers: Endgame", 2019),
            ]
            fallback_items = [self._create_fallback_metadata(t, y) for t, y in sample_titles]
            res = TrendingMoviesResponse(page=1, total_pages=1, results=fallback_items)
            return res

        headers, base_params = self._get_auth_headers_and_params()
        params = {**base_params, "page": str(page)}
        url = f"{settings.TMDB_BASE_URL}/trending/movie/{time_window}"

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(url, headers=headers, params=params)
                if resp.status_code == 200:
                    data = resp.json()
                    raw_results = data.get("results", [])
                    parsed = [self._parse_movie_dict(item) for item in raw_results]
                    response_obj = TrendingMoviesResponse(
                        page=data.get("page", 1),
                        total_pages=data.get("total_pages", 1),
                        results=parsed,
                    )
                    self._trending_cache[cache_key] = (now, response_obj)
                    return response_obj
        except Exception as e:
            logger.warning("Error fetching trending movies: %s", str(e))

        return TrendingMoviesResponse(page=1, total_pages=1, results=[])


tmdb_service = TmdbService()
