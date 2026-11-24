import React, { useState, useEffect, useRef, useCallback } from 'react'
import { X, RefreshCw } from 'lucide-react'
import { getTrendingMovies, getPopularMovies } from '../services/api'
import { getOptimizedImageUrl, isOttReleased } from '../utils/helpers'
import { useWatchHistory } from '../context/WatchHistoryContext'

export default function HeroBanner({ onQuickPlay }) {
  const { isInWatchlist, toggleWatchlist } = useWatchHistory()
  const [movies, setMovies] = useState([])
  const [isLoading, setIsLoading] = useState(true)
  const [errorMessage, setErrorMessage] = useState(null)
  const [currentIndex, setCurrentIndex] = useState(0)
  const [selectedMovieForInfo, setSelectedMovieForInfo] = useState(null)
  const timerRef = useRef(null)

  // Close info modal on Escape key
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'Escape' && selectedMovieForInfo) {
        setSelectedMovieForInfo(null)
      }
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [selectedMovieForInfo])

  // Fetch verified released trending movies dynamically from metadata service
  const fetchHeroMovies = useCallback(async () => {
    setIsLoading(true)
    setErrorMessage(null)

    try {
      let rawMovies = []

      // 1. Primary: Query trending movies from desktop/metadata service
      try {
        const trendingData = await getTrendingMovies('week', 1)
        if (trendingData?.results && Array.isArray(trendingData.results)) {
          rawMovies = trendingData.results
        }
      } catch (trendErr) {
        console.warn('[HeroBanner] Trending movies query failed, falling back to popular:', trendErr)
      }

      // 2. Secondary fallback: Query popular movies if trending list was empty
      if (rawMovies.length === 0) {
        try {
          const popData = await getPopularMovies(1)
          if (popData?.results && Array.isArray(popData.results)) {
            rawMovies = popData.results
          }
        } catch (popErr) {
          console.warn('[HeroBanner] Popular movies query failed:', popErr)
        }
      }

      const seen = new Set()
      const valid = rawMovies.filter((m) => {
        const title = m.title || m.name
        const backdrop = m.backdrop_url || m.backdrop_path
        if (!backdrop || !title) return false
        if (!isOttReleased(m)) return false
        const key = title.toLowerCase().trim()
        if (seen.has(key)) return false
        seen.add(key)
        return true
      })

      if (valid.length > 0) {
        const formatted = valid.slice(0, 8).map((m) => {
          const releaseYear = m.year
            ? String(m.year)
            : m.release_date
            ? m.release_date.split('-')[0]
            : m.first_air_date
            ? m.first_air_date.split('-')[0]
            : ''
          const displayRating = m.rating
            ? Number(m.rating).toFixed(1)
            : m.vote_average
            ? Number(m.vote_average).toFixed(1)
            : '7.8'
          const backdrop = m.backdrop_url
            ? getOptimizedImageUrl(m.backdrop_url, 'w1280')
            : m.backdrop_path
            ? getOptimizedImageUrl(m.backdrop_path, 'w1280')
            : ''
          const poster = m.poster_url
            ? getOptimizedImageUrl(m.poster_url, 'w500')
            : m.poster_path
            ? getOptimizedImageUrl(m.poster_path, 'w500')
            : null

          return {
            id: m.id || m.tmdb_id || m.title,
            title: m.title || m.name,
            searchQuery: m.title || m.name,
            synopsis: m.overview || 'Newly released blockbuster streaming in high definition on Cineforge.',
            year: releaseYear,
            rating: displayRating,
            mediaType: m.media_type === 'tv' ? 'TV show' : 'Movie',
            backdrop: backdrop,
            poster_url: poster,
          }
        })

        setMovies(formatted)
        setCurrentIndex(0)
        setErrorMessage(null)
      } else {
        setMovies([])
        if (rawMovies.length === 0) {
          setErrorMessage('Unable to load featured movies from metadata service.')
        } else {
          setErrorMessage('No titles matching digital streaming release criteria are currently available.')
        }
      }
    } catch (err) {
      console.error('[HeroBanner] Failed to load dynamic hero banner movies:', err)
      setMovies([])
      setErrorMessage(err.message || 'Failed to connect to metadata service.')
    } finally {
      setIsLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchHeroMovies()
  }, [fetchHeroMovies])

  // Auto-slide carousel every 7 seconds
  useEffect(() => {
    if (movies.length <= 1) return

    timerRef.current = setInterval(() => {
      setCurrentIndex((prev) => (prev + 1) % movies.length)
    }, 7000)

    return () => {
      if (timerRef.current) clearInterval(timerRef.current)
    }
  }, [movies.length, currentIndex])

  const handleNext = () => {
    if (movies.length === 0) return
    setCurrentIndex((prev) => (prev + 1) % movies.length)
  }

  const handlePrev = () => {
    if (movies.length === 0) return
    setCurrentIndex((prev) => (prev - 1 + movies.length) % movies.length)
  }

  // Hero Skeleton Shimmer Placeholder while loading
  if (isLoading) {
    return (
      <section className="hero-slider-shell hero-skeleton-shell" aria-busy="true" aria-label="Loading featured cinema">
        <div className="home-hero hero-skeleton-hero">
          <div className="hero-vignette" />
          <div className="hero-inner">
            <div className="hero-skeleton-eyebrow" />
            <div className="hero-skeleton-title-box" />
            <div className="hero-skeleton-meta" />
            <div className="hero-skeleton-synopsis">
              <div className="hero-skeleton-line-1" />
              <div className="hero-skeleton-line-2" />
            </div>
            <div className="hero-actions">
              <div className="hero-skeleton-btn-primary" />
              <div className="hero-skeleton-btn-secondary" />
            </div>
          </div>
        </div>
        <div className="hero-slider-controls hero-skeleton-controls">
          <div className="hero-slider-dots">
            {[1, 2, 3, 4, 5].map((i) => (
              <span key={i} className={`hero-skeleton-dot ${i === 1 ? 'is-active' : ''}`} />
            ))}
          </div>
        </div>
      </section>
    )
  }

  // Visible Failure / Empty State (compact, non-intrusive notification; never invent fake movie data)
  if (movies.length === 0) {
    return (
      <section className="hero-fallback-shell" aria-label="Featured cinema unavailable">
        <div className="home-hero-fallback">
          <div className="hero-fallback-content">
            <span className="eyebrow">Featured Spotlight</span>
            <h2>Trending Highlights Offline</h2>
            <p>
              {errorMessage || 'Unable to load spotlight cinema. Check your connection or search for titles directly below.'}
            </p>
          </div>
          <div className="hero-fallback-actions">
            <button
              type="button"
              className="button button-primary"
              onClick={fetchHeroMovies}
              style={{ display: 'inline-flex', alignItems: 'center', gap: '8px' }}
            >
              <RefreshCw size={15} /> Retry
            </button>
          </div>
        </div>
      </section>
    )
  }

  return (
    <section className="hero-slider-shell" data-hero-slider aria-label="Trending titles">
      {/* Sliding Track */}
      <div
        className="hero-slider-track"
        style={{ transform: `translateX(-${currentIndex * 100}%)` }}
      >
        {movies.map((movie) => (
          <article
            key={movie.id}
            className="home-hero"
            style={{ backgroundImage: `url(${movie.backdrop})` }}
          >
            <div className="hero-vignette" />
            <div className="hero-inner">
              <p className="eyebrow">Trending this week</p>
              <h1>{movie.title}</h1>
              <div className="meta-line">
                <span className="rating">★ {movie.rating}</span>
                <span>{movie.year}</span>
                <span>{movie.mediaType}</span>
              </div>
              <p>{movie.synopsis}</p>
              <div className="hero-actions">
                <button
                  type="button"
                  className="button button-primary"
                  onClick={() => onQuickPlay(movie.searchQuery)}
                >
                  ▶ Play
                </button>
                <button
                  type="button"
                  className="button button-secondary"
                  onClick={() => setSelectedMovieForInfo(movie)}
                >
                  <span aria-hidden="true">ⓘ</span> See more
                </button>
              </div>
            </div>
          </article>
        ))}
      </div>

      {/* Hero Slider Controls: Previous / Dots / Next */}
      <div className="hero-slider-controls" aria-label="Hero slider controls">
        <button type="button" onClick={handlePrev} aria-label="Previous title">
          ‹
        </button>
        <div className="hero-slider-dots">
          {movies.map((m, idx) => (
            <button
              key={m.id}
              type="button"
              className={idx === currentIndex ? 'is-active' : ''}
              onClick={() => setCurrentIndex(idx)}
              aria-label={`Show slide ${idx + 1}`}
            />
          ))}
        </div>
        <button type="button" onClick={handleNext} aria-label="Next title">
          ›
        </button>
      </div>

      {/* Hero Movie Info Modal - Expanded Showcase */}
      {selectedMovieForInfo && (
        <div
          className="hero-info-modal-backdrop"
          onClick={() => setSelectedMovieForInfo(null)}
          role="dialog"
          aria-modal="true"
        >
          <div
            className="hero-info-modal-card"
            onClick={(e) => e.stopPropagation()}
          >
            <button
              type="button"
              className="hero-info-close-btn"
              onClick={() => setSelectedMovieForInfo(null)}
              title="Close (Esc)"
            >
              <X size={20} />
            </button>

            {/* Panoramic Cinematic Backdrop Header */}
            <div
              className="hero-info-banner-header"
              style={{ backgroundImage: `url(${selectedMovieForInfo.backdrop})` }}
            >
              <div className="hero-info-vignette" />
              <div className="hero-info-header-content">
                <div className="hero-info-meta-tags">
                  <span className="hero-info-rating">★ {selectedMovieForInfo.rating} TMDB</span>
                  <span className="hero-info-tag">{selectedMovieForInfo.year}</span>
                  <span className="hero-info-tag">{selectedMovieForInfo.mediaType}</span>
                  <span className="hero-info-tag badge-quality">4K UHD / 1080P</span>
                </div>
                <h2 className="hero-info-title">{selectedMovieForInfo.title}</h2>
                <div className="hero-info-header-actions">
                  <button
                    type="button"
                    className="button button-primary hero-info-play-btn"
                    onClick={() => {
                      const query = selectedMovieForInfo.searchQuery
                      setSelectedMovieForInfo(null)
                      onQuickPlay(query)
                    }}
                  >
                    ▶ Play Now
                  </button>

                  <button
                    type="button"
                    className={`button button-secondary hero-info-watchlist-btn ${
                      isInWatchlist(selectedMovieForInfo.title) ? 'is-in-watchlist' : ''
                    }`}
                    onClick={() => {
                      toggleWatchlist({
                        title: selectedMovieForInfo.title,
                        clean_title: selectedMovieForInfo.title,
                        year: selectedMovieForInfo.year,
                        rating: selectedMovieForInfo.rating,
                        poster_url: selectedMovieForInfo.poster_url,
                        backdrop_url: selectedMovieForInfo.backdrop,
                        overview: selectedMovieForInfo.synopsis,
                      })
                    }}
                  >
                    {isInWatchlist(selectedMovieForInfo.title) ? '✓ In Watchlist' : '+ Add to Watchlist'}
                  </button>
                </div>
              </div>
            </div>

            {/* Rich Content Grid */}
            <div className="hero-info-body-grid">
              <div className="hero-info-main-col">
                <h4 className="hero-info-section-title">Storyline</h4>
                <p className="hero-info-synopsis">{selectedMovieForInfo.synopsis}</p>
              </div>

              <div className="hero-info-side-col">
                <div className="hero-info-meta-card">
                  <h4 className="hero-info-section-title">Movie Details</h4>
                  <div className="hero-info-meta-row">
                    <span className="meta-label">Title</span>
                    <span className="meta-value">{selectedMovieForInfo.title}</span>
                  </div>
                  <div className="hero-info-meta-row">
                    <span className="meta-label">Release Year</span>
                    <span className="meta-value">{selectedMovieForInfo.year}</span>
                  </div>
                  <div className="hero-info-meta-row">
                    <span className="meta-label">TMDB Rating</span>
                    <span className="meta-value score">★ {selectedMovieForInfo.rating} / 10</span>
                  </div>
                  <div className="hero-info-meta-row">
                    <span className="meta-label">Format</span>
                    <span className="meta-value">{selectedMovieForInfo.mediaType}</span>
                  </div>
                  <div className="hero-info-meta-row">
                    <span className="meta-label">Audio Tracks</span>
                    <span className="meta-value">Multi-Audio / Original</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </section>
  )
}
