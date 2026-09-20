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
      <div className="modal-content delivery-modal">
        <div className="delivery-header">
          <div className="delivery-icon-glow">
            <Radio size={32} className="text-red animate-pulse" />
          </div>
          <h2 className="delivery-modal-title">Initiating Bot Stream Pipeline</h2>
          <p className="delivery-modal-desc">
            Fetching media file from Telegram and forwarding to stream bot...
          </p>
        </div>

        {/* Selected Movie Info */}
        <div className="delivery-candidate-card">
          <span className="badge badge-quality mb-1">SELECTED RELEASE</span>
          <h4 className="delivery-candidate-title">{candidate.title}</h4>
          {detailsText && (
            <p className="delivery-candidate-details">{detailsText}</p>
          )}
        </div>

        {/* Pipeline Steps */}
        <div className="delivery-pipeline">
          {/* Step 1 */}
          <div className={`pipeline-step ${getStepStatus(1)}`}>
            <div className="step-icon">
              {getStepStatus(1) === 'done' ? (
                <CheckCircle2 size={18} className="text-success" />
              ) : (
                <Loader2 size={18} className="animate-spin text-red" />
              )}
            </div>
            <div className="step-text">
              <span className="step-title">1. Querying @Spoty_xbot</span>
              <span className="step-subtitle">Triggering inline callback button</span>
            </div>
          </div>

          {/* Step 2 */}
          <div className={`pipeline-step ${getStepStatus(2)}`}>
            <div className="step-icon">
              {getStepStatus(2) === 'done' ? (
                <CheckCircle2 size={18} className="text-success" />
              ) : getStepStatus(2) === 'active' ? (
                <Loader2 size={18} className="animate-spin text-red" />
              ) : (
                <div className="step-dot" />
              )}
            </div>
            <div className="step-text">
              <span className="step-title">2. Forwarding to @stre89d_bot</span>
              <span className="step-subtitle">Routing video document to stream engine</span>
            </div>
          </div>

          {/* Step 3 */}
          <div className={`pipeline-step ${getStepStatus(3)}`}>
            <div className="step-icon">
              {getStepStatus(3) === 'done' ? (
                <CheckCircle2 size={18} className="text-success" />
              ) : getStepStatus(3) === 'active' ? (
                <Loader2 size={18} className="animate-spin text-red" />
              ) : (
                <div className="step-dot" />
              )}
            </div>
            <div className="step-text">
              <span className="step-title">3. Generating Stream URLs</span>
              <span className="step-subtitle">Extracting direct stream & web watch links</span>
            </div>
          </div>
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
