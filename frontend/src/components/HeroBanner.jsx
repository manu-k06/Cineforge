import React, { useState, useEffect, useRef } from 'react'
import { X } from 'lucide-react'
import { getPopularMovies, getTrendingMovies } from '../services/api'
import { getOptimizedImageUrl } from '../utils/helpers'
import { useWatchHistory } from '../context/WatchHistoryContext'

const DEFAULT_HERO_MOVIES = [
  {
    id: 693134,
    title: 'Dune: Part Two',
    searchQuery: 'Dune Part Two',
    synopsis: 'Paul Atreides unites with Chani and the Fremen while seeking revenge against the conspirators who destroyed his family.',
    year: '2024',
    rating: '8.2',
    mediaType: 'Movie',
    backdrop: getOptimizedImageUrl('/xOMo8BRK7PfcJv9JCnx7s520Wio.jpg', 'w1280'),
  },
  {
    id: 533535,
    title: 'Deadpool & Wolverine',
    searchQuery: 'Deadpool and Wolverine',
    synopsis: 'A listless Wade Wilson toils in civilian life with his days as the morally flexible mercenary behind him, until the TVA pulls him into an epic mission.',
    year: '2024',
    rating: '7.7',
    mediaType: 'Movie',
    backdrop: getOptimizedImageUrl('/yDHYTfA3R0jFYba16jBB1jv8M9l.jpg', 'w1280'),
  },
  {
    id: 872585,
    title: 'Oppenheimer',
    searchQuery: 'Oppenheimer',
    synopsis: 'The story of J. Robert Oppenheimer’s role in the development of the atomic bomb during World War II.',
    year: '2023',
    rating: '8.1',
    mediaType: 'Movie',
    backdrop: getOptimizedImageUrl('/fm6K9vYvt39mgrVIezqp90uk8Ux.jpg', 'w1280'),
  },
  {
    id: 157336,
    title: 'Interstellar',
    searchQuery: 'Interstellar',
    synopsis: 'The adventures of a group of explorers who make use of a newly discovered wormhole to surpass the limitations on human space travel.',
    year: '2014',
    rating: '8.4',
    mediaType: 'Movie',
    backdrop: getOptimizedImageUrl('/xJHokMbljvjADYdit5fK5VQsXEG.jpg', 'w1280'),
  },
  {
    id: 155,
    title: 'The Dark Knight',
    searchQuery: 'The Dark Knight',
    synopsis: 'Batman raises the stakes in his war on crime against the Joker, a psychotic criminal mastermind who plunges Gotham into anarchy.',
    year: '2008',
    rating: '8.5',
    mediaType: 'Movie',
    backdrop: getOptimizedImageUrl('/nMKdUUepR0i5zn0y1T4CsSB5chy.jpg', 'w1280'),
  },
]

export default function HeroBanner({ onQuickPlay }) {
  const { isInWatchlist, toggleWatchlist } = useWatchHistory()
  const [movies, setMovies] = useState([])
  const [isLoading, setIsLoading] = useState(true)
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

  // Fetch verified released trending movies
  useEffect(() => {
    let isMounted = true

    // Safety timeout: ensure skeleton doesn't hang indefinitely if network is slow
    const fallbackTimer = setTimeout(() => {
      if (isMounted) {
        setMovies((prev) => (prev.length === 0 ? DEFAULT_HERO_MOVIES : prev))
        setIsLoading(false)
      }
    }, 1800)

    async function fetchHeroMovies() {
      try {
        // Query popular released and weekly trending in parallel
        const [popRes, trendRes] = await Promise.allSettled([
          getPopularMovies(1),
          getTrendingMovies('week', 1),
        ])

        const popList = popRes.status === 'fulfilled' && popRes.value?.results ? popRes.value.results : []
        const trendList = trendRes.status === 'fulfilled' && trendRes.value?.results ? trendRes.value.results : []

        const combined = [...popList, ...trendList]
        const today = new Date()
        const currentYear = today.getFullYear()

        const seen = new Set()
        const valid = combined.filter((m) => {
          if (!m.backdrop_url || !m.title) return false
          const key = m.title.toLowerCase().trim()
          if (seen.has(key)) return false
          seen.add(key)

          const yr = parseInt(m.year || '0', 10)
          if (yr > currentYear) return false
          if (m.release_date && new Date(m.release_date) > today) return false

          return true
        })

        if (valid.length > 0 && isMounted) {
          const formatted = valid.slice(0, 8).map((m) => {
            const releaseYear = m.year || (m.release_date ? m.release_date.split('-')[0] : '2025')
            const displayRating = m.rating ? Number(m.rating).toFixed(1) : '7.8'

            return {
              id: m.tmdb_id || m.title,
              title: m.title,
              searchQuery: m.title,
              synopsis: m.overview || 'Newly released blockbuster streaming in high definition on Cineforge.',
              year: releaseYear,
              rating: displayRating,
              mediaType: m.media_type === 'tv' ? 'TV show' : 'Movie',
              backdrop: m.backdrop_url,
            }
          })

          setMovies(formatted)
          clearTimeout(fallbackTimer)
          setIsLoading(false)
        } else if (isMounted) {
          setMovies(DEFAULT_HERO_MOVIES)
          clearTimeout(fallbackTimer)
          setIsLoading(false)
        }
      } catch (err) {
        console.error('Failed to load hero banner movies:', err)
        if (isMounted) {
          setMovies(DEFAULT_HERO_MOVIES)
          clearTimeout(fallbackTimer)
          setIsLoading(false)
        }
      }
    }

    fetchHeroMovies()

    return () => {
      isMounted = false
      clearTimeout(fallbackTimer)
    }
  }, [])

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

  // Hero Skeleton Shimmer Placeholder
  if (isLoading || movies.length === 0) {
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
