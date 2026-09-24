import datetime
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
    Example: '@KCFilmss - The Greatest of All Time 2024 Dual Audio 1080p.mkv' -> ('The Greatest of All Time', 2024)
    """
    if not raw_title:
        return "", None

    # Strip bracket size tags like [459.87 MB], [1.05 GB], etc.
    text = re.sub(r"\[\s*[\d\.]+\s*(?:MB|GB|GiB|MiB)\s*\]", "", raw_title, flags=re.IGNORECASE)
    # Strip file extensions
    text = re.sub(r"\.(?:mkv|mp4|avi|webm|mov)$", "", text, flags=re.IGNORECASE)
    # Strip word extensions (e.g. ' mp4' or ' mkv')
    text = re.sub(r"(?i)\b(?:mkv|mp4|avi|webm|mov)\b", "", text)
    # Split merged year and resolution like 2019720p -> 2019 720p
    text = re.sub(r"(\d{4})(?=\d{3,4}p)", r"\1 ", text)
    # Strip Telegram channels/handles
    text = re.sub(r"@[\w\d_]+", "", text)
    # Strip common pirate site watermarks
    text = re.sub(
        r"(?i)\b\d*(?:tamilmv|tamilblasters|cinemavilla|moviesda|filmywap|cineforge|spoty_xbot)[\w\.-]*",
        "",
        text,
    )
    # Strip brackets [ ... ]
    text = re.sub(r"\[.*?\]", "", text)
    # Replace separators with spaces
    text = re.sub(r"[._\-–—]", " ", text)
    # Normalize whitespace
    text = re.sub(r"\s+", " ", text).strip()

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
    junk_pattern = (
        r"(?i)\b(1080p|720p|480p|2160p|4k|uhd|bluray|web-?dl|webrip|hdrip|x264|x265|"
        r"hevc|aac|dts|remux|dual\s*audio|multi\s*sub|esubs?|proper|repack|org\s*audio)\b.*"
    )
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
            # Fallback entries are only kept for 60 seconds so real queries can retry
            ttl = 60 if cached_meta.source == "fallback" else settings.METADATA_CACHE_TTL
            if now - cached_time < ttl:
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

                # Disambiguate and sort results to prioritize:
                # 1. Exact year match if year provided
                # 2. Exact title match (case-insensitive)
                # 3. High vote count (avoids 0-vote student/indie stubs overwriting blockbusters)
                # 4. Popularity
                def _score_movie(m: Dict[str, Any]) -> float:
                    score = 0.0
                    m_title = (m.get("title") or m.get("original_title") or "").strip().lower()
                    m_date = m.get("release_date") or ""
                    m_year = int(m_date[:4]) if len(m_date) >= 4 and m_date[:4].isdigit() else None
                    vote_cnt = m.get("vote_count", 0) or 0
                    pop = float(m.get("popularity", 0.0) or 0.0)

                    # Title match
                    if m_title == clean_title.lower():
                        score += 5000.0
                    elif clean_title.lower() in m_title:
                        score += 1000.0

                    # Year match
                    if effective_year and m_year:
                        if m_year == effective_year:
                            score += 10000.0
                        elif abs(m_year - effective_year) <= 1:
                            score += 500.0

                    # Prioritize real releases with high audience votes
                    score += min(vote_cnt, 50000) * 1.5
                    score += pop * 2.0
                    return score

                results.sort(key=_score_movie, reverse=True)
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
        imdb_id = (extended_data or {}).get("imdb_id") or data.get("imdb_id")
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
            imdb_id=imdb_id,
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
        """Retrieve trending movies strictly available on OTT / Digital streaming."""
        cache_key = f"ott_trending:{time_window}:{page}"
        now = time.time()

        if cache_key in self._trending_cache:
            cached_time, cached_trending = self._trending_cache[cache_key]
            if now - cached_time < 3600:  # 1 hour cache
                return cached_trending

        if not self.is_configured():
            # Return curated fallback list of released cinema
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

        # 90-day theatrical-to-OTT buffer: excludes movies still in theatrical exclusivity or unreleased
        ott_cutoff = (datetime.date.today() - datetime.timedelta(days=90)).isoformat()
        params = {
            "sort_by": "popularity.desc",
            "with_release_type": "4|5|6",  # 4 = Digital (OTT/VOD), 5 = Physical, 6 = TV
            "primary_release_date.lte": ott_cutoff,
            "vote_count.gte": "100",
            "include_adult": "false",
            "page": str(page),
        }
        return await self._fetch_movie_list(
            f"{settings.TMDB_BASE_URL}/discover/movie",
            params,
            cache_key,
            min_votes=100,
        )

    async def _fetch_movie_list(
        self,
        url: str,
        extra_params: Dict[str, str],
        cache_key: str,
        min_votes: int = 50,
        require_poster: bool = True,
    ) -> TrendingMoviesResponse:
        now = time.time()
        if cache_key in self._trending_cache:
            cached_time, cached_res = self._trending_cache[cache_key]
            if now - cached_time < 3600:
                return cached_res

        if not self.is_configured():
            return TrendingMoviesResponse(page=1, total_pages=1, results=[])

        headers, base_params = self._get_auth_headers_and_params()
        params = {**base_params, **extra_params}
        ott_cutoff = (datetime.date.today() - datetime.timedelta(days=75)).isoformat()

        try:
            async with httpx.AsyncClient(timeout=6.0) as client:
                resp = await client.get(url, headers=headers, params=params)
                if resp.status_code == 200:
                    data = resp.json()
                    raw_results = data.get("results", [])
                    parsed = []
                    for item in raw_results:
                        # Must have valid poster
                        if require_poster and not item.get("poster_path"):
                            continue
                        # Strictly reject unreleased or theatrical-only titles
                        rel_date = item.get("release_date")
                        if not rel_date or rel_date > ott_cutoff:
                            continue
                        # Must have sufficient viewer vote count
                        if item.get("vote_count", 0) < min_votes:
                            continue

                        parsed.append(self._parse_movie_dict(item))

                    res = TrendingMoviesResponse(
                        page=data.get("page", 1),
                        total_pages=data.get("total_pages", 1),
                        results=parsed,
                    )
                    self._trending_cache[cache_key] = (now, res)
                    return res
        except Exception as e:
            logger.warning("Error fetching movie list from %s: %s", url, str(e))

        return TrendingMoviesResponse(page=1, total_pages=1, results=[])

    async def get_popular_movies(self, page: int = 1) -> TrendingMoviesResponse:
        """Retrieve real, released popular movies from TMDb with confirmed OTT/Digital availability."""
        ott_cutoff = (datetime.date.today() - datetime.timedelta(days=90)).isoformat()
        params = {
            "sort_by": "popularity.desc",
            "with_release_type": "4|5|6",
            "primary_release_date.lte": ott_cutoff,
            "vote_count.gte": "150",
            "include_adult": "false",
            "page": str(page),
        }
        return await self._fetch_movie_list(
            f"{settings.TMDB_BASE_URL}/discover/movie",
            params,
            f"popular_ott_released:{page}",
            min_votes=150,
        )

    async def get_top_rated_movies(self, page: int = 1) -> TrendingMoviesResponse:
        """Retrieve true top rated cinema masterpieces with high vote thresholds."""
        ott_cutoff = (datetime.date.today() - datetime.timedelta(days=90)).isoformat()
        params = {
            "sort_by": "vote_average.desc",
            "vote_count.gte": "1000",
            "primary_release_date.lte": ott_cutoff,
            "include_adult": "false",
            "page": str(page),
        }
        return await self._fetch_movie_list(
            f"{settings.TMDB_BASE_URL}/discover/movie",
            params,
            f"top_rated_masterpieces:{page}",
            min_votes=1000,
        )

    async def discover_movies(self, language: str = "ml", sort_by: str = "popularity.desc", page: int = 1) -> TrendingMoviesResponse:
        """Discover released regional movies (e.g. Malayalam 'ml', Tamil 'ta', etc.) with real votes."""
        ott_cutoff = (datetime.date.today() - datetime.timedelta(days=60)).isoformat()
        params = {
            "with_original_language": language,
            "sort_by": sort_by,
            "primary_release_date.lte": ott_cutoff,
            "vote_count.gte": "10",
            "include_adult": "false",
            "page": str(page),
        }
        return await self._fetch_movie_list(
            f"{settings.TMDB_BASE_URL}/discover/movie",
            params,
            f"discover_released:{language}:{page}",
            min_votes=10,
        )


    async def search_movie_suggestions(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Fast autocomplete search returning top suggestions (title, year, poster thumbnail, id) from TMDb.
        """
        clean_title, parsed_year = sanitize_movie_query(query)
        if not clean_title:
            return []

        if not self.is_configured():
            return [
                {
                    "id": None,
                    "title": clean_title,
                    "year": str(parsed_year) if parsed_year else None,
                    "poster_url": None,
                    "rating": None,
                }
            ]

        headers, base_params = self._get_auth_headers_and_params()
        search_params = {**base_params, "query": clean_title, "include_adult": "false"}
        if parsed_year:
            search_params["year"] = str(parsed_year)

        suggestions: List[Dict[str, Any]] = []

        try:
            async with httpx.AsyncClient(timeout=3.5) as client:
                search_url = f"{settings.TMDB_BASE_URL}/search/movie"
                res = await client.get(search_url, headers=headers, params=search_params)
                if res.status_code == 200:
                    data = res.json()
                    results = data.get("results", [])
                    # Retry without year if needed
                    if not results and parsed_year:
                        search_params.pop("year", None)
                        res2 = await client.get(search_url, headers=headers, params=search_params)
                        if res2.status_code == 200:
                            results = res2.json().get("results", [])

                    results.sort(
                        key=lambda m: (
                            5000 if (m.get("title") or "").strip().lower() == clean_title.lower() else 0
                        ) + min(m.get("vote_count", 0) or 0, 50000) * 1.5 + float(m.get("popularity", 0.0) or 0.0),
                        reverse=True,
                    )

                    for m in results[:limit]:
                        release_date = m.get("release_date") or ""
                        year_str = release_date.split("-")[0] if release_date else None
                        poster_path = m.get("poster_path")
                        suggestions.append(
                            {
                                "id": m.get("id"),
                                "title": m.get("title") or m.get("original_title") or clean_title,
                                "year": year_str,
                                "poster_url": self._format_image_url(poster_path, "w185"),
                                "rating": round(float(m.get("vote_average", 0)), 1) if m.get("vote_average") else None,
                            }
                        )
        except Exception as e:
            logger.debug("TMDb suggestions error for '%s': %s", clean_title, e)

        return suggestions


tmdb_service = TmdbService()
