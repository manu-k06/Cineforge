import React from 'react'

export default function Footer() {
  return (
    <footer className="site-footer">
      <img
        className="brand-image small"
        src="/assets/images/aperture-mark.png"
        alt="Cineby"
        onError={(e) => {
          e.target.style.display = 'none'
        }}
      />
      <strong>Cineby</strong>
      <span>Metadata and imagery supplied by TMDB.</span>
      <span>Your library stays in this browser unless you export it.</span>
      <a
        className="telegram-footer-link"
        href="https://t.me/cinebytv"
        target="_blank"
        rel="noopener noreferrer"
        data-analytics-nav="telegram"
      >
        <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">
          <path d="M21.7 3.5 18.5 20c-.2 1.2-.9 1.5-1.8.9l-5-3.7-2.4 2.3c-.3.3-.5.5-1 .5l.4-5.1 9.3-8.4c.4-.4-.1-.6-.6-.3L5.9 13.5.9 12c-1.1-.3-1.1-1.1.2-1.6L20.4 3c.9-.3 1.7.2 1.3.5Z" />
        </svg>
        <span>Telegram</span>
      </a>
      <a href="/dmca" onClick={(e) => e.preventDefault()}>
        DMCA
      </a>
    </footer>
  )
}
