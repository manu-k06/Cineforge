import React, { useState, useMemo } from 'react'
import { X, Play, HardDrive, Sparkles, ChevronDown, ChevronUp, Layers, CheckCircle2, Film, Globe } from 'lucide-react'
import { parseMovieMetadata } from '../utils/helpers'

// Categorize release language from candidate metadata and display text
export function categorizeLanguage(cand) {
  const l = (cand.language || '').toLowerCase()
  const text = `${cand.title || ''} ${cand.display_text || ''} ${cand.details || ''}`.toLowerCase()

  if (l.includes('multi') || l.includes('dual') || /\b(multi\s*audio|dual\s*audio|multi\s*lang)\b/i.test(text)) {
    return 'Multi Audio'
  }
  if (l.includes('english') || /\b(english|eng)\b/i.test(text)) {
    return 'English'
  }
  if (l.includes('tamil') || /\b(tamil|tam)\b/i.test(text)) {
    return 'Tamil'
  }
  if (l.includes('telugu') || /\b(telugu|tel|telug)\b/i.test(text)) {
    return 'Telugu'
  }
  if (l.includes('hindi') || /\b(hindi|hin)\b/i.test(text)) {
    return 'Hindi'
  }
  if (l.includes('malayalam') || /\b(malayalam|mal)\b/i.test(text)) {
    return 'Malayalam'
  }
  if (l.includes('kannada') || /\b(kannada|kan)\b/i.test(text)) {
    return 'Kannada'
  }
  // International clean release encoders (usually original English audio)
  if (/\b(pahe|psa|yts|yify|rarbg|eztv|galaxyrg|bluray|hevc|web-?dl|bdrip)\b/i.test(text)) {
    return 'English'
  }
  return 'Original / Other'
}

// Return human-friendly flag badge and color for language
export function getLanguageBadgeInfo(category) {
  switch (category) {
    case 'English':
      return { flag: '🇬🇧', label: 'English', cls: 'badge-lang-eng' }
    case 'Multi Audio':
      return { flag: '🌐', label: 'Multi Audio', cls: 'badge-lang-multi' }
    case 'Tamil':
      return { flag: '🇮🇳', label: 'Tamil', cls: 'badge-lang-tam' }
    case 'Telugu':
      return { flag: '🇮🇳', label: 'Telugu', cls: 'badge-lang-tel' }
    case 'Hindi':
      return { flag: '🇮🇳', label: 'Hindi', cls: 'badge-lang-hin' }
    case 'Malayalam':
      return { flag: '🇮🇳', label: 'Malayalam', cls: 'badge-lang-mal' }
    case 'Kannada':
      return { flag: '🇮🇳', label: 'Kannada', cls: 'badge-lang-kan' }
    default:
      return { flag: '🎬', label: 'Original', cls: 'badge-lang-other' }
  }
}

