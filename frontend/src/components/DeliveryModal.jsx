import React, { useEffect, useState } from 'react'
import { Loader2, AlertTriangle, Sparkles, Lightbulb, Play, Film, CheckCircle2 } from 'lucide-react'

const CINEMA_TRIVIA = [
  "Did you know? 'Oppenheimer' was shot using 65mm IMAX black-and-white film invented specifically for the movie.",
  "Did you know? 'Interstellar' physicist Kip Thorne's equations led to genuine astrophysics discoveries about gravitational lensing.",
  "Did you know? In 'The Dark Knight', Heath Ledger designed the Joker's messy makeup himself using drugstore cosmetics.",
  "Did you know? 'Manjummel Boys' became the first Malayalam movie in history to cross ₹240 crore worldwide.",
  "Did you know? In 'Dune: Part Two', Denis Villeneuve and sound designers recorded real desert tremors to simulate sandworms.",
  "Did you know? In 'Inception', the hallway fight scene was shot inside a real 100-foot rotating centrifuge set.",
  "Did you know? 'Aavesham' director Jithu Madhavan based Ranga's iconic eccentric personality on real college urban legends.",
]

export default function DeliveryModal({ candidate, error, onClose, onRetry }) {
  const [elapsedTime, setElapsedTime] = useState(0)
  const [triviaIndex, setTriviaIndex] = useState(0)

  // Timer
  useEffect(() => {
    const timer = setInterval(() => {
      setElapsedTime((prev) => prev + 1)
    }, 1000)
    return () => clearInterval(timer)
  }, [])

  // Rotate trivia every 3 seconds
  useEffect(() => {
    const triviaTimer = setInterval(() => {
      setTriviaIndex((prev) => (prev + 1) % CINEMA_TRIVIA.length)
    }, 3200)
    return () => clearInterval(triviaTimer)
  }, [])

  const currentFact = CINEMA_TRIVIA[triviaIndex]

  return (
    <div className="delivery-modal-backdrop" onClick={onClose} role="dialog" aria-modal="true">
      <div className="delivery-modal-card" onClick={(e) => e.stopPropagation()}>
        {/* Header */}
        <div className="delivery-modal-header">
          <div className="delivery-ring-glow">
            <Loader2 size={36} className="animate-spin text-ember" />
          </div>
          <h3 className="delivery-modal-title">Preparing Cinema Stream</h3>
          <p className="delivery-modal-subtitle">
            Allocating stream bandwidth and syncing multi-channel audio tracks...
          </p>
        </div>

        {/* Candidate Info Card */}
        <div className="delivery-movie-box">
          <div className="delivery-badge-row">
            <span className="badge badge-quality">{candidate.quality || '1080P'}</span>
            {candidate.language && <span className="badge badge-lang">{candidate.language}</span>}
            {candidate.size && <span className="badge badge-size">{candidate.size}</span>}
          </div>
          <h4 className="delivery-movie-title">{candidate.title}</h4>
          <span className="delivery-movie-desc">
            {candidate.display_text || 'High-definition stream node connecting...'}
          </span>
        </div>

        {/* Progress Bar */}
        <div className="delivery-progress-wrap">
          <div className="delivery-progress-bar">
            <div
              className="delivery-progress-fill"
              style={{ width: `${Math.min(94, 25 + elapsedTime * 22)}%` }}
            />
          </div>
          <div className="delivery-status-row">
            <span className="delivery-status-label">
              {elapsedTime < 2
                ? 'Resolving media block...'
                : elapsedTime < 4
                ? 'Mounting container stream...'
                : 'Readying media player...'}
            </span>
            <span className="delivery-timer-label">{elapsedTime}s</span>
          </div>
        </div>

        {/* Did You Know? Trivia Card */}
        {!error && (
          <div className="delivery-trivia-card">
            <div className="delivery-trivia-icon">
              <Lightbulb size={16} className="text-amber" />
            </div>
            <div className="delivery-trivia-content">
              <strong className="delivery-trivia-heading">Did You Know?</strong>
              <p className="delivery-trivia-text">{currentFact}</p>
            </div>
          </div>
        )}

        {/* Error Box */}
        {error && (
          <div className="delivery-error-box">
            <AlertTriangle size={20} className="text-danger" />
            <div className="delivery-error-content">
              <strong>Stream generation failed</strong>
              <p>{error}</p>
            </div>
            <div className="delivery-error-actions">
              <button type="button" className="btn btn-secondary btn-sm" onClick={onClose}>
                Cancel
              </button>
              {onRetry && (
                <button type="button" className="btn btn-primary btn-sm" onClick={onRetry}>
                  Retry
                </button>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
