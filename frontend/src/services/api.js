/**
 * Cineforge API Client
 * Connects frontend to FastAPI Telegram bot delivery backend and CineAI service
 */

const API_BASE = (import.meta.env.VITE_API_BASE_URL || '').replace(/\/$/, '')

export async function searchMovies(query, page = 1, useAi = true) {
  const url = `${API_BASE}/api/search?q=${encodeURIComponent(query)}&page=${page}&use_ai=${useAi}`
  const response = await fetch(url)
  
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}))
    throw new Error(errorData.detail || `Search failed with status ${response.status}`)
  }
  
  return await response.json()
}

export async function getSearchSuggestions(query, limit = 5) {
  if (!query || !query.trim() || query.trim().length < 2) return []
  try {
    const url = `${API_BASE}/api/search/suggestions?q=${encodeURIComponent(query.trim())}&limit=${limit}`
    const response = await fetch(url)
    if (!response.ok) return []
    const data = await response.json()
    return data.suggestions || []
  } catch {
    return []
  }
}

export async function deliverCandidate(candidate) {
  const payload = {
    candidate_id: candidate.candidate_id,
    source_bot: candidate.source_bot || 'Spoty_xbot',
    source_message_id: candidate.source_message_id,
    callback_data: candidate.callback_data || null,
    start_payload: candidate.start_payload || null,
  }

  const response = await fetch(`${API_BASE}/api/search/deliver`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(payload),
  })

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}))
    throw new Error(errorData.detail || `Stream delivery failed with status ${response.status}`)
  }

  return await response.json()
}

export async function getBackendHealth() {
  try {
    const response = await fetch(`${API_BASE}/health`)
    return response.ok
  } catch {
    return false
  }
}

/**
 * CineAI Endpoints
 */
export async function getAiStatus() {
  try {
    const response = await fetch(`${API_BASE}/api/ai/status`)
    return response.ok ? await response.json() : null
  } catch {
    return null
  }
}

export async function getAiRecommendations(prompt, count = 5) {
  const response = await fetch(`${API_BASE}/api/ai/recommend`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ prompt, count }),
  })
  if (!response.ok) {
    const err = await response.json().catch(() => ({}))
    throw new Error(err.detail || 'Failed to fetch recommendations')
  }
  return await response.json()
}

export async function askAiCompanion(movieTitle, question) {
  const response = await fetch(`${API_BASE}/api/ai/ask`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ movie_title: movieTitle, question }),
  })
  if (!response.ok) {
    const err = await response.json().catch(() => ({}))
    throw new Error(err.detail || 'Failed to ask CineAI companion')
  }
  return await response.json()
}

import { getOptimizedImageUrl } from '../utils/helpers'

const TMDB_API_KEY = import.meta.env.VITE_TMDB_API_KEY || '27c65ee52f2aa6f980dc01b4162d2daf'
const TMDB_BASE_URL = 'https://api.themoviedb.org/3'

function mapTmdbMovie(m) {
  if (!m) return null
  const releaseYear = m.release_date ? m.release_date.split('-')[0] : (m.first_air_date ? m.first_air_date.split('-')[0] : '2024')
  return {
    tmdb_id: m.id,
    title: m.title || m.name || 'Untitled',
    year: releaseYear,
    rating: m.vote_average ? Number(m.vote_average).toFixed(1) : '7.8',
    poster_url: m.poster_path ? getOptimizedImageUrl(m.poster_path, 'w500') : (m.poster_url ? getOptimizedImageUrl(m.poster_url, 'w500') : null),
    backdrop_url: m.backdrop_path ? getOptimizedImageUrl(m.backdrop_path, 'w1280') : (m.backdrop_url ? getOptimizedImageUrl(m.backdrop_url, 'w1280') : null),
    overview: m.overview || '',
    media_type: m.media_type || 'movie',
    vote_count: m.vote_count || 0,
    release_date: m.release_date || null,
  }
}

/**
 * TMDb Metadata Enrichment Endpoints (Dynamic Backend + Direct TMDb Fallback)
 */
export async function getMetadataStatus() {
  if (API_BASE) {
    try {
      const response = await fetch(`${API_BASE}/api/metadata/status`)
      if (response.ok) return await response.json()
    } catch {
      // Fallback
    }
  }
  return { status: 'direct_tmdb', configured: true }
}

export async function getMovieMetadata(title, year = null) {
  if (API_BASE) {
    try {
      let url = `${API_BASE}/api/metadata/movie?title=${encodeURIComponent(title)}`
      if (year) url += `&year=${year}`
      const response = await fetch(url)
      if (response.ok) {
        const data = await response.json()
        if (data.poster_url) data.poster_url = getOptimizedImageUrl(data.poster_url, 'w500')
        if (data.backdrop_url) data.backdrop_url = getOptimizedImageUrl(data.backdrop_url, 'w1280')
        return data
      }
    } catch {
      // Fall through to direct TMDb
    }
  }

  // Direct TMDb Search fallback
  try {
    const tmdbUrl = `${TMDB_BASE_URL}/search/movie?api_key=${TMDB_API_KEY}&query=${encodeURIComponent(title)}${year ? `&year=${year}` : ''}`
    const res = await fetch(tmdbUrl)
    if (res.ok) {
      const data = await res.json()
      if (data.results && data.results.length > 0) {
        return mapTmdbMovie(data.results[0])
      }
    }
  } catch (err) {
    console.warn(`Direct TMDb search failed for ${title}:`, err)
  }

  throw new Error(`Failed to fetch metadata for ${title}`)
}

