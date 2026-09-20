import React, { useState, useRef } from 'react'
import {
  ArrowLeft,
  Play,
  ExternalLink,
  Download,
  Copy,
  Check,
  HardDrive,
  Film,
  AlertCircle,
  Tv,
  Layers,
  Star,
  Sparkles,
  Share2,
} from 'lucide-react'
import { formatBytes, parseMovieMetadata } from '../utils/helpers'

export default function WatchPage({
  delivery,
  candidate,
  group,
  onBack,
  onSwitchVersion,
}) {
  const [copied, setCopied] = useState(false)
  const [hasPlaybackError, setHasPlaybackError] = useState(false)
  const videoRef = useRef(null)

  if (!delivery) return null

  const title = delivery.candidate_title || candidate?.title || delivery.file_name || 'Movie'
  const meta = parseMovieMetadata(title, candidate?.display_text || candidate?.details || '')

  const effectiveWatchUrl = delivery.watch_url || delivery.player_url || delivery.stream_url
  const effectiveDownloadUrl = delivery.download_url || `${delivery.stream_url}&d=true`

  const handleCopyLink = () => {
    const url = delivery.stream_url || delivery.watch_url
    if (url) {
      navigator.clipboard.writeText(url)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    }
  }

  const versions = group?.candidates || []

  return (
    <div className="cinema-watch-page">
      {/* Top Navigation Bar */}
      <div className="watch-navbar">
        <button className="btn btn-secondary btn-back" onClick={onBack}>
          <ArrowLeft size={18} />
          <span>Back to Browse</span>
        </button>
        <div className="watch-breadcrumbs">
          <span className="crumb-home" onClick={onBack}>Browse</span>
          <span className="crumb-sep">/</span>
          <span className="crumb-title">{meta.cleanTitle}</span>
          {meta.year && <span className="crumb-year">({meta.year})</span>}
        </div>
      </div>

      {/* Theater Viewport */}
      <div className="cinema-theater-container">
        {/* Ambient Backlight Glow */}
        <div className="cinema-ambient-glow" />

        {/* Video Player Screen */}
        <div className="cinema-screen-box">
          <video
            ref={videoRef}
            className="cinema-video-element"
            controls
            autoPlay
            playsInline
            src={delivery.stream_url}
            onError={() => setHasPlaybackError(true)}
          >
            Your browser does not support the video tag.
          </video>

          {/* Browser Codec Fallback Overlay */}
          {hasPlaybackError && (
            <div className="cinema-fallback-overlay">
              <div className="fallback-card">
                <AlertCircle size={36} className="text-warning mb-2" />
                <h3>Direct Browser Playback Restricted</h3>
                <p>
                  This video format (MKV container or HEVC 10-bit codec) is not natively decoded by your browser engine.
                  You can stream it smoothly using the bot's web player or an external player.
                </p>
                <div className="fallback-buttons">
                  <a
                    href={effectiveWatchUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="btn btn-primary"
                  >
                    <Tv size={16} /> Open in Bot Web Player
                  </a>
                  <a
                    href={effectiveDownloadUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="btn btn-secondary"
                  >
                    <Download size={16} /> Download Video ({formatBytes(delivery.file_size)})
                  </a>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Streaming Action Toolbar */}
        <div className="cinema-action-bar">
          <div className="action-bar-left">
            <a
              href={effectiveWatchUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="btn btn-primary btn-web-player"
            >
              <ExternalLink size={16} /> Open Web Player
            </a>

            {delivery.download_url && (
              <a
                href={delivery.download_url}
                target="_blank"
                rel="noopener noreferrer"
                className="btn btn-secondary"
              >
                <Download size={16} /> Download Video
              </a>
            )}

            <button className="btn btn-secondary" onClick={handleCopyLink}>
              {copied ? (
                <>
                  <Check size={16} className="text-success" />
                  <span>Copied Link!</span>
                </>
              ) : (
                <>
                  <Copy size={16} />
                  <span>Copy Stream URL</span>
                </>
              )}
            </button>
          </div>

          <div className="action-bar-right">
            <span className="badge badge-quality">
              {delivery.mime_type || 'Video'}
            </span>
            <span className="stream-badge-bot">
              Powered by @stre89d_bot
            </span>
          </div>
        </div>
      </div>

      {/* Cinema Information & Versions Layout */}
      <div className="cinema-details-layout">
        {/* Main Details Column */}
        <div className="details-main-col">
          <div className="details-header">
            <div className="badges-row">
              <span className="badge badge-red">
                <Film size={12} /> STREAMING NOW
              </span>
              <span className="badge badge-quality">{meta.resolution}</span>
              {meta.tags.map((t) => (
                <span key={t} className="badge">
                  {t}
                </span>
              ))}
            </div>
            <h1 className="details-title">{meta.cleanTitle}</h1>
            <div className="details-meta-stats">
              {meta.year && <span className="stat-item">{meta.year}</span>}
              {delivery.file_size && (
                <>
                  <span className="stat-dot">•</span>
                  <span className="stat-item">
                    <HardDrive size={13} className="inline-icon" /> {formatBytes(delivery.file_size)}
                  </span>
                </>
              )}
              {delivery.container && (
                <>
                  <span className="stat-dot">•</span>
                  <span className="stat-item uppercase">{delivery.container}</span>
                </>
              )}
            </div>
          </div>

          <div className="details-body">
            <h3 className="section-heading">File Information</h3>
            <div className="file-info-grid">
              <div className="info-cell">
                <span className="cell-label">File Name</span>
                <span className="cell-value text-mono">{delivery.file_name}</span>
              </div>
              <div className="info-cell">
                <span className="cell-label">Source</span>
                <span className="cell-value">Telegram Bot Delivery</span>
              </div>
              <div className="info-cell">
                <span className="cell-label">Stream Endpoint</span>
                <span className="cell-value text-mono text-break">{delivery.stream_url}</span>
              </div>
            </div>
          </div>
        </div>

        {/* Sidebar: Available Releases & Quality Switcher */}
        {versions.length > 1 && (
          <div className="details-sidebar-col">
            <div className="sidebar-box">
              <div className="sidebar-header">
                <Layers size={16} className="text-red" />
                <h3 className="sidebar-title">Available Releases ({versions.length})</h3>
              </div>
              <p className="sidebar-desc">
                Switch resolution, file size, or audio tracks on the fly:
              </p>

              <div className="sidebar-versions-list">
                {versions.map((ver, idx) => {
                  const verMeta = parseMovieMetadata(ver.title, ver.display_text || ver.size || '')
                  const isCurrent = (candidate?.candidate_id === ver.candidate_id) || (ver.title === candidate?.title)

                  return (
                    <div
                      key={ver.candidate_id || idx}
                      className={`version-row ${isCurrent ? 'active-version' : ''}`}
                      onClick={() => !isCurrent && onSwitchVersion(ver)}
                    >
                      <div className="version-info">
                        <div className="version-badges">
                          <span className="badge badge-quality">{ver.quality || verMeta.resolution}</span>
                          {(ver.size || verMeta.fileSize) && (
                            <span className="badge badge-sm">
                              {ver.size || verMeta.fileSize}
                            </span>
                          )}
                          {isCurrent && (
                            <span className="badge badge-red badge-sm">PLAYING</span>
                          )}
                        </div>
                        <span className="version-display-text" title={ver.display_text || ver.title}>
                          {ver.display_text || ver.title}
                        </span>
                      </div>
                      {!isCurrent && (
                        <button className="btn btn-secondary btn-sm switch-btn">
                          <Play size={12} fill="#FFFFFF" /> Switch
                        </button>
                      )}
                    </div>
                  )
                })}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
