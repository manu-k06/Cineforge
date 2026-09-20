import React from 'react'
import { X, Play, HardDrive, CheckCircle2, Layers } from 'lucide-react'
import { parseMovieMetadata } from '../utils/helpers'

export default function VersionPickerModal({ group, onClose, onSelectCandidate }) {
  if (!group || !group.candidates || group.candidates.length === 0) return null

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content version-modal" onClick={(e) => e.stopPropagation()}>
        {/* Header */}
        <div className="modal-header">
          <div className="modal-title-box">
            <span className="badge badge-red">
              <Layers size={12} /> {group.candidates.length} Available Releases
            </span>
            <h2 className="modal-title">{group.title}</h2>
            <p className="modal-subtitle">
              Select your preferred resolution, audio track, and file size to start streaming:
            </p>
          </div>
          <button className="btn-icon modal-close-btn" onClick={onClose} title="Close">
            <X size={20} />
          </button>
        </div>

        {/* Candidate List */}
        <div className="candidates-list">
          {group.candidates.map((cand, idx) => {
            const meta = parseMovieMetadata(
              cand.title,
              cand.display_text || cand.size || cand.details || ''
            )
            const displaySize = cand.size || meta.fileSize
            const detailsText = cand.display_text || cand.details || ''

            return (
              <div
                key={cand.candidate_id || idx}
                className="candidate-item"
                onClick={() => onSelectCandidate(cand)}
              >
                <div className="candidate-left">
                  <div className="candidate-badge-col">
                    <span className="badge badge-quality">{cand.quality || meta.resolution}</span>
                    {displaySize && (
                      <span className="candidate-size">
                        <HardDrive size={12} /> {displaySize}
                      </span>
                    )}
                  </div>
                  <div className="candidate-info">
                    <h4 className="candidate-title">{cand.title}</h4>
                    {detailsText && (
                      <p className="candidate-details-text">{detailsText}</p>
                    )}
                    <div className="candidate-tags-row">
                      {cand.container && (
                        <span className="badge badge-sm">{cand.container.toUpperCase()}</span>
                      )}
                      {cand.language && (
                        <span className="badge badge-sm">{cand.language}</span>
                      )}
                      {meta.tags.map((t) => (
                        <span key={t} className="badge badge-sm">
                          {t}
                        </span>
                      ))}
                    </div>
                  </div>
                </div>

                <div className="candidate-right">
                  <button className="btn btn-primary btn-sm candidate-play-btn">
                    <Play size={14} fill="#FFFFFF" /> Stream
                  </button>
                </div>
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}