export async function getTrendingMovies(timeWindow = 'week', page = 1) {
  if (API_BASE) {
    try {
      const controller = new AbortController()
      const timeoutId = setTimeout(() => controller.abort(), 2500)
      const response = await fetch(`${API_BASE}/api/metadata/trending?time_window=${timeWindow}&page=${page}`, {
        signal: controller.signal,
      })
      clearTimeout(timeoutId)
      if (response.ok) {
        const data = await response.json()
        if (data?.results?.length) {
          data.results = data.results.map((m) => ({
            ...m,
            poster_url: m.poster_url ? getOptimizedImageUrl(m.poster_url, 'w500') : null,
            backdrop_url: m.backdrop_url ? getOptimizedImageUrl(m.backdrop_url, 'w1280') : null,
          }))
          return data
        }
      }
    } catch {
      // Fall through to direct TMDb
    }
  }

  // Direct TMDb Trending
  const tmdbUrl = `${TMDB_BASE_URL}/trending/movie/${timeWindow}?api_key=${TMDB_API_KEY}&page=${page}`
  const res = await fetch(tmdbUrl)
  if (!res.ok) throw new Error('Failed to fetch trending movies from TMDb')
  const data = await res.json()
  return {
    results: (data.results || []).map(mapTmdbMovie).filter(Boolean),
    total_pages: data.total_pages || 1,
  }
}

export async function getPopularMovies(page = 1) {
  if (API_BASE) {
    try {
      const controller = new AbortController()
      const timeoutId = setTimeout(() => controller.abort(), 2500)
      const response = await fetch(`${API_BASE}/api/metadata/popular?page=${page}`, { signal: controller.signal })
      clearTimeout(timeoutId)
      if (response.ok) {
        const data = await response.json()
        if (data?.results?.length) {
          data.results = data.results.map((m) => ({
            ...m,
            poster_url: m.poster_url ? getOptimizedImageUrl(m.poster_url, 'w500') : null,
            backdrop_url: m.backdrop_url ? getOptimizedImageUrl(m.backdrop_url, 'w1280') : null,
          }))
          return data
        }
      }
    } catch {
      // Fall through to direct TMDb
    }
  }

  // Direct TMDb Popular
  try {
    const tmdbUrl = `${TMDB_BASE_URL}/movie/popular?api_key=${TMDB_API_KEY}&page=${page}`
    const res = await fetch(tmdbUrl)
    if (res.ok) {
      const data = await res.json()
      return {
        results: (data.results || []).map(mapTmdbMovie).filter(Boolean),
        total_pages: data.total_pages || 1,
      }
    }
  } catch (e) {
    console.warn('Direct TMDb popular failed, falling back to trending:', e)
  }
  return await getTrendingMovies('day', page)
}

export async function getTopRatedMovies(page = 1) {
  if (API_BASE) {
    try {
      const controller = new AbortController()
      const timeoutId = setTimeout(() => controller.abort(), 2500)
      const response = await fetch(`${API_BASE}/api/metadata/top-rated?page=${page}`, { signal: controller.signal })
      clearTimeout(timeoutId)
      if (response.ok) {
        const data = await response.json()
        if (data?.results?.length) {
          data.results = data.results.map((m) => ({
            ...m,
            poster_url: m.poster_url ? getOptimizedImageUrl(m.poster_url, 'w500') : null,
            backdrop_url: m.backdrop_url ? getOptimizedImageUrl(m.backdrop_url, 'w1280') : null,
          }))
          return data
        }
      }
    } catch {
      // Fall through to direct TMDb
    }
  }

  // Direct TMDb Top Rated
  try {
    const tmdbUrl = `${TMDB_BASE_URL}/movie/top_rated?api_key=${TMDB_API_KEY}&page=${page}`
    const res = await fetch(tmdbUrl)
    if (res.ok) {
      const data = await res.json()
      return {
        results: (data.results || []).map(mapTmdbMovie).filter(Boolean),
        total_pages: data.total_pages || 1,
      }
    }
  } catch (e) {
    console.warn('Direct TMDb top-rated failed, falling back to trending:', e)
  }
  return await getTrendingMovies('week', 2)
}

