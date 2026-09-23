import React, { useState, useEffect, useRef } from 'react'
import { Play, Plus, Check, Star, ChevronLeft, ChevronRight, Volume2, VolumeX, Sparkles, Loader2, Info } from 'lucide-react'
import { getPopularMovies, getTrendingMovies } from '../services/api'
import { useWatchHistory } from '../context/WatchHistoryContext'

export default function HeroBanner({ onQuickPlay }) {
  const { isInWatchlist, toggleWatchlist } = useWatchHistory()
  const [movies, setMovies] = useState([])
  const [isLoading, setIsLoading] = useState(true)
  const [currentIndex, setCurrentIndex] = useState(0)
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
          const formatted = valid.slice(0, 6).map((m, idx) => {
            const releaseYear = m.year || (m.release_date ? m.release_date.split('-')[0] : '2024')
            const displayRating = m.rating ? Number(m.rating).toFixed(1) : '8.4'
            const matchScore = Math.min(99, Math.max(92, Math.round(Number(displayRating) * 10 + (idx % 3) * 2)))
            const genresList = m.genres && m.genres.length > 0 ? m.genres : ['Action', 'Thriller', 'Sci-Fi']

            return {
              id: m.tmdb_id || m.title,
              title: m.title,
              searchQuery: m.title,
              synopsis: m.overview || 'Newly released blockbuster streaming in ultra high definition with multi-audio on Cineforge.',
              year: releaseYear,
              rating: displayRating,
              matchScore: `${matchScore}% Match`,
              certificate: 'U/A 16+',
              quality: '4K UHD',
              audio: 'Dolby Atmos',
              duration: '2h 15m',
              genres: genresList,
              backdrop: m.backdrop_url,
              poster_url: m.poster_url || null,
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

  // Skeleton loading placeholder
  if (isLoading || movies.length === 0) {
    return (
      <div className="hero-banner-container skeleton-hero-container">
        <div className="hero-overlay-radial"></div>
        <div className="hero-overlay-linear"></div>
        <div className="hero-content" style={{ opacity: 0.6 }}>
          <div className="hero-meta-top">
            <span className="badge badge-spotlight animate-pulse">
              <Loader2 size={13} className="animate-spin" /> SPOTLIGHT CINEMA...
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
  const isSaved = isInWatchlist(current.title)

  const handleToggleWatchlist = () => {
    toggleWatchlist({
      title: current.title,
      clean_title: current.title,
      year: current.year,
      rating: current.rating,
      poster_url: current.poster_url,
      backdrop_url: current.backdrop,
      overview: current.synopsis,
      genres: current.genres,
    })
  }

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
        <div className="hero-overlay-radial"></div>
        <div className="hero-overlay-linear"></div>
      </div>

      {/* Hero Content */}
      <div className="hero-content">
        {/* OTT Spotlight Tag */}
        <div className="hero-meta-top">
          <span className="ott-spotlight-pill">
            <Sparkles size={13} className="text-primary" />
            <span>FEATURED SPOTLIGHT</span>
          </span>
        </div>

        <h1 className="hero-title">{current.title}</h1>

        {/* Netflix/Apple TV Style Metadata Badges */}
        <div className="hero-stats">
          <span className="ott-match-score">{current.matchScore}</span>
          <span className="stat-dot">•</span>
          <span className="stat-year">{current.year}</span>
          <span className="stat-dot">•</span>
          <span className="ott-cert-badge">{current.certificate || 'PG-13'}</span>
          <span className="stat-dot">•</span>
          <span className="stat-duration">{current.duration}</span>
          <span className="stat-dot">•</span>
          <span className="ott-tech-badge">{current.quality}</span>
          <span className="ott-tech-badge">{current.audio}</span>
        </div>

        <p className="hero-synopsis">{current.synopsis}</p>

        {/* Cinematic Action Buttons */}
        <div className="hero-actions">
          <button
            className="btn btn-hero-play"
            onClick={() => onQuickPlay(current.searchQuery)}
            id="hero-play-btn"
          >
            <Play size={20} fill="#000000" color="#000000" className="translate-play" />
            <span>Play Now</span>
          </button>

          <button
            className={`btn btn-hero-watchlist ${isSaved ? 'in-watchlist' : ''}`}
            onClick={handleToggleWatchlist}
            id="hero-watchlist-btn"
          >
            {isSaved ? <Check size={18} className="text-primary" /> : <Plus size={18} />}
            <span>{isSaved ? 'In My List' : 'Add to My List'}</span>
          </button>

          <button
            className="btn btn-hero-info"
            onClick={() => onQuickPlay(current.searchQuery)}
            title="More Details & Versions"
          >
            <Info size={18} />
            <span>More Info</span>
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
