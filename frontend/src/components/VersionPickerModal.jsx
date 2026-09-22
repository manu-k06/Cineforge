import React, { useState } from 'react'
import { X, Play, HardDrive, Sparkles, ChevronDown, ChevronUp, Layers, CheckCircle2, Film } from 'lucide-react'
import { parseMovieMetadata } from '../utils/helpers'

export default function VersionPickerModal({ group, onClose, onSelectCandidate }) {
  const [showAllFiles, setShowAllFiles] = useState(false)

  if (!group || !group.candidates || group.candidates.length === 0) return null

  // Categorize candidates into 3 consumer-friendly tiers
  const candidates = group.candidates

  const uhdCandidates = candidates.filter((c) =>
    /2160p|4k|uhd/i.test(c.quality || c.display_text || c.title || '')
  )
  const fhdCandidates = candidates.filter((c) =>
    /1080p|fhd/i.test(c.quality || c.display_text || c.title || '')
  )
  const hdCandidates = candidates.filter((c) =>
    /720p|hd|480p|576p/i.test(c.quality || c.display_text || c.title || '')
  )

  // Pick best representative candidate per tier (prefer larger file size if available)
  const getBest = (list) => {
    if (!list || list.length === 0) return null
    return list.reduce((best, curr) => {
      const bestBytes = best.size_bytes || 0
      const currBytes = curr.size_bytes || 0
      return currBytes > bestBytes ? curr : best
    }, list[0])
  }

  const bestUhd = getBest(uhdCandidates)
  const bestFhd = getBest(fhdCandidates) || (uhdCandidates.length === 0 ? getBest(candidates) : null)
  const bestHd = getBest(hdCandidates)

  const tiers = [
    {
      id: 'uhd',
      title: '4K Ultra HD',
      subtitle: 'Crisp 2160p resolution with high dynamic range & surround audio',
      badge: 'CINEMA 4K',
      badgeClass: 'badge-gold',
      candidate: bestUhd,
      count: uhdCandidates.length,
      recommended: false,
    },
    {
      id: 'fhd',
      title: '1080p Full HD',
      subtitle: 'Optimal high-bitrate streaming with zero buffering & dual audio',
      badge: 'RECOMMENDED',
      badgeClass: 'badge-recommended',
      candidate: bestFhd,
      count: fhdCandidates.length,
      recommended: true,
    },
    {
      id: 'hd',
      title: '720p Fast Stream',
      subtitle: 'Quick loading format optimized for mobile or slower connections',
      badge: 'FAST STREAM',
      badgeClass: 'badge-silver',
      candidate: bestHd,
      count: hdCandidates.length,
      recommended: false,
    },
  ].filter((t) => t.candidate !== null)

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content version-modal-redesign" onClick={(e) => e.stopPropagation()}>
        {/* Modal Header */}
        <div className="modal-header">
          <div className="modal-title-box">
            <span className="badge badge-red">
              <Film size={12} /> STREAM SELECTOR
            </span>
            <h2 className="modal-title">{group.title}</h2>
            <p className="modal-subtitle">
              Choose your preferred viewing quality. We automatically select the cleanest stream.
            </p>
          </div>
          <button className="btn-icon modal-close-btn" onClick={onClose} title="Close">
            <X size={20} />
          </button>
        </div>

        {/* 3-Tier Quality Cards */}
        <div className="quality-tiers-grid">
          {tiers.map((tier) => {
            const cand = tier.candidate
            const meta = parseMovieMetadata(
              cand.title,
              cand.display_text || cand.size || cand.details || ''
            )
            const displaySize = cand.size || meta.fileSize

            return (
              <div
                key={tier.id}
                className={`quality-tier-card ${tier.recommended ? 'tier-recommended' : ''}`}
                onClick={() => onSelectCandidate(cand)}
              >
                <div className="tier-card-top">
                  <span className={`badge ${tier.badgeClass}`}>{tier.badge}</span>
                  {displaySize && (
                    <span className="tier-size">
                      <HardDrive size={13} /> {displaySize}
                    </span>
                  )}
                </div>

                <div className="tier-card-body">
                  <h3 className="tier-title">{tier.title}</h3>
                  <p className="tier-desc">{tier.subtitle}</p>

                  <div className="tier-tags">
                    {cand.container && <span className="badge badge-sm">{cand.container.toUpperCase()}</span>}
                    {cand.language && <span className="badge badge-sm">{cand.language}</span>}
                    {meta.tags.slice(0, 2).map((t) => (
                      <span key={t} className="badge badge-sm">
                        {t}
                      </span>
                    ))}
                    {tier.count > 1 && (
                      <span className="badge badge-sm text-muted">
                        +{tier.count - 1} more {tier.title.split(' ')[0]} sources
                      </span>
                    )}
                  </div>
                </div>

                <div className="tier-card-bottom">
                  <button className="btn btn-tier-play">
                    <Play size={16} fill="#FFFFFF" />
                    <span>Watch in {tier.title.split(' ')[0]}</span>
                  </button>
                </div>
              </div>
            )
          })}
        </div>

        {/* Advanced Drawer: All Raw Files */}
        <div className="advanced-raw-section">
          <button
            className="advanced-toggle-btn"
            onClick={() => setShowAllFiles(!showAllFiles)}
          >
            <span>
              Advanced: View all {candidates.length} raw release files
            </span>
            {showAllFiles ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
          </button>

          {showAllFiles && (
            <div className="candidates-list-accordion">
              {candidates.map((cand, idx) => {
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
                        {detailsText && <p className="candidate-details-text">{detailsText}</p>}
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
          )}
        </div>
      </div>
    </div>
  )
}
