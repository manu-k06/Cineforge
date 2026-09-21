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
