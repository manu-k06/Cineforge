import React, { useState } from 'react'
import { Play, Plus, Check, Star, ChevronLeft, ChevronRight, Volume2, VolumeX, Sparkles } from 'lucide-react'

const FEATURED_MOVIES = [
  {
    id: 'avengers',
    title: 'Avengers: Endgame',
    searchQuery: 'Avengers Endgame',
    synopsis: 'After the devastating events of Infinity War, the universe is in ruins. With the help of remaining allies, the Avengers assemble once more to reverse Thanos’ actions and restore balance to the universe.',
    year: '2019',
    rating: '8.4',
    certificate: 'U/A 16+',
    quality: '4K ULTRA HD',
    audio: 'Dolby Atmos 5.1',
    duration: '3h 1min',
    genres: ['Action', 'Sci-Fi', 'Adventure'],
    backdrop: 'https://image.tmdb.org/t/p/original/7RyHsO4yDXtBv1zUU3mTpHeQ0d5.jpg',
  },
  {
    id: 'dune',
    title: 'Dune: Part Two',
    searchQuery: 'Dune Part Two',
    synopsis: 'Paul Atreides unites with Chani and the Fremen while seeking revenge against the conspirators who destroyed his family. Facing a choice between the love of his life and the fate of the universe.',
    year: '2024',
    rating: '8.6',
    certificate: 'U/A 16+',
    quality: '4K ULTRA HD',
    audio: 'IMAX Enhanced',
    duration: '2h 46min',
    genres: ['Sci-Fi', 'Adventure', 'Drama'],
    backdrop: 'https://image.tmdb.org/t/p/original/xOMo8BRK7PfcJv9JCnx7s520DRq.jpg',
  },
  {
    id: 'interstellar',
    title: 'Interstellar',
    searchQuery: 'Interstellar',
    synopsis: 'When Earth becomes uninhabitable in the future, a farmer and ex-NASA pilot, Joseph Cooper, is tasked to pilot a spacecraft along with a team of researchers to find a new planet for humanity.',
    year: '2014',
    rating: '8.7',
    certificate: 'U/A 13+',
    quality: 'IMAX 4K',
    audio: 'DTS-HD MA 5.1',
    duration: '2h 49min',
    genres: ['Sci-Fi', 'Drama', 'Adventure'],
    backdrop: 'https://image.tmdb.org/t/p/original/rAiYTsqJJR0KP8UN8vJjZHa820g.jpg',
  },
  {
    id: 'aavesham',
    title: 'Aavesham',
    searchQuery: 'Aavesham',
    synopsis: 'Three teenagers arrive in Bangalore for their engineering degree and get involved in a brawl with seniors. In pursuit of protection, they find an eccentric local gangster named Ranga.',
    year: '2024',
    rating: '8.0',
    certificate: 'U/A 16+',
    quality: '1080p FULL HD',
    audio: 'Dual Audio (Malayalam / Hindi)',
    duration: '2h 38min',
    genres: ['Action', 'Comedy', 'Drama'],
    backdrop: 'https://image.tmdb.org/t/p/original/w4z8jY8L21F7sC8r41X1W42R.jpg',
  },
  {
    id: 'oppenheimer',
    title: 'Oppenheimer',
    searchQuery: 'Oppenheimer',
    synopsis: 'The story of American scientist J. Robert Oppenheimer and his role in the development of the atomic bomb during World War II.',
    year: '2023',
    rating: '8.9',
    certificate: 'A 18+',
    quality: '4K ULTRA HD',
    audio: 'Dolby Atmos',
    duration: '3h 0min',
    genres: ['Biography', 'Drama', 'History'],
    backdrop: 'https://image.tmdb.org/t/p/original/fm6K9vY92Yr8zbivvgMcq9xYvYw.jpg',
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
              <span key={g} className="badge badge-genre">{g}</span>
            ))}
          </div>
        </div>

        <p className="hero-synopsis">{current.synopsis}</p>

        <div className="hero-actions">
          <button 
            className="btn btn-hero-play"
            onClick={() => onQuickPlay(current.searchQuery)}
          >
            <Play size={20} fill="#000000" />
            <span>Play Now</span>
          </button>

          <button 
            className="btn btn-hero-watchlist"
            onClick={() => setIsWatchlist(!isWatchlist)}
          >
            {isWatchlist ? <Check size={18} className="text-success" /> : <Plus size={18} />}
            <span>{isWatchlist ? 'In Watchlist' : 'Add to Watchlist'}</span>
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
