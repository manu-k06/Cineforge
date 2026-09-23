import React, { useState, useEffect, useRef } from 'react'
import { getPopularMovies, getTrendingMovies } from '../services/api'

export default function HeroBanner({ onQuickPlay }) {
  const [movies, setMovies] = useState([])
  const [isLoading, setIsLoading] = useState(true)
  const [currentIndex, setCurrentIndex] = useState(0)
  const timerRef = useRef(null)

  // Fetch verified released trending movies
  useEffect(() => {
    let isMounted = true

    async function fetchHeroMovies() {
      try {
        setIsLoading(true)

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
          const formatted = valid.slice(0, 6).map((m) => {
            const releaseYear = m.year || (m.release_date ? m.release_date.split('-')[0] : '2025')
            const displayRating = m.rating ? Number(m.rating).toFixed(1) : '7.8'

            return {
              id: m.tmdb_id || m.title,
              title: m.title,
              searchQuery: m.title,
              synopsis: m.overview || 'Newly released blockbuster streaming in high definition on Cineby.',
              year: releaseYear,
              rating: displayRating,
              mediaType: m.media_type === 'tv' ? 'TV show' : 'Movie',
              backdrop: m.backdrop_url,
            }
          })

          setMovies(formatted)
        }
      } catch (err) {
        console.error('Failed to load hero banner movies:', err)
      } finally {
        if (isMounted) setIsLoading(false)
      }
    }

    fetchHeroMovies()

    return () => {
      isMounted = false
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

  if (isLoading || movies.length === 0) {
    return (
      <section className="hero-slider-shell" style={{ height: '70vh', minHeight: '520px' }}>
        <div className="home-hero" style={{ background: '#07080b' }}>
          <div className="hero-inner">
            <p className="eyebrow">Discovering...</p>
            <div style={{ height: '44px', width: '320px', background: 'rgba(255,255,255,0.08)', borderRadius: '6px', margin: '14px 0' }} />
            <div style={{ height: '18px', width: '160px', background: 'rgba(255,255,255,0.05)', borderRadius: '4px', marginBottom: '14px' }} />
            <div style={{ height: '40px', width: '420px', background: 'rgba(255,255,255,0.04)', borderRadius: '4px' }} />
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
                  onClick={() => onQuickPlay(movie.searchQuery)}
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
    </section>
  )
}
