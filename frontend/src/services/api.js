/**
 * Cineforge API Client
 * Connects frontend to FastAPI Telegram bot delivery backend
 */

export async function searchMovies(query, page = 1) {
  const url = `/api/search?q=${encodeURIComponent(query)}&page=${page}`
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

  const response = await fetch('/api/search/deliver', {
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
    const response = await fetch('/health')
    return response.ok
  } catch {
    return false
  }
}
