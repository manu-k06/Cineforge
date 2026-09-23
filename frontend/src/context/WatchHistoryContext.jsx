import React, { createContext, useContext, useEffect, useState, useMemo, useRef } from 'react'
import { useAuth } from './AuthContext'
import {
  getWatchHistoryApi,
  saveWatchProgressApi,
  deleteWatchHistoryApi,
  getWatchlistApi,
  saveWatchlistApi,
  deleteWatchlistApi,
  syncGuestDataApi,
} from '../services/api'

const STORAGE_KEYS = {
  HISTORY: 'cineforge_watch_history_v1',
  WATCHLIST: 'cineforge_watchlist_v1',
}

const WatchHistoryContext = createContext({
  watchHistory: [],
  continueWatchingList: [],
  watchlist: [],
  updateProgress: () => {},
  removeFromHistory: () => {},
  clearHistory: () => {},
  toggleWatchlist: () => {},
  isInWatchlist: () => false,
  removeFromWatchlist: () => {},
})

function loadLocal(key, fallback = []) {
  try {
    const raw = localStorage.getItem(key)
    return raw ? JSON.parse(raw) : fallback
  } catch (e) {
    console.warn(`Failed to read ${key} from localStorage:`, e)
    return fallback
  }
}

function saveLocal(key, value) {
  try {
    localStorage.setItem(key, JSON.stringify(value))
  } catch (e) {
    console.warn(`Failed to save ${key} to localStorage:`, e)
  }
}