export async function getRegionalMovies(language = 'ml', page = 1) {
  if (API_BASE) {
    try {
      const controller = new AbortController()
      const timeoutId = setTimeout(() => controller.abort(), 2500)
      const response = await fetch(`${API_BASE}/api/metadata/discover?language=${language}&page=${page}`, {
        signal: controller.signal,
      })
      clearTimeout(timeoutId)
      if (response.ok) {
        const data = await response.json()
        if (data?.results?.length) {
          data.results = data.results.map((m) => ({
            ...m,
            poster_url: m.poster_url ? getOptimizedImageUrl(m.poster_url, 'w500') : null,
            backdrop_url: m.backdrop_url ? getOptimizedImageUrl(m.backdrop_url, 'w1280') : null,
          }))
          return data
        }
      }
    } catch {
      // Fall through to direct TMDb
    }
  }

  // Direct TMDb Discover for Regional Language (e.g. 'ml' for Malayalam)
  try {
    const tmdbUrl = `${TMDB_BASE_URL}/discover/movie?api_key=${TMDB_API_KEY}&with_original_language=${language}&sort_by=popularity.desc&page=${page}`
    const res = await fetch(tmdbUrl)
    if (res.ok) {
      const data = await res.json()
      return {
        results: (data.results || []).map(mapTmdbMovie).filter(Boolean),
        total_pages: data.total_pages || 1,
      }
    }
  } catch (e) {
    console.warn('Direct regional discover failed, falling back to trending:', e)
  }
  return await getTrendingMovies('day', 2)
}

/**
 * Subtitle Discovery & WebVTT Endpoints
 */
export async function getSubtitleTracks(title = '', year = null, imdbId = null, streamUrl = '') {
  try {
    // Gracefully handle legacy argument order: (streamUrl, title, year)
    let effectiveTitle = title
    let effectiveYear = year
    let effectiveImdbId = imdbId
    let effectiveStreamUrl = streamUrl

    if (typeof title === 'string' && (title.startsWith('http://') || title.startsWith('https://'))) {
      effectiveStreamUrl = title
      effectiveTitle = typeof year === 'string' ? year : ''
      effectiveYear = typeof imdbId === 'number' ? imdbId : null
      effectiveImdbId = null
    }

    const params = new URLSearchParams()
    if (effectiveTitle && String(effectiveTitle).trim()) params.set('title', String(effectiveTitle).trim())
    if (effectiveYear && String(effectiveYear).trim()) params.set('year', String(effectiveYear).trim())
    if (effectiveImdbId && String(effectiveImdbId).trim()) params.set('imdb_id', String(effectiveImdbId).trim())
    if (effectiveStreamUrl && String(effectiveStreamUrl).trim()) params.set('stream_url', String(effectiveStreamUrl).trim())

    const response = await fetch(`${API_BASE}/api/subtitles/tracks?${params.toString()}`)
    if (!response.ok) return { tracks: [] }
    const data = await response.json()
    if (data && data.tracks) {
      data.tracks = data.tracks.map((t) => ({
        ...t,
        vtt_url: t.vtt_url && t.vtt_url.startsWith('http') ? t.vtt_url : `${API_BASE}${t.vtt_url}`,
      }))
    }
    return data
  } catch {
    return { tracks: [] }
  }
}

/**
 * Watch History & Watchlist API Endpoints
 */
export async function getWatchHistoryApi(token) {
  if (!token) return []
  try {
    const res = await fetch(`${API_BASE}/api/history`, {
      headers: { Authorization: `Bearer ${token}` },
    })
    if (!res.ok) return []
    const data = await res.json()
    return data.history || []
  } catch {
    return []
  }
}

export async function saveWatchProgressApi(token, payload) {
  if (!token) return null
  try {
    const res = await fetch(`${API_BASE}/api/history`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify(payload),
    })
    if (!res.ok) return null
    return await res.json()
  } catch {
    return null
  }
}

export async function deleteWatchHistoryApi(token, title) {
  if (!token) return false
  try {
    const res = await fetch(`${API_BASE}/api/history/${encodeURIComponent(title)}`, {
      method: 'DELETE',
      headers: { Authorization: `Bearer ${token}` },
    })
    return res.ok
  } catch {
    return false
  }
}

export async function getWatchlistApi(token) {
  if (!token) return []
  try {
    const res = await fetch(`${API_BASE}/api/watchlist`, {
      headers: { Authorization: `Bearer ${token}` },
    })
    if (!res.ok) return []
    const data = await res.json()
    return data.watchlist || []
  } catch {
    return []
  }
}

export async function saveWatchlistApi(token, payload) {
  if (!token) return null
  try {
    const res = await fetch(`${API_BASE}/api/watchlist`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify(payload),
    })
    if (!res.ok) return null
    return await res.json()
  } catch {
    return null
  }
}

export async function deleteWatchlistApi(token, title) {
  if (!token) return false
  try {
    const res = await fetch(`${API_BASE}/api/watchlist/${encodeURIComponent(title)}`, {
      method: 'DELETE',
      headers: { Authorization: `Bearer ${token}` },
    })
    return res.ok
  } catch {
    return false
  }
}

export async function syncGuestDataApi(token, history, watchlist) {
  if (!token) return null
  try {
    const res = await fetch(`${API_BASE}/api/history/sync-guest`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({ history, watchlist }),
    })
    if (!res.ok) return null
    return await res.json()
  } catch {
    return null
  }
}


