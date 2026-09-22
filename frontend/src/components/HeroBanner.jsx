import React, { useState, useEffect, useRef } from 'react'
import { Play, Plus, Check, Star, ChevronLeft, ChevronRight, Volume2, VolumeX, Sparkles, Loader2 } from 'lucide-react'
import { getPopularMovies, getTrendingMovies } from '../services/api'

export default function HeroBanner({ onQuickPlay }) {
  const [movies, setMovies] = useState([])
  const [isLoading, setIsLoading] = useState(true)
  const [currentIndex, setCurrentIndex] = useState(0)
  const [watchlist, setWatchlist] = useState(new Set())
  const [isMuted, setIsMuted] = useState(true)
  const timerRef = useRef(null)

  // Fetch live, verified released movies with high-res backdrops
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

        // Strict filter: MUST have backdrop, MUST be released (no unreleased movies)
        const seen = new Set()
        const valid = combined.filter((m) => {
          if (!m.backdrop_url || !m.title) return false
          const key = m.title.toLowerCase().trim()
          if (seen.has(key)) return false
          seen.add(key)

          // Filter out future release years
          const yr = parseInt(m.year || '0', 10)
          if (yr > currentYear) return false
          if (m.release_date && new Date(m.release_date) > today) return false

          return true
        })

        if (valid.length > 0 && isMounted) {
          const formatted = valid.slice(0, 6).map((m) => {
            const releaseYear = m.year || (m.release_date ? m.release_date.split('-')[0] : '2024')
            const displayRating = m.rating ? Number(m.rating).toFixed(1) : '8.4'
            const genresList = m.genres && m.genres.length > 0 ? m.genres : ['Action', 'Thriller', 'Sci-Fi']

            return {
              id: m.tmdb_id || m.title,
              title: m.title,
              searchQuery: m.title,
              synopsis: m.overview || 'Newly released blockbuster streaming in ultra high definition with multi-audio on Cineforge.',
              year: releaseYear,
              rating: displayRating,
              certificate: 'U/A 16+',
              quality: '4K ULTRA HD',
              audio: 'Dolby Atmos 5.1',
              duration: '2h 15min',
              genres: genresList,
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

  // Auto-slide carousel every 8 seconds
  useEffect(() => {
    if (movies.length <= 1) return

    timerRef.current = setInterval(() => {
      setCurrentIndex((prev) => (prev + 1) % movies.length)
    }, 8000)

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

  const toggleWatchlist = (id) => {
    setWatchlist((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  // Skeleton loading placeholder
  if (isLoading || movies.length === 0) {
    return (
      <div className="hero-banner-container skeleton-hero-container">
        <div className="hero-overlay-top"></div>
        <div className="hero-overlay-radial"></div>
        <div className="hero-overlay-linear"></div>
        <div className="hero-content" style={{ opacity: 0.6 }}>
          <div className="hero-meta-top">
            <span className="badge badge-spotlight animate-pulse">
              <Loader2 size={13} className="animate-spin" /> DISCOVERING SPOTLIGHT CINEMA...
            </span>
          </div>
          <div style={{ height: '48px', width: '380px', background: 'rgba(255,255,255,0.08)', borderRadius: '8px', margin: '16px 0' }} className="skeleton"></div>
          <div style={{ height: '24px', width: '260px', background: 'rgba(255,255,255,0.05)', borderRadius: '6px', marginBottom: '16px' }} className="skeleton"></div>
          <div style={{ height: '60px', width: '500px', background: 'rgba(255,255,255,0.04)', borderRadius: '6px' }} className="skeleton"></div>
        </div>
      </div>
    )
  }

  const current = movies[currentIndex]
  const isCurrentInWatchlist = watchlist.has(current.id)

  return (
    <div className="hero-banner-container">
      {/* Dynamic TMDb Backdrop with Vignette Gradients */}
      <div
        className="hero-backdrop"
        key={current.id}
        style={{
          backgroundImage: `url(${current.backdrop})`,
        }}
      >
        {/* Top Dark Vignette: Completely eliminates bright backdrop glare behind navbar */}
        <div className="hero-overlay-top"></div>
        <div className="hero-overlay-radial"></div>
        <div className="hero-overlay-linear"></div>
      </div>

      {/* Hero Content */}
      <div className="hero-content">
        <div className="hero-meta-top">
          <span className="badge badge-spotlight">
            <Sparkles size={13} /> STREAM SPOTLIGHT
          </span>
          <span className="badge badge-quality">{current.quality}</span>
          {current.audio && <span className="badge badge-audio">{current.audio}</span>}
        </div>

        <h1 className="hero-title">{current.title}</h1>

        <div className="hero-stats">
          <div className="stat-rating">
            <Star size={16} fill="#FFD700" color="#FFD700" />
            <span>{current.rating}</span>
          </div>
          <span className="stat-dot">•</span>
          <span className="stat-certificate">{current.certificate || 'U/A 16+'}</span>
          <span className="stat-dot">•</span>
          <span className="stat-year">{current.year}</span>
          <span className="stat-dot">•</span>
          <span className="stat-duration">{current.duration}</span>
          <span className="stat-dot">•</span>
          <div className="stat-genres">
            {current.genres.map((g) => (
              <span key={g} className="badge badge-genre">
                {g}
              </span>
            ))}
          </div>
        </div>

        <p className="hero-synopsis">{current.synopsis}</p>

        <div className="hero-actions">
          <button
            className="btn btn-hero-play"
            onClick={() => onQuickPlay(current.searchQuery)}
            id="hero-play-btn"
          >
            <Play size={20} fill="#000000" />
            <span>Play Now</span>
          </button>

          <button
            className="btn btn-hero-watchlist"
            onClick={() => toggleWatchlist(current.id)}
            id="hero-watchlist-btn"
          >
            {isCurrentInWatchlist ? <Check size={18} className="text-success" /> : <Plus size={18} />}
            <span>{isCurrentInWatchlist ? 'In Watchlist' : 'Add to Watchlist'}</span>
          </button>

          <button
            className="btn-icon btn-hero-sound"
            onClick={() => setIsMuted(!isMuted)}
            title={isMuted ? 'Unmute' : 'Mute'}
          >
            {isMuted ? <VolumeX size={18} /> : <Volume2 size={18} />}
          </button>
        </div>
      </div>

      {/* Slide Navigation Controls */}
      <div className="hero-slider-controls">
        <button className="slider-btn" onClick={handlePrev} title="Previous" id="hero-prev-btn">
          <ChevronLeft size={20} />
        </button>
        <div className="slider-dots">
          {movies.map((item, idx) => (
            <button
              key={item.id}
              className={`dot ${idx === currentIndex ? 'active' : ''}`}
              onClick={() => setCurrentIndex(idx)}
              aria-label={`Go to slide ${idx + 1}`}
            />
          ))}
        </div>
        <button className="slider-btn" onClick={handleNext} title="Next" id="hero-next-btn">
          <ChevronRight size={20} />
        </button>
      </div>
    </div>
  )
}
