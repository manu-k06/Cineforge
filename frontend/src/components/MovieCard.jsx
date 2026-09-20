import React from 'react'
import { Play, Film, HardDrive, Sparkles, Layers } from 'lucide-react'
import { parseMovieMetadata, getPosterGradient } from '../utils/helpers'

export default function MovieCard({ group, onSelect }) {
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

  const gradient = getPosterGradient(meta.cleanTitle)
  const displaySize = primaryCandidate.size || meta.fileSize
  const displayQuality = primaryCandidate.quality || meta.resolution

  return (
    <div className="movie-card" onClick={() => onSelect(group)}>
      {/* Poster Image or Cinematic Generator */}
      <div className="movie-poster" style={{ background: gradient }}>
        {/* Top Badges */}
        <div className="poster-badges-top">
          <span className="badge badge-quality">{displayQuality}</span>
          {releaseCount > 1 && (
            <span className="badge badge-red">
              <Layers size={11} /> {releaseCount} Releases
            </span>
          )}
        </div>

        {/* Poster Content Graphic */}
        <div className="poster-inner-art">
          <Film size={36} className="poster-icon" />
          <span className="poster-display-title">{meta.cleanTitle}</span>
          {meta.year && <span className="poster-display-year">{meta.year}</span>}
        </div>

        {/* Hover Overlay with Glow Play Icon */}
        <div className="poster-hover-overlay">
          <div className="play-button-glow">
            <Play size={24} fill="#FFFFFF" color="#FFFFFF" />
          </div>
          <span className="hover-cta-text">
            {releaseCount > 1 ? 'Choose Version' : 'Stream Now'}
          </span>
        </div>
      </div>

      {/* Card Info Details */}
      <div className="movie-info">
        <h3 className="movie-title" title={primaryCandidate.title || group.title}>
          {meta.cleanTitle}
        </h3>

        <div className="movie-meta-row">
          {meta.year && <span className="movie-year">{meta.year}</span>}
          {displaySize && (
            <>
              {meta.year && <span className="meta-sep">•</span>}
              <span className="movie-size">
                <HardDrive size={12} className="icon-size" /> {displaySize}
              </span>
            </>
          )}
        </div>

        {/* Quality and Audio Tags */}
        <div className="movie-tags">
          {primaryCandidate.container && (
            <span className="badge badge-sm">{primaryCandidate.container.toUpperCase()}</span>
          )}
          {primaryCandidate.language && (
            <span className="badge badge-sm">{primaryCandidate.language}</span>
          )}
          {meta.tags.map((tag) => (
            <span key={tag} className="badge badge-sm">
              {tag}
            </span>
          ))}
          {!displaySize && rawDetails && (
            <span className="candidate-details-snippet" title={rawDetails}>
              {rawDetails.slice(0, 35)}...
            </span>
          )}
        </div>
      </div>
    </div>
  )
}
