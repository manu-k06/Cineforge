import React, { useState, useEffect } from 'react'
import { Film } from 'lucide-react'
import { parseMovieMetadata, getPosterGradient } from '../utils/helpers'
import { getMovieMetadata } from '../services/api'
import { useWatchHistory } from '../context/WatchHistoryContext'

export default function MovieCard({ group, metadata: initialMetadata, rank = null, onSelect }) {
  const { isInWatchlist, toggleWatchlist } = useWatchHistory()
  
  const isGroup = Boolean(group?.candidates && group.candidates.length > 0)
  const primaryCandidate = isGroup ? group.candidates[0] : (group || {})

  const rawDetails = primaryCandidate.display_text || primaryCandidate.size || primaryCandidate.details || ''
  const meta = parseMovieMetadata(
    primaryCandidate.title || group?.title || '',
    rawDetails
  )

  const [metadata, setMetadata] = useState(initialMetadata || group?.metadata || null)
  const [imgLoaded, setImgLoaded] = useState(false)
  const [imgError, setImgError] = useState(false)

  useEffect(() => {
    if (initialMetadata) {
      setMetadata(initialMetadata)
      setImgError(false)
    } else if (!metadata && (group?.title || primaryCandidate.title)) {
      const searchTitle = group?.title || primaryCandidate.title
      getMovieMetadata(searchTitle, meta.year)
        .then((data) => {
          if (data && data.source !== 'fallback') {
            setMetadata(data)
          }
        })
        .catch(() => {})
    }
  }, [initialMetadata, group?.title, primaryCandidate.title, meta.year])

  const posterSrc = metadata?.poster_url || primaryCandidate?.poster_url || null
  const effectiveYear = metadata?.year || meta.year || '2025'
  const displayRating = metadata?.rating ? Number(metadata.rating).toFixed(1) : (primaryCandidate.quality || 'HD')
  const mediaType = metadata?.media_type === 'tv' ? 'TV' : 'Movie'
  const cleanTitle = meta.cleanTitle || group?.title || primaryCandidate.title || 'Untitled'
  const isSaved = isInWatchlist(cleanTitle)

  const handleWatchlistClick = (e) => {
    e.stopPropagation()
    toggleWatchlist({
      title: cleanTitle,
      clean_title: cleanTitle,
      year: effectiveYear,
      rating: metadata?.rating || null,
      poster_url: posterSrc,
      backdrop_url: metadata?.backdrop_url || null,
      overview: metadata?.overview || null,
      genres: metadata?.genres || [],
    })
  }

  return (
    <article
      className="poster-card"
      onClick={() => onSelect(group)}
      title={cleanTitle}
    >
      {/* Poster Image */}
      {posterSrc && !imgError ? (
        <img
          src={posterSrc}
          alt={cleanTitle}
          loading="lazy"
          onLoad={() => setImgLoaded(true)}
          onError={() => setImgError(true)}
          style={{
            opacity: imgLoaded ? 1 : 0,
            transition: 'opacity 0.24s ease',
          }}
        />
      ) : (
        <div
          className="poster-fallback"
          style={{ background: getPosterGradient(cleanTitle) }}
        >
          <Film size={32} opacity={0.3} />
          <span className="poster-fallback-title">{cleanTitle}</span>
        </div>
      )}

      {/* Cineby Signature Red Rank Badge (TOP 01, TOP 02, etc.) */}
      {rank !== null && rank !== undefined && (
        <b className="rank-badge">
          TOP<br />
          {String(rank).padStart(2, '0')}
        </b>
      )}

      {/* Gradient Vignette at Bottom */}
      <span className="poster-shade" />

      {/* Title & Metadata Line */}
      <span className="card-copy">
        <strong>{cleanTitle}</strong>
        <small>
          {displayRating} · {effectiveYear} · {mediaType}
        </small>
      </span>

      {/* Hover Action: Quick Add / Remove Watchlist */}
      <div className="card-hover-actions">
        <button
          type="button"
          className="card-action-btn"
          onClick={handleWatchlistClick}
          title={isSaved ? 'In Watchlist' : 'Add to Watchlist'}
          aria-label={isSaved ? 'Remove from Watchlist' : 'Add to Watchlist'}
        >
          {isSaved ? '✓' : '＋'}
        </button>
      </div>
    </article>
  )
}
