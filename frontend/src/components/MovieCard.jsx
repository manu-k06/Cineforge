import React, { useState, useEffect } from 'react'
import { Play, Film, HardDrive, Sparkles, Layers, Star, Plus, BookmarkCheck } from 'lucide-react'
import { parseMovieMetadata, getPosterGradient } from '../utils/helpers'
import { getMovieMetadata } from '../services/api'
import { useWatchHistory } from '../context/WatchHistoryContext'

export default function MovieCard({ group, metadata: initialMetadata, onSelect }) {
  const { isInWatchlist, toggleWatchlist } = useWatchHistory()
  // If grouped by title, group has { title, candidates }
  // Otherwise it's a single candidate
  const isGroup = Boolean(group.candidates && group.candidates.length > 0)
  const primaryCandidate = isGroup ? group.candidates[0] : group
  const releaseCount = isGroup ? group.candidates.length : 1

  const rawDetails = primaryCandidate.display_text || primaryCandidate.size || primaryCandidate.details || ''
  const meta = parseMovieMetadata(
    primaryCandidate.title || group.title,
    rawDetails
  )

  const [metadata, setMetadata] = useState(initialMetadata || group.metadata || null)
  const [imgLoaded, setImgLoaded] = useState(false)
  const [imgError, setImgError] = useState(false)

  // Synchronize or lazily enrich metadata if not passed from search_response
  useEffect(() => {
    if (initialMetadata) {
      setMetadata(initialMetadata)
      setImgError(false)
    } else if (!metadata && (group.title || primaryCandidate.title)) {
      const searchTitle = group.title || primaryCandidate.title
      getMovieMetadata(searchTitle, meta.year)
        .then((data) => {
          if (data && data.source !== 'fallback') {
            setMetadata(data)
          }
        })
        .catch(() => {
          // Graceful fallback: rely on gradient
        })
    }
  }, [initialMetadata, group.title, primaryCandidate.title, meta.year])

  const gradient = getPosterGradient(meta.cleanTitle)
  const displaySize = primaryCandidate.size || meta.fileSize
  const displayQuality = primaryCandidate.quality || meta.resolution
  const effectiveYear = metadata?.year || meta.year

  return (
    <div className="movie-card" onClick={() => onSelect(group)}>
      {/* Poster Image or Cinematic Generator */}
      <div className="movie-poster" style={{ background: gradient, position: 'relative', overflow: 'hidden' }}>
        {/* Real TMDb HD Poster Image */}
        {metadata?.poster_url && !imgError && (
          <img
            src={metadata.poster_url}
            alt={meta.cleanTitle}
            loading="lazy"
            onLoad={() => setImgLoaded(true)}
            onError={() => setImgError(true)}
            style={{
              position: 'absolute',
              inset: 0,
              width: '100%',
              height: '100%',
              objectFit: 'cover',
              opacity: imgLoaded ? 1 : 0,
              transition: 'opacity 0.35s ease',
              zIndex: 1,
            }}
          />
        )}

        {/* Top Badges */}
        <div className="poster-badges-top" style={{ zIndex: 2 }}>
          {metadata?.rating ? (
            <span
              className="badge badge-quality"
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '3px',
                backgroundColor: 'rgba(0,0,0,0.75)',
                border: '1px solid rgba(255,215,0,0.5)',
                color: '#FFD700',
              }}
            >
              <Star size={11} fill="#FFD700" color="#FFD700" /> {metadata.rating}
            </span>
          ) : (
            <span className="badge badge-quality">{displayQuality}</span>
          )}
          {releaseCount > 1 && (
            <span className="badge badge-red">
              <Layers size={11} /> {releaseCount} Releases
            </span>
          )}
        </div>

        {/* Poster Inner Art Graphic (Fallback while loading or if no poster) */}
        {(!imgLoaded || imgError || !metadata?.poster_url) && (
          <div className="poster-inner-art" style={{ zIndex: 1 }}>
            <Film size={36} className="poster-icon" />
            <span className="poster-display-title">{meta.cleanTitle}</span>
            {effectiveYear && <span className="poster-display-year">{effectiveYear}</span>}
          </div>
        )}

        {/* Hover Overlay with Glow Play Icon */}
        <div className="poster-hover-overlay" style={{ zIndex: 3 }}>
          <div className="play-button-glow">
            <Play size={24} fill="#FFFFFF" color="#FFFFFF" />
          </div>
          <span className="hover-cta-text">
            {releaseCount > 1 ? 'Choose Version' : 'Stream Now'}
          </span>

          {/* Quick Watchlist Bookmark Button */}
          <button
            className={`card-watchlist-btn ${isInWatchlist(meta.cleanTitle || group.title) ? 'active' : ''}`}
            onClick={(e) => {
              e.stopPropagation()
              toggleWatchlist({
                title: meta.cleanTitle || group.title,
                clean_title: meta.cleanTitle,
                year: effectiveYear,
                rating: metadata?.rating || null,
                poster_url: metadata?.poster_url || null,
                backdrop_url: metadata?.backdrop_url || null,
                overview: metadata?.overview || null,
                genres: metadata?.genres || [],
              })
            }}
            title={isInWatchlist(meta.cleanTitle || group.title) ? 'Remove from My List' : 'Add to My List'}
          >
            {isInWatchlist(meta.cleanTitle || group.title) ? (
              <BookmarkCheck size={16} fill="#E50000" color="#E50000" />
            ) : (
              <Plus size={16} color="#FFFFFF" />
            )}
          </button>
        </div>
      </div>

      {/* Card Info Details */}
      <div className="movie-info">
        <h3 className="movie-title" title={primaryCandidate.title || group.title}>
          {meta.cleanTitle}
        </h3>

        <div className="movie-meta-row">
          {effectiveYear && <span className="movie-year">{effectiveYear}</span>}
          {displaySize && (
            <>
              {effectiveYear && <span className="meta-sep">•</span>}
              <span className="movie-size">
                <HardDrive size={12} className="icon-size" /> {displaySize}
              </span>
            </>
          )}
        </div>

        {/* Quality and Audio Tags + TMDb Genres */}
        <div className="movie-tags">
          {metadata?.genres?.slice(0, 2).map((genre) => (
            <span
              key={genre}
              className="badge badge-sm"
              style={{ backgroundColor: 'rgba(255, 255, 255, 0.08)', color: '#e2e8f0' }}
            >
              {genre}
            </span>
          ))}
          {primaryCandidate.container && (
            <span className="badge badge-sm">{primaryCandidate.container.toUpperCase()}</span>
          )}
          {primaryCandidate.language && (
            <span className="badge badge-sm">{primaryCandidate.language}</span>
          )}
          {meta.tags.slice(0, 2).map((tag) => (
            <span key={tag} className="badge badge-sm">
              {tag}
            </span>
          ))}
        </div>
      </div>
    </div>
  )
}
