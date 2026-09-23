import React, { useEffect, useState, useMemo } from 'react'
import { Sparkles, Film, Volume2, ShieldCheck, X, AlertTriangle, RefreshCw, Clapperboard, Lightbulb } from 'lucide-react'
import { getMovieTrivia, CINEMA_CALIBRATION_STEPS } from '../utils/movieTrivia'
import { parseMovieMetadata } from '../utils/helpers'

export default function DeliveryModal({ candidate, metadata, error, onClose, onRetry }) {
  const [elapsedTime, setElapsedTime] = useState(0)
  const [progress, setProgress] = useState(15)
  const [triviaIndex, setTriviaIndex] = useState(0)

  const meta = useMemo(() => {
    return parseMovieMetadata(candidate?.title || '', candidate?.display_text || '')
  }, [candidate])

  const movieTitle = metadata?.title || meta.cleanTitle || candidate?.title || 'Featured Film'
  const movieYear = metadata?.year || meta.year || ''
  const backdropUrl = metadata?.backdrop_url || metadata?.poster_url || null

  // Fetch or generate rich trivia for this film
  const triviaFact = useMemo(() => {
    return getMovieTrivia(movieTitle, metadata?.overview || '')
  }, [movieTitle, metadata])

  // Progress simulation & elapsed time timer
  useEffect(() => {
    const timer = setInterval(() => {
      setElapsedTime((prev) => prev + 1)
      setProgress((prev) => {
        if (prev < 90) return prev + Math.floor(Math.random() * 14 + 8)
        return prev
      })
    }, 1000)
    return () => clearInterval(timer)
  }, [])

  // Calibration step calculation
  const currentStep = useMemo(() => {
    if (elapsedTime <= 1) return CINEMA_CALIBRATION_STEPS[0]
    if (elapsedTime <= 2) return CINEMA_CALIBRATION_STEPS[1]
    if (elapsedTime <= 4) return CINEMA_CALIBRATION_STEPS[2]
    if (elapsedTime <= 6) return CINEMA_CALIBRATION_STEPS[3]
    return CINEMA_CALIBRATION_STEPS[4]
  }, [elapsedTime])

  return (
    <div className="preshow-modal-overlay">
      {/* Ambient Blurred Backdrop */}
      {backdropUrl && (
        <div
          className="preshow-ambient-backdrop"
          style={{ backgroundImage: `url(${backdropUrl})` }}
        />
      )}
      <div className="preshow-backdrop-vignette" />

      {/* Main Pre-Show Theater Card */}
      <div className="preshow-card animate-fade-in">
        {/* Top Header Row */}
        <div className="preshow-top-bar">
          <div className="preshow-pill-badge">
            <Clapperboard size={13} className="text-primary" />
            <span>CINEMA PRE-SHOW</span>
          </div>

          <button
            className="preshow-close-btn"
            onClick={onClose}
            title="Cancel and close"
          >
            <X size={18} />
          </button>
        </div>

        {/* Film Title & Metadata Badges */}
        <div className="preshow-film-header">
          <h2 className="preshow-film-title">{movieTitle}</h2>
          <div className="preshow-meta-chips">
            {movieYear && <span className="preshow-chip">{movieYear}</span>}
            <span className="preshow-chip chip-quality">{candidate?.quality || '1080P'}</span>
            <span className="preshow-chip chip-audio">
              <Volume2 size={12} /> Dolby Audio
            </span>
            {candidate?.size && <span className="preshow-chip">{candidate.size}</span>}
          </div>
        </div>

        {/* 💡 DID YOU KNOW? Trivia Feature Card */}
        {!error && (
          <div className="preshow-trivia-box">
            <div className="trivia-header-row">
              <div className="trivia-badge">
                <Lightbulb size={14} className="trivia-bulb-icon" />
                <span>DID YOU KNOW?</span>
              </div>
              <span className="trivia-sub-badge">Cinema Trivia</span>
            </div>
            <p className="trivia-body-text">{triviaFact}</p>
          </div>
        )}

        {/* Laser Cinema Stream Calibration Bar */}
        {!error ? (
          <div className="preshow-calibration-box">
            <div className="calibration-status-row">
              <span className="calibration-step-text">
                <Sparkles size={14} className="spin-icon text-primary" />
                {currentStep}
              </span>
              <span className="calibration-percentage">{Math.min(98, progress)}%</span>
            </div>

            <div className="calibration-progress-track">
              <div
                className="calibration-progress-fill"
                style={{ width: `${Math.min(98, progress)}%` }}
              />
            </div>

            <div className="preshow-footer-tip">
              <span>Optimizing high-bitrate video stream • Ready in moments</span>
            </div>
          </div>
        ) : (
          /* Error State Recovery */
          <div className="preshow-error-card">
            <div className="preshow-error-icon">
              <AlertTriangle size={28} />
            </div>
            <div className="preshow-error-content">
              <h4>Playback Initialization Paused</h4>
              <p>{error || 'The cinema stream node is busy. You can retry or choose an alternative release.'}</p>
            </div>
            <div className="preshow-error-actions">
              <button className="btn btn-secondary btn-sm" onClick={onClose}>
                Choose Another Release
              </button>
              {onRetry && (
                <button className="btn btn-primary btn-sm" onClick={onRetry}>
                  <RefreshCw size={14} /> Retry Playback
                </button>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
