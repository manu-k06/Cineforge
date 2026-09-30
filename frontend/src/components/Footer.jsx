import React, { useState } from 'react'
import { Shield, ExternalLink, X, Send } from 'lucide-react'

export default function Footer({ onTabChange, isBackendOnline = true }) {
  const [isDmcaOpen, setIsDmcaOpen] = useState(false)

  const handleNav = (tab) => {
    if (onTabChange) {
      onTabChange(tab)
      window.scrollTo({ top: 0, behavior: 'smooth' })
    }
  }

  return (
    <>
      <footer className="site-footer">
        {/* Top 3-Column Grid */}
        <div className="footer-top-grid">
          {/* Column 1: Brand & Node Status */}
          <div className="footer-brand-col">
            <div className="footer-brand-header" onClick={() => handleNav('home')}>
              <img
                className="brand-image"
                src="/assets/images/aperture-mark.png"
                alt="Cineforge"
                onError={(e) => {
                  e.target.style.display = 'none'
                }}
              />
              <strong>Cineforge</strong>
            </div>
            <p className="footer-brand-desc">
              Next-generation cinema aggregator. Stream high-bitrate movies and television directly from
              Telegram bot nodes with seamless multi-audio playback and zero subscriptions.
            </p>
            <div className={`footer-status-badge ${isBackendOnline ? 'online' : 'offline'}`}>
              <span className="footer-status-dot" />
              <span>{isBackendOnline ? 'All Nodes Operational' : 'Node Reconnecting'}</span>
            </div>
          </div>

          {/* Column 2: Explore Navigation */}
          <div className="footer-nav-col">
            <h4 className="footer-col-title">Explore</h4>
            <button type="button" className="footer-link" onClick={() => handleNav('home')}>
              Home Showcase
            </button>
            <button type="button" className="footer-link" onClick={() => handleNav('watchlist')}>
              My Watchlist
            </button>
            <button type="button" className="footer-link" onClick={() => handleNav('history')}>
              Watch History
            </button>
            <a
              href="https://www.themoviedb.org"
              target="_blank"
              rel="noopener noreferrer"
              className="footer-link"
            >
              <span>TMDb Catalogue</span>
              <ExternalLink size={12} />
            </a>
          </div>

          {/* Column 3: Community & Legal */}
          <div className="footer-nav-col">
            <h4 className="footer-col-title">Community &amp; Legal</h4>
            <a
              className="footer-link telegram"
              href="https://t.me/cineforge"
              target="_blank"
              rel="noopener noreferrer"
              data-analytics-nav="telegram"
            >
              <Send size={14} />
              <span>Telegram Community</span>
            </a>
            <button
              type="button"
              className="footer-link"
              onClick={() => setIsDmcaOpen(true)}
            >
              <Shield size={14} />
              <span>DMCA Disclaimer</span>
            </button>
            <a
              href="https://github.com/manu-k06/Cineforge"
              target="_blank"
              rel="noopener noreferrer"
              className="footer-link"
            >
              <span>GitHub Source</span>
              <ExternalLink size={12} />
            </a>
          </div>
        </div>

        {/* Legal Disclaimer Box */}
        <div className="footer-disclaimer-card">
          <strong>Non-Hosting Legal Notice:</strong> Cineforge operates strictly as an automated client-side
          metadata aggregator and indexing utility. No video media or copyright-protected files are hosted, stored,
          uploaded, or transcoded on our servers. Media streams are delivered on-the-fly directly from independent
          third-party Telegram bot endpoints. Metadata, artwork, and descriptions are furnished by The Movie Database (TMDb).
        </div>

        {/* Bottom Bar */}
        <div className="footer-bottom-bar">
          <span>&copy; {new Date().getFullYear()} Cineforge. Built with pride for cinema lovers.</span>
          <div className="footer-credits">
            <span>v2.4.0</span>
            <span>&bull;</span>
            <span>Fast, Private &amp; Open</span>
          </div>
        </div>
      </footer>

      {/* DMCA Safe Harbor Modal */}
      {isDmcaOpen && (
        <div className="delivery-modal-backdrop" onClick={() => setIsDmcaOpen(false)}>
          <div className="dmca-modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="dmca-modal-header">
              <div className="dmca-modal-title">
                <Shield size={20} className="text-red" />
                <h3>Digital Millennium Copyright Act (DMCA) Notice</h3>
              </div>
              <button
                type="button"
                className="dmca-modal-close"
                onClick={() => setIsDmcaOpen(false)}
                aria-label="Close modal"
              >
                <X size={18} />
              </button>
            </div>

            <div className="dmca-modal-body">
              <p>
                <strong>Cineforge</strong> respects the intellectual property rights of creators and copyright owners
                and complies with the provisions of the Digital Millennium Copyright Act (17 U.S.C. § 512).
              </p>

              <h4>1. Service Nature &amp; Non-Hosting Statement</h4>
              <p>
                Cineforge does not store, upload, transmit, or cache copyright-protected audiovisual media on any server under
                its control. The application serves strictly as an indexing interface connecting personal users to public,
                third-party peer nodes and automated Telegram bots.
              </p>

              <h4>2. Takedown Requests</h4>
              <p>
                Because Cineforge does not store or host any content, removal of index references must be directed to the
                respective third-party Telegram channel or hosting host where the files physically reside. However, if you
                wish for an index entry or query alias to be removed from search caching, please reach out via our community channels.
              </p>

              <div className="dmca-modal-footer">
                <button
                  type="button"
                  className="btn btn-primary"
                  onClick={() => setIsDmcaOpen(false)}
                >
                  Understood &amp; Close
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </>
  )
}
