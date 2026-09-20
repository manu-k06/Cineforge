import React, { useState, useRef } from 'react'
import {
  X,
  Play,
  ExternalLink,
  Download,
  Copy,
  Check,
  HardDrive,
  Film,
  AlertCircle,
  Tv,
} from 'lucide-react'
import { formatBytes } from '../utils/helpers'

export default function PlayerModal({ delivery, onClose }) {
  const [copied, setCopied] = useState(false)
  const [hasPlaybackError, setHasPlaybackError] = useState(false)
  const videoRef = useRef(null)

  if (!delivery) return null

  const handleCopyLink = () => {
    const url = delivery.stream_url || delivery.watch_url
    if (url) {
      navigator.clipboard.writeText(url)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    }
  }

  const effectiveWatchUrl = delivery.watch_url || delivery.player_url || delivery.stream_url
  const effectiveDownloadUrl = delivery.download_url || `${delivery.stream_url}&d=true`

  return (
    <div className="modal-overlay player-modal-overlay" onClick={onClose}>
      <div className="modal-content player-modal-content" onClick={(e) => e.stopPropagation()}>
        {/* Header */}
        <div className="player-modal-header">
          <div className="player-title-info">
            <span className="badge badge-red mb-1">
              <Film size={12} /> STREAM READY
            </span>
            <h2 className="player-modal-title">
              {delivery.candidate_title || delivery.file_name}
            </h2>
            {delivery.file_size && (
              <span className="player-file-size">
                <HardDrive size={12} /> {formatBytes(delivery.file_size)} • {delivery.mime_type || 'video'}
              </span>
            )}
          </div>
          <button className="btn-icon" onClick={onClose} title="Close player">
            <X size={20} />
          </button>
        </div>

        {/* Video Player */}
        <div className="player-screen-wrapper">
          <video
            ref={videoRef}
            className="html5-video-player"
            controls
            autoPlay
            playsInline
            src={delivery.stream_url}
            onError={() => setHasPlaybackError(true)}
          >
            Your browser does not support the video tag.
          </video>

          {/* Fallback Banner for MKV / Unsupported Codecs */}
          {hasPlaybackError && (
            <div className="player-error-overlay">
              <AlertCircle size={32} className="text-warning mb-2" />
              <h3>Direct Browser Playback Restricted</h3>
              <p>
                This file format (e.g. MKV container or HEVC 10-bit) might not be natively decoded by your browser.
              </p>
              <div className="error-cta-row">
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
                  <Download size={16} /> Download Video
                </a>
              </div>
            </div>
          )}
        </div>

        {/* Action Toolbar */}
        <div className="player-actions-toolbar">
          <div className="toolbar-left">
            <a
              href={effectiveWatchUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="btn btn-primary"
              title="Open full-screen web player"
            >
              <ExternalLink size={16} /> Open Web Player
            </a>

            {delivery.download_url && (
              <a
                href={delivery.download_url}
                target="_blank"
                rel="noopener noreferrer"
                className="btn btn-secondary"
                title="Download video file"
              >
                <Download size={16} /> Download
              </a>
            )}

            <button className="btn btn-secondary" onClick={handleCopyLink}>
              {copied ? (
                <>
                  <Check size={16} className="text-success" />
                  <span>Copied!</span>
                </>
              ) : (
                <>
                  <Copy size={16} />
                  <span>Copy Stream Link</span>
                </>
              )}
            </button>
          </div>

          <div className="toolbar-right">
            <span className="stream-badge-bot">
              Powered by @stre89d_bot
            </span>
          </div>
        </div>

        {/* Stream URL details */}
        <div className="player-stream-info">
          <span className="info-label">Direct Stream Endpoint:</span>
          <code className="stream-url-snippet">{delivery.stream_url}</code>
        </div>
      </div>
    </div>
  )
}
