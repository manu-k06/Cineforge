import React, { useEffect, useState } from 'react'
import { Loader2, CheckCircle2, AlertTriangle, Play, Sparkles, Send, Radio } from 'lucide-react'

export default function DeliveryModal({ candidate, error, onClose, onRetry }) {
  const [elapsedTime, setElapsedTime] = useState(0)

  useEffect(() => {
    const timer = setInterval(() => {
      setElapsedTime((prev) => prev + 1)
    }, 1000)
    return () => clearInterval(timer)
  }, [])

  // Dynamic step simulation based on elapsed time
  const getStepStatus = (stepIndex) => {
    if (error) return 'error'
    if (stepIndex === 1) {
      return elapsedTime >= 1 ? 'done' : 'active'
    }
    if (stepIndex === 2) {
      if (elapsedTime < 1) return 'pending'
      return elapsedTime >= 3 ? 'done' : 'active'
    }
    if (stepIndex === 3) {
      if (elapsedTime < 3) return 'pending'
      return 'active'
    }
    return 'pending'
  }

  const detailsText = candidate.display_text || candidate.details || candidate.size || ''

  return (
    <div className="modal-overlay">
      <div className="modal-content delivery-modal cinematic-delivery">
        <div className="delivery-header">
          <div className="cinema-buffering-ring">
            <Loader2 size={42} className="animate-spin text-red" />
          </div>
          <h2 className="delivery-modal-title">Preparing Cinema Stream</h2>
          <p className="delivery-modal-desc">
            Allocating dedicated high-speed bandwidth & syncing audio tracks...
          </p>
        </div>

        {/* Selected Movie Info */}
        <div className="delivery-candidate-card">
          <div className="candidate-badge-row">
            <span className="badge badge-quality">{candidate.quality || '1080P'}</span>
            {candidate.size && <span className="badge badge-sm">{candidate.size}</span>}
            {candidate.language && <span className="badge badge-sm">{candidate.language}</span>}
          </div>
          <h4 className="delivery-candidate-title">{candidate.title}</h4>
        </div>

        {/* Cinematic Stream Initialization Status */}
        <div className="cinema-loading-progress">
          <div className="progress-bar-track">
            <div 
              className="progress-bar-fill" 
              style={{ width: `${Math.min(95, 20 + elapsedTime * 25)}%` }}
            />
          </div>
          <span className="loading-status-text">
            {elapsedTime < 2 ? 'Connecting to cinema node...' : elapsedTime < 4 ? 'Mounting media container...' : 'Readying video player...'}
          </span>
        </div>

        {/* Elapsed Timer */}
        {!error && (
          <div className="delivery-timer">
            <span className="timer-text">Elapsed: {elapsedTime}s</span>
            <span className="timer-tip">(Typically completes in 4-6 seconds)</span>
          </div>
        )}

        {/* Error Handling */}
        {error && (
          <div className="delivery-error-box">
            <AlertTriangle size={20} className="text-danger" />
            <div className="error-message-col">
              <span className="error-heading">Stream Generation Failed</span>
              <span className="error-desc">{error}</span>
            </div>
            <div className="error-actions">
              <button className="btn btn-secondary btn-sm" onClick={onClose}>
                Cancel
              </button>
              {onRetry && (
                <button className="btn btn-primary btn-sm" onClick={onRetry}>
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