export default function VersionPickerModal({ group, onClose, onSelectCandidate }) {
  const [showAllFiles, setShowAllFiles] = useState(false)
  const [selectedLang, setSelectedLang] = useState('all')

  const allCandidates = group?.candidates || []
  if (allCandidates.length === 0) return null

  // 1. Compute available languages and counts
  const { availableLangs, langCounts } = useMemo(() => {
    const counts = { all: allCandidates.length }
    allCandidates.forEach((c) => {
      const cat = categorizeLanguage(c)
      counts[cat] = (counts[cat] || 0) + 1
    })

    const PREFERRED_ORDER = ['English', 'Multi Audio', 'Tamil', 'Telugu', 'Hindi', 'Malayalam', 'Kannada', 'Original / Other']
    const langs = PREFERRED_ORDER.filter((lang) => (counts[lang] || 0) > 0)
    return { availableLangs: langs, langCounts: counts }
  }, [allCandidates])

  // 2. Filter candidates based on active language tab
  const filteredCandidates = useMemo(() => {
    if (selectedLang === 'all') return allCandidates
    return allCandidates.filter((c) => categorizeLanguage(c) === selectedLang)
  }, [allCandidates, selectedLang])

  // 3. Categorize active candidates into 3 consumer-friendly tiers
  const uhdCandidates = filteredCandidates.filter((c) =>
    /2160p|4k|uhd/i.test(c.quality || c.display_text || c.title || '')
  )
  const fhdCandidates = filteredCandidates.filter((c) =>
    /1080p|fhd/i.test(c.quality || c.display_text || c.title || '')
  )
  const hdCandidates = filteredCandidates.filter((c) =>
    /720p|hd|480p|576p/i.test(c.quality || c.display_text || c.title || '')
  )

  // Pick best representative candidate per tier
  const getBest = (list) => {
    if (!list || list.length === 0) return null
    return [...list].sort((a, b) => {
      // In 'all' mode, prefer English or Multi-Audio over single regional dubs
      if (selectedLang === 'all') {
        const catA = categorizeLanguage(a)
        const catB = categorizeLanguage(b)
        const score = (cat) => (cat === 'English' ? 3 : cat === 'Multi Audio' ? 2 : 1)
        const diff = score(catB) - score(catA)
        if (diff !== 0) return diff
      }
      return (b.size_bytes || 0) - (a.size_bytes || 0)
    })[0]
  }

  const bestUhd = getBest(uhdCandidates)
  const bestFhd = getBest(fhdCandidates) || (uhdCandidates.length === 0 ? getBest(filteredCandidates) : null)
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
      subtitle: 'Optimal high-bitrate streaming with zero buffering & rich audio',
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
              Choose your preferred viewing quality and audio track. We automatically select the cleanest stream.
            </p>
          </div>
          <button className="btn-icon modal-close-btn" onClick={onClose} title="Close">
            <X size={20} />
          </button>
        </div>

        {/* Audio / Language Selector Drawer */}
        {availableLangs.length > 1 && (
          <div className="language-selector-section">
            <div className="lang-section-header">
              <span className="lang-header-label">
                <Globe size={14} /> AUDIO TRACKS ({allCandidates.length} Streams)
              </span>
            </div>
            <div className="language-tabs-bar">
              <button
                className={`lang-tab-pill ${selectedLang === 'all' ? 'active' : ''}`}
                onClick={() => setSelectedLang('all')}
              >
                <span>All Tracks</span>
                <span className="lang-count">{langCounts.all}</span>
              </button>
              {availableLangs.map((lang) => {
                const info = getLanguageBadgeInfo(lang)
                return (
                  <button
                    key={lang}
                    className={`lang-tab-pill ${selectedLang === lang ? 'active' : ''}`}
                    onClick={() => setSelectedLang(lang)}
                  >
                    <span>{info.flag} {info.label}</span>
                    <span className="lang-count">{langCounts[lang] || 0}</span>
                  </button>
                )
              })}
            </div>
          </div>
        )}

        {/* 3-Tier Quality Cards */}
        <div className="quality-tiers-grid">
          {tiers.length > 0 ? (
            tiers.map((tier) => {
              const cand = tier.candidate
              const meta = parseMovieMetadata(
                cand.title,
                cand.display_text || cand.size || cand.details || ''
              )
              const displaySize = cand.size || meta.fileSize
              const langInfo = getLanguageBadgeInfo(categorizeLanguage(cand))

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
                      <span className={`badge badge-sm ${langInfo.cls}`}>
                        {langInfo.flag} {cand.language || langInfo.label}
                      </span>
                      {cand.container && <span className="badge badge-sm">{cand.container.toUpperCase()}</span>}
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
            })
          ) : (
            <div className="empty-tier-notice">
              <p>No streams available for this audio filter.</p>
              <button className="btn btn-sm btn-secondary" onClick={() => setSelectedLang('all')}>
                Show All Audio Tracks
              </button>
            </div>
          )}
        </div>

        {/* Advanced Drawer: Raw Files */}
        <div className="advanced-raw-section">
          <button
            className="advanced-toggle-btn"
            onClick={() => setShowAllFiles(!showAllFiles)}
          >
            <span>
              Advanced: View all {filteredCandidates.length} {selectedLang !== 'all' ? selectedLang : ''} release files
            </span>
            {showAllFiles ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
          </button>

          {showAllFiles && (
            <div className="candidates-list-accordion">
              {filteredCandidates.map((cand, idx) => {
                const meta = parseMovieMetadata(
                  cand.title,
                  cand.display_text || cand.size || cand.details || ''
                )
                const displaySize = cand.size || meta.fileSize
                const detailsText = cand.display_text || cand.details || ''
                const langInfo = getLanguageBadgeInfo(categorizeLanguage(cand))

                return (
                  <div
                    key={cand.candidate_id || idx}
                    className="candidate-item"
                    onClick={() => onSelectCandidate(cand)}
                  >
                    <div className="candidate-left">
                      <div className="candidate-badge-col">
                        <span className="badge badge-quality">{cand.quality || meta.resolution}</span>
                        <span className={`badge badge-sm ${langInfo.cls}`}>
                          {langInfo.flag} {cand.language || langInfo.label}
                        </span>
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
