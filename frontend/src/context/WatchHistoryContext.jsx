import React, { createContext, useContext, useEffect, useState, useMemo, useRef } from 'react'
import { useAuth } from './AuthContext'
import {
  getWatchHistoryApi,
  saveWatchProgressApi,
  deleteWatchHistoryApi,
  clearWatchHistoryApi,
  getWatchlistApi,
  saveWatchlistApi,
  deleteWatchlistApi,
  syncGuestDataApi,
} from '../services/api'

const LEGACY_STORAGE_KEYS = {
  HISTORY: 'cineforge_watch_history_v1',
  WATCHLIST: 'cineforge_watchlist_v1',
}

function getStorageKeys(userId) {
  const prefix = userId ? `cineforge_u_${userId}` : 'cineforge_guest'
  return {
    HISTORY: `${prefix}_history_v2`,
    WATCHLIST: `${prefix}_watchlist_v2`,
  }
}

function cleanupLegacyStorage() {
  try {
    localStorage.removeItem(LEGACY_STORAGE_KEYS.HISTORY)
    localStorage.removeItem(LEGACY_STORAGE_KEYS.WATCHLIST)
  } catch (e) {
    // Ignore storage errors
  }
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
  const currentUserId = user?.id || null
  const keys = useMemo(() => getStorageKeys(currentUserId), [currentUserId])

  // Clean up legacy unscoped keys on mount
  useEffect(() => {
    cleanupLegacyStorage()
  }, [])

  const [watchHistory, setWatchHistory] = useState(() => loadLocal(getStorageKeys(user?.id).HISTORY, []))
  const [watchlist, setWatchlist] = useState(() => loadLocal(getStorageKeys(user?.id).WATCHLIST, []))
  const prevUserIdRef = useRef(currentUserId)

  // React immediately to login / logout / account switch
  useEffect(() => {
    if (prevUserIdRef.current !== currentUserId) {
      prevUserIdRef.current = currentUserId
      setWatchHistory(loadLocal(keys.HISTORY, []))
      setWatchlist(loadLocal(keys.WATCHLIST, []))
    }
  }, [currentUserId, keys])

  // Save to the active user's scoped localStorage whenever local state changes
  useEffect(() => {
    saveLocal(keys.HISTORY, watchHistory)
  }, [watchHistory, keys.HISTORY])

  useEffect(() => {
    saveLocal(keys.WATCHLIST, watchlist)
  }, [watchlist, keys.WATCHLIST])

  // Sync with cloud on user sign in or token change
  useEffect(() => {
    const token = session?.access_token
    const userId = user?.id
    if (!token || !userId) {
      return
    }

    let isMounted = true

    const syncWithCloud = async () => {
      try {
        const guestKeys = getStorageKeys(null)
        const guestHist = loadLocal(guestKeys.HISTORY, [])
        const guestWatch = loadLocal(guestKeys.WATCHLIST, [])

        // If genuine guest activity exists on this device, migrate to user account and clear guest storage
        if (guestHist.length > 0 || guestWatch.length > 0) {
          await syncGuestDataApi(token, guestHist, guestWatch)
          saveLocal(guestKeys.HISTORY, [])
          saveLocal(guestKeys.WATCHLIST, [])
        }

        // Fetch user's cloud records
        const [cloudHist, cloudWatch] = await Promise.all([
          getWatchHistoryApi(token),
          getWatchlistApi(token),
        ])

        if (!isMounted) return

        // Update watch history if cloud query returned an array
        if (Array.isArray(cloudHist)) {
          const localUserHist = loadLocal(getStorageKeys(userId).HISTORY, [])
          const map = new Map()
          cloudHist.forEach((item) => {
            if (item?.title) map.set(item.title.toLowerCase(), item)
          })
          localUserHist.forEach((item) => {
            if (item?.title) {
              const k = item.title.toLowerCase()
              if (!map.has(k)) {
                map.set(k, item)
              }
            }
          })
          const mergedHist = Array.from(map.values())
          setWatchHistory(mergedHist)
          saveLocal(getStorageKeys(userId).HISTORY, mergedHist)
        }

        // Update watchlist if cloud query returned an array
        if (Array.isArray(cloudWatch)) {
          const localUserWatch = loadLocal(getStorageKeys(userId).WATCHLIST, [])
          const map = new Map()
          cloudWatch.forEach((item) => {
            if (item?.title) map.set(item.title.toLowerCase(), item)
          })
          localUserWatch.forEach((item) => {
            if (item?.title) {
              const k = item.title.toLowerCase()
              if (!map.has(k)) {
                map.set(k, item)
              }
            }
          })
          const mergedWatch = Array.from(map.values())
          setWatchlist(mergedWatch)
          saveLocal(getStorageKeys(userId).WATCHLIST, mergedWatch)
        }
      } catch (err) {
        console.warn('Watch history cloud sync failed:', err)
      }
    }

    syncWithCloud()

    return () => {
      isMounted = false
    }
  }, [user?.id, session?.access_token])

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
      candidate_id: item.candidate_id || null,
      source_bot: item.source_bot || null,
      start_payload: item.start_payload || null,
      file_size: item.file_size || null,
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
    saveLocal(keys.HISTORY, [])
    const token = session?.access_token
    if (token) {
      clearWatchHistoryApi(token).catch((e) =>
        console.warn('Failed to clear history on cloud:', e)
      )
    }
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