export function WatchHistoryProvider({ children }) {
  const { user, session } = useAuth()
  const [watchHistory, setWatchHistory] = useState(() => loadLocal(STORAGE_KEYS.HISTORY, []))
  const [watchlist, setWatchlist] = useState(() => loadLocal(STORAGE_KEYS.WATCHLIST, []))
  const hasSyncedGuestRef = useRef(false)

  // Save to localStorage whenever local state changes
  useEffect(() => {
    saveLocal(STORAGE_KEYS.HISTORY, watchHistory)
  }, [watchHistory])

  useEffect(() => {
    saveLocal(STORAGE_KEYS.WATCHLIST, watchlist)
  }, [watchlist])

  // Sync with Supabase on user sign in
  useEffect(() => {
    const token = session?.access_token
    if (!token || !user) {
      hasSyncedGuestRef.current = false
      return
    }

    if (hasSyncedGuestRef.current) return
    hasSyncedGuestRef.current = true

    const syncWithCloud = async () => {
      try {
        const localHist = loadLocal(STORAGE_KEYS.HISTORY, [])
        const localWatch = loadLocal(STORAGE_KEYS.WATCHLIST, [])

        // 1. If local guest items exist, sync them to cloud account
        if (localHist.length > 0 || localWatch.length > 0) {
          await syncGuestDataApi(token, localHist, localWatch)
        }

        // 2. Fetch authoritative cloud records
        const [cloudHist, cloudWatch] = await Promise.all([
          getWatchHistoryApi(token),
          getWatchlistApi(token),
        ])

        // 3. Merge cloud records into state
        if (cloudHist && cloudHist.length > 0) {
          setWatchHistory((prev) => {
            const map = new Map()
            // Cloud items
            cloudHist.forEach((item) => map.set(item.title.toLowerCase(), item))
            // Newer local items
            prev.forEach((item) => {
              const k = item.title.toLowerCase()
              if (!map.has(k)) {
                map.set(k, item)
              }
            })
            return Array.from(map.values())
          })
        }

        if (cloudWatch && cloudWatch.length > 0) {
          setWatchlist((prev) => {
            const map = new Map()
            cloudWatch.forEach((item) => map.set(item.title.toLowerCase(), item))
            prev.forEach((item) => {
              const k = item.title.toLowerCase()
              if (!map.has(k)) {
                map.set(k, item)
              }
            })
            return Array.from(map.values())
          })
        }
      } catch (err) {
        console.warn('Watch history cloud sync failed:', err)
      }
    }

    syncWithCloud()
  }, [user, session?.access_token])

  // Record / Upsert Playback Progress
  const updateProgress = (item) => {
    if (!item || !item.title) return

    const title = item.title
    const progressSeconds = Math.max(0, item.progress_seconds || 0)
    const durationSeconds = Math.max(0, item.duration_seconds || 0)
    const progressPercent = durationSeconds > 0 ? (progressSeconds / durationSeconds) * 100 : 0
    const isCompleted = item.completed || (progressPercent >= 90 && durationSeconds > 0)

    const updatedRecord = {
      title,
      clean_title: item.clean_title || title,
      year: item.year || null,
      poster_url: item.poster_url || null,
      backdrop_url: item.backdrop_url || null,
      stream_url: item.stream_url || '',
      candidate_title: item.candidate_title || title,
      quality: item.quality || null,
      progress_seconds: progressSeconds,
      duration_seconds: durationSeconds,
      progress_percent: Math.min(100, Math.round(progressPercent)),
      completed: isCompleted,
      updated_at: new Date().toISOString(),
    }

    setWatchHistory((prev) => {
      const filtered = prev.filter((p) => p.title.toLowerCase() !== title.toLowerCase())
      return [updatedRecord, ...filtered]
    })

    // Cloud persistence if user is logged in
    const token = session?.access_token
    if (token) {
      saveWatchProgressApi(token, updatedRecord).catch((e) =>
        console.warn('Failed to save progress to cloud:', e)
      )
    }
  }

  // Remove single title from Watch History
  const removeFromHistory = (title) => {
    if (!title) return
    setWatchHistory((prev) => prev.filter((p) => p.title.toLowerCase() !== title.toLowerCase()))

    const token = session?.access_token
    if (token) {
      deleteWatchHistoryApi(token, title).catch((e) =>
        console.warn('Failed to delete history on cloud:', e)
      )
    }
  }

  // Clear entire history
  const clearHistory = () => {
    setWatchHistory([])
    saveLocal(STORAGE_KEYS.HISTORY, [])
  }

  // Check if title is in watchlist
  const isInWatchlist = (title) => {
    if (!title) return false
    return watchlist.some((item) => item.title.toLowerCase() === title.toLowerCase())
  }

  // 1-Click Toggle for Watchlist
  const toggleWatchlist = (movie) => {
    if (!movie || !movie.title) return

    const title = movie.title
    const exists = isInWatchlist(title)
    const token = session?.access_token

    if (exists) {
      // Remove
      setWatchlist((prev) => prev.filter((item) => item.title.toLowerCase() !== title.toLowerCase()))
      if (token) {
        deleteWatchlistApi(token, title).catch((e) =>
          console.warn('Failed to delete from watchlist on cloud:', e)
        )
      }
    } else {
      // Add
      const newEntry = {
        title,
        clean_title: movie.clean_title || movie.title,
        year: movie.year || null,
        rating: movie.rating || null,
        poster_url: movie.poster_url || null,
        backdrop_url: movie.backdrop_url || null,
        overview: movie.overview || null,
        genres: movie.genres || [],
        created_at: new Date().toISOString(),
      }
      setWatchlist((prev) => [newEntry, ...prev])
      if (token) {
        saveWatchlistApi(token, newEntry).catch((e) =>
          console.warn('Failed to add to watchlist on cloud:', e)
        )
      }
    }
  }

  const removeFromWatchlist = (title) => {
    if (!title) return
    setWatchlist((prev) => prev.filter((item) => item.title.toLowerCase() !== title.toLowerCase()))
    const token = session?.access_token
    if (token) {
      deleteWatchlistApi(token, title).catch((e) =>
        console.warn('Failed to delete from watchlist on cloud:', e)
      )
    }
  }

  // Filter for Continue Watching Rail:
  // Requires at least 15s watched, not finished, and duration < 90%
  const continueWatchingList = useMemo(() => {
    return watchHistory.filter((item) => {
      if (item.completed) return false
      if (!item.progress_seconds || item.progress_seconds < 15) return false
      if (item.duration_seconds > 0) {
        const percent = (item.progress_seconds / item.duration_seconds) * 100
        if (percent >= 90) return false
      }
      return true
    })
  }, [watchHistory])

  const value = {
    watchHistory,
    continueWatchingList,
    watchlist,
    updateProgress,
    removeFromHistory,
    clearHistory,
    toggleWatchlist,
    isInWatchlist,
    removeFromWatchlist,
  }

  return (
    <WatchHistoryContext.Provider value={value}>
      {children}
    </WatchHistoryContext.Provider>
  )
}

export function useWatchHistory() {
  const context = useContext(WatchHistoryContext)
  if (!context) {
    throw new Error('useWatchHistory must be used within a WatchHistoryProvider')
  }
  return context
}
