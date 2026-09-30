import React, { useState, useRef, useEffect } from 'react'
import { Bookmark, LogOut, User, ChevronDown, UserPlus } from 'lucide-react'
import { useAuth } from '../context/AuthContext'
import { useWatchHistory } from '../context/WatchHistoryContext'

export default function Navbar({ onSearchClick, isBackendOnline, activeTab, setActiveTab }) {
  const { user, profile, openAuthModal, signOut } = useAuth()
  const { watchlist } = useWatchHistory()
  const [isDropdownOpen, setIsDropdownOpen] = useState(false)
  const [isBrowseOpen, setIsBrowseOpen] = useState(false)
  const [isScrolled, setIsScrolled] = useState(false)

  const cartoonAvatarSrc = '/assets/images/avatars/cartoon-avatar.svg'
  const dropdownRef = useRef(null)
  const browseRef = useRef(null)

  // Track scroll position to transition header from transparent gradient to frosted blur
  useEffect(() => {
    const handleScroll = () => {
      setIsScrolled(window.scrollY > 20)
    }
    window.addEventListener('scroll', handleScroll, { passive: true })
    return () => window.removeEventListener('scroll', handleScroll)
  }, [])

  // Close dropdowns on outside click
  useEffect(() => {
    const handleClickOutside = (e) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target)) {
        setIsDropdownOpen(false)
      }
      if (browseRef.current && !browseRef.current.contains(e.target)) {
        setIsBrowseOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  const displayName = profile?.full_name || user?.user_metadata?.full_name || user?.email?.split('@')[0] || 'Member'
  const firstName = displayName.split(' ')[0]

  return (
    <header className={`site-header ${isScrolled ? 'is-scrolled' : ''}`}>
      {/* Brand: Aperture Mark + Cineforge in Archivo Black */}
      <div className="brand" onClick={() => setActiveTab('home')} title="Cineforge Home">
        <img
          className="brand-image"
          src="/assets/images/aperture-mark.png"
          alt="Cineforge"
          onError={(e) => {
            // Fallback SVG if image not loaded
            e.target.style.display = 'none'
          }}
        />
        <span>Cineforge</span>
      </div>

      {/* Primary Nav */}
      <nav className="primary-nav" aria-label="Primary navigation">
        <button
          className={activeTab === 'home' ? 'is-active' : ''}
          onClick={() => setActiveTab('home')}
        >
          Home
        </button>

        {/* Browse Popover Dropdown */}
        <div className="nav-menu nav-browse-menu" ref={browseRef}>
          <button
            className={`nav-menu-trigger ${['movies', 'shows', 'history', 'watchlist'].includes(activeTab) ? 'is-active' : ''} ${isBrowseOpen ? 'is-open' : ''}`}
            type="button"
            onClick={() => setIsBrowseOpen((prev) => !prev)}
            aria-expanded={isBrowseOpen}
          >
            Browse <span className="nav-chevron" aria-hidden="true">⏷</span>
          </button>

          {isBrowseOpen && (
            <div className="nav-popover nav-browse-panel">
              <div className="browse-panel-top">
                <strong className="browse-panel-title">Browse</strong>
                <span>Library & discovery</span>
              </div>

              <p className="menu-eyebrow">Discover</p>
              <div className="menu-discovery-grid">
                <button
                  type="button"
                  className="menu-discovery-card"
                  onClick={() => {
                    setActiveTab('movies')
                    setIsBrowseOpen(false)
                  }}
                >
                  <strong>Movies</strong>
                  <small>Explore the catalogue</small>
                </button>
                <button
                  type="button"
                  className="menu-discovery-card"
                  onClick={() => {
                    setActiveTab('shows')
                    setIsBrowseOpen(false)
                  }}
                >
                  <strong>TV Shows</strong>
                  <small>Series and episodes</small>
                </button>
              </div>

              <p className="menu-eyebrow">Your library</p>
              <div className="menu-personal-grid">
                <button
                  type="button"
                  className="personal-menu-card"
                  onClick={() => {
                    setActiveTab('history')
                    setIsBrowseOpen(false)
                  }}
                >
                  <strong>History</strong>
                  <span>Pick up where you left off</span>
                </button>
                <button
                  type="button"
                  className="personal-menu-card"
                  onClick={() => {
                    setActiveTab('watchlist')
                    setIsBrowseOpen(false)
                  }}
                >
                  <strong>Watchlist</strong>
                  <span>Saved for later {watchlist.length > 0 && `(${watchlist.length})`}</span>
                </button>
              </div>
            </div>
          )}
        </div>
      </nav>

      {/* Header Actions: Search & User Profile / Auth */}
      <div className="header-actions">
        <button
          className="icon-button"
          type="button"
          onClick={onSearchClick}
          aria-label="Search titles"
          title="Search titles"
        >
          ⌕
        </button>

        {user ? (
          <button
            className="nav-profile-pill"
            type="button"
            onClick={() => setIsDropdownOpen((prev) => !prev)}
            aria-expanded={isDropdownOpen}
            aria-label="User account menu"
            title={`${displayName} (${user.email})`}
          >
            <div className="nav-profile-avatar-wrap">
              <img
                src={cartoonAvatarSrc}
                alt="Cartoon Avatar"
                className="nav-profile-avatar-img"
              />
            </div>
            <span className="nav-profile-name">{firstName}</span>
            <ChevronDown size={13} className={`nav-profile-chevron ${isDropdownOpen ? 'is-rotated' : ''}`} />
          </button>
        ) : (
          <button
            className="nav-guest-pill"
            type="button"
            onClick={openAuthModal}
            title="Sign in to sync your library across devices"
          >
            <div className="nav-guest-icon-badge">
              <User size={14} />
            </div>
            <span className="nav-guest-text">Sign In</span>
            <span className="nav-guest-tag">Sync</span>
          </button>
        )}

        {/* User Profile Dropdown when authenticated */}
        {user && isDropdownOpen && (
          <div className="user-profile-menu" ref={dropdownRef}>
            {/* Profile Hero Header */}
            <div className="user-profile-hero">
              <div className="user-hero-avatar">
                <img
                  src={cartoonAvatarSrc}
                  alt="Cartoon Avatar"
                  className="user-hero-avatar-img"
                />
              </div>
              <div className="user-hero-info">
                <strong className="user-hero-name">{displayName}</strong>
                <span className="user-hero-email" title={user.email}>{user.email}</span>
              </div>
            </div>

            {/* Quick Library Shortcuts (Watchlist) */}
            <div className="user-library-shortcuts">
              <button
                type="button"
                className="user-shortcut-card"
                onClick={() => {
                  setActiveTab('watchlist')
                  setIsDropdownOpen(false)
                }}
              >
                <div className="shortcut-icon-wrap watchlist">
                  <Bookmark size={15} />
                </div>
                <div className="shortcut-meta">
                  <span className="shortcut-name">Watchlist</span>
                  <span className="shortcut-number">{watchlist.length} saved titles</span>
                </div>
                <span className="shortcut-arrow">➔</span>
              </button>
            </div>

            {/* Account Actions: Add Another Account & Sign Out */}
            <div className="user-profile-footer">
              <button
                type="button"
                className="user-action-button"
                onClick={async () => {
                  setIsDropdownOpen(false)
                  await signOut()
                  openAuthModal('signin')
                }}
              >
                <UserPlus size={14} />
                <span>Add another account</span>
              </button>

              <button
                type="button"
                className="user-signout-button"
                onClick={() => {
                  signOut()
                  setIsDropdownOpen(false)
                }}
              >
                <LogOut size={14} />
                <span>Sign Out</span>
              </button>
            </div>
          </div>
        )}
      </div>
    </header>
  )
}
