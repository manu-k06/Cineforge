import React, { useRef } from 'react'
import { Play, X, ChevronLeft, ChevronRight, Clock, Film } from 'lucide-react'

export default function ContinueWatchingRail({ items = [], onResume, onRemove }) {
  const scrollRef = useRef(null)

  if (!items || items.length === 0) return null

  const scroll = (direction) => {
    if (!scrollRef.current) return
    const amount = direction === 'left' ? -600 : 600
    scrollRef.current.scrollBy({ left: amount, behavior: 'smooth' })
  }

  // Format remaining time nicely (e.g., "45m left", "1h 12m left")
  const formatRemainingTime = (progressSec, durationSec) => {
    if (!durationSec || durationSec <= 0 || progressSec >= durationSec) {
      return `${Math.round(progressSec / 60)}m watched`
    }
    const rem = durationSec - progressSec
    const h = Math.floor(rem / 3600)
    const m = Math.floor((rem % 3600) / 60)
    if (h > 0) {
      return `${h}h ${m}m left`
    }
    return `${Math.max(1, m)}m left`
  }

  return (
    <section className="continue-watching-section">
      <div className="continue-watching-header">
        <div className="section-title-wrapper">
          <div className="section-indicator-dot" />
          <h2 className="continue-watching-title">Continue Watching</h2>
          <span className="continue-watching-count">{items.length} in progress</span>
        </div>

        {items.length > 3 && (
          <div className="rail-nav-controls">
            <button
              className="rail-nav-btn"
              onClick={() => scroll('left')}
              title="Scroll left"
            >
              <ChevronLeft size={18} />
            </button>
            <button
              className="rail-nav-btn"
              onClick={() => scroll('right')}
              title="Scroll right"
            >
              <ChevronRight size={18} />
            </button>
          </div>
        )}
      </div>

      <div className="continue-watching-carousel" ref={scrollRef}>
        {items.map((item) => {
          const progressPercent = item.duration_seconds > 0
            ? Math.min(100, Math.round((item.progress_seconds / item.duration_seconds) * 100))
            : item.progress_percent || 0
          const remainingText = formatRemainingTime(item.progress_seconds, item.duration_seconds)
          const thumbUrl = item.backdrop_url || item.poster_url

          return (
            <div
              key={item.title}
              className="continue-watching-card"
              onClick={() => onResume(item)}
            >
              <div className="continue-thumbnail-box">
                {thumbUrl ? (
                  <img
                    src={thumbUrl}
                    alt={item.clean_title || item.title}
                    className="continue-thumb-img"
                    loading="lazy"
                  />
                ) : (
                  <div className="continue-thumb-fallback">
                    <Film size={32} className="text-secondary" />
                    <span>{item.clean_title || item.title}</span>
                  </div>
                )}

                {/* Dismiss Button */}
                <button
                  className="continue-dismiss-btn"
                  onClick={(e) => {
                    e.stopPropagation()
                    onRemove(item.title)
                  }}
                  title="Remove from Continue Watching"
                >
                  <X size={14} />
                </button>

                {/* Remaining Time Badge */}
                <div className="continue-time-badge">
                  <Clock size={11} />
                  <span>{remainingText}</span>
                </div>

                {/* Play Hover Overlay */}
                <div className="continue-hover-overlay">
                  <div className="continue-play-circle">
                    <Play size={20} fill="#FFFFFF" color="#FFFFFF" className="translate-play" />
                  </div>
                  <span className="continue-resume-label">Resume</span>
                </div>

                {/* Glowing Red Progress Track along bottom */}
                <div className="continue-progress-bar-container">
                  <div
                    className="continue-progress-bar-fill"
                    style={{ width: `${Math.max(5, progressPercent)}%` }}
                  />
                </div>
              </div>

              {/* Title & Metadata row */}
              <div className="continue-card-meta">
                <h4 className="continue-movie-title" title={item.title}>
                  {item.clean_title || item.title}
                </h4>
                <div className="continue-movie-sub">
                  {item.year && <span className="continue-movie-year">{item.year}</span>}
                  {item.quality && (
                    <>
                      <span className="continue-meta-sep">•</span>
                      <span className="continue-movie-quality">{item.quality}</span>
                    </>
                  )}
                  <span className="continue-meta-sep">•</span>
                  <span className="continue-progress-text">{progressPercent}%</span>
                </div>
              </div>
            </div>
          )
        })}
      </div>
    </section>
  )
}
