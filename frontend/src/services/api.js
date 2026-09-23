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

/**
 * TMDb Metadata Enrichment Endpoints
 */
export async function getMetadataStatus() {
  try {
    const response = await fetch(`${API_BASE}/api/metadata/status`)
    return response.ok ? await response.json() : { status: 'unconfigured', configured: false }
  } catch {
    return { status: 'unconfigured', configured: false }
  }
}

export async function getMovieMetadata(title, year = null) {
  let url = `${API_BASE}/api/metadata/movie?title=${encodeURIComponent(title)}`
  if (year) url += `&year=${year}`
  const response = await fetch(url)
  if (!response.ok) {
    throw new Error(`Failed to fetch metadata for ${title}`)
  }
  return await response.json()
}

export async function getTrendingMovies(timeWindow = 'week', page = 1) {
  const response = await fetch(`${API_BASE}/api/metadata/trending?time_window=${timeWindow}&page=${page}`)
  if (!response.ok) {
    throw new Error('Failed to fetch trending movies')
  }
  return await response.json()
}

export async function getPopularMovies(page = 1) {
  try {
    const response = await fetch(`${API_BASE}/api/metadata/popular?page=${page}`)
    if (response.ok) return await response.json()
  } catch (e) {
    console.warn('Popular endpoint unavailable, falling back to trending:', e)
  }
  return await getTrendingMovies('day', page)
}

export async function getTopRatedMovies(page = 1) {
  try {
    const response = await fetch(`${API_BASE}/api/metadata/top-rated?page=${page}`)
    if (response.ok) return await response.json()
  } catch (e) {
    console.warn('Top-rated endpoint unavailable, falling back to trending:', e)
  }
  return await getTrendingMovies('week', 2)
}

export async function getRegionalMovies(language = 'ml', page = 1) {
  try {
    const response = await fetch(`${API_BASE}/api/metadata/discover?language=${language}&page=${page}`)
    if (response.ok) return await response.json()
  } catch (e) {
    console.warn('Regional discover endpoint unavailable, falling back to trending:', e)
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


