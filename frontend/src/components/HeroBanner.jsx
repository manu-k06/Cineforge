import React, { useState } from 'react'
import { Play, Plus, Check, Star, ChevronLeft, ChevronRight, Volume2, VolumeX, Sparkles } from 'lucide-react'

const FEATURED_MOVIES = [
  {
    id: 'avengers',
    title: 'Avengers: Endgame',
    searchQuery: 'Avengers Endgame',
    synopsis: 'After the devastating events of Infinity War, the universe is in ruins. With the help of remaining allies, the Avengers assemble once more to reverse Thanos’ actions and restore balance.',
    year: '2019',
    rating: '8.4',
    quality: '4K UHD',
    duration: '3h 1min',
    genres: ['Action', 'Sci-Fi', 'Adventure'],
    backdrop: 'https://images.unsplash.com/photo-1534447677768-be436bb09401?q=80&w=1920&auto=format&fit=crop',
  },
  {
    id: 'dune',
    title: 'Dune: Part Two',
    searchQuery: 'Dune Part Two',
    synopsis: 'Paul Atreides unites with Chani and the Fremen while seeking revenge against the conspirators who destroyed his family. Facing a choice between the love of his life and the fate of the universe.',
    year: '2024',
    rating: '8.6',
    quality: '4K UHD',
    duration: '2h 46min',
    genres: ['Sci-Fi', 'Adventure', 'Drama'],
    backdrop: 'https://images.unsplash.com/photo-1509198397868-475647b2a1e5?q=80&w=1920&auto=format&fit=crop',
  },
  {
    id: 'interstellar',
    title: 'Interstellar',
    searchQuery: 'Interstellar',
    synopsis: 'When Earth becomes uninhabitable in the future, a farmer and ex-NASA pilot, Joseph Cooper, is tasked to pilot a spacecraft along with a team of researchers to find a new planet for humans.',
    year: '2014',
    rating: '8.7',
    quality: 'IMAX 4K',
    duration: '2h 49min',
    genres: ['Sci-Fi', 'Drama', 'Mystery'],
    backdrop: 'https://images.unsplash.com/photo-1451187580459-43490279c0fa?q=80&w=1920&auto=format&fit=crop',
  },
]

export default function HeroBanner({ onQuickPlay }) {
  const [currentIndex, setCurrentIndex] = useState(0)
  const [isWatchlist, setIsWatchlist] = useState(false)
  const [isMuted, setIsMuted] = useState(true)

  const current = FEATURED_MOVIES[currentIndex]

  const handleNext = () => {
    setCurrentIndex((prev) => (prev + 1) % FEATURED_MOVIES.length)
  }

  const handlePrev = () => {
    setCurrentIndex((prev) => (prev - 1 + FEATURED_MOVIES.length) % FEATURED_MOVIES.length)
  }

  return (
    <div className="hero-banner-container">
      {/* Background with vignette gradients */}
      <div 
        className="hero-backdrop"
        style={{ backgroundImage: `url(${current.backdrop})` }}
      >
        <div className="hero-overlay-radial"></div>
        <div className="hero-overlay-linear"></div>
      </div>

      {/* Hero Content */}
      <div className="hero-content">
        <div className="hero-meta-top">
          <span className="badge badge-red">
            <Sparkles size={13} /> STREAMVIBE SPOTLIGHT
          </span>
          <span className="badge badge-quality">{current.quality}</span>
        </div>

        <h1 className="hero-title">{current.title}</h1>

        <div className="hero-stats">
          <div className="stat-rating">
            <Star size={16} fill="#FFD700" color="#FFD700" />
            <span>{current.rating}</span>
          </div>
          <span className="stat-dot">•</span>
          <span className="stat-year">{current.year}</span>
          <span className="stat-dot">•</span>
          <span className="stat-duration">{current.duration}</span>
          <span className="stat-dot">•</span>
          <div className="stat-genres">
            {current.genres.map((g) => (
              <span key={g} className="badge">{g}</span>
            ))}
          </div>
        </div>

        <p className="hero-synopsis">{current.synopsis}</p>

        <div className="hero-actions">
          <button 
            className="btn btn-primary btn-hero-play"
            onClick={() => onQuickPlay(current.searchQuery)}
          >
            <Play size={18} fill="#FFFFFF" />
            <span>Play Now</span>
          </button>

          <button 
            className="btn btn-secondary"
            onClick={() => setIsWatchlist(!isWatchlist)}
          >
            {isWatchlist ? <Check size={18} className="text-success" /> : <Plus size={18} />}
            <span>{isWatchlist ? 'In Watchlist' : 'Add to Watchlist'}</span>
          </button>

          <button 
            className="btn-icon" 
            onClick={() => setIsMuted(!isMuted)} 
            title={isMuted ? 'Unmute preview' : 'Mute preview'}
          >
            {isMuted ? <VolumeX size={18} /> : <Volume2 size={18} />}
          </button>
        </div>
      </div>

      {/* Slide Navigation Controls */}
      <div className="hero-slider-controls">
        <button className="slider-btn" onClick={handlePrev} title="Previous">
          <ChevronLeft size={20} />
        </button>
        <div className="slider-dots">
          {FEATURED_MOVIES.map((item, idx) => (
            <button
              key={item.id}
              className={`dot ${idx === currentIndex ? 'active' : ''}`}
              onClick={() => setCurrentIndex(idx)}
            />
          ))}
        </div>
        <button className="slider-btn" onClick={handleNext} title="Next">
          <ChevronRight size={20} />
        </button>
      </div>
    </div>
  )
}
