import React, { useState, useRef, useEffect } from 'react'
import { Bookmark, History, LogOut } from 'lucide-react'
import { useAuth } from '../context/AuthContext'
import { useWatchHistory } from '../context/WatchHistoryContext'

export default function Navbar({ onSearchClick, isBackendOnline, activeTab, setActiveTab }) {
  const { user, openAuthModal, signOut } = useAuth()
  const { watchlist, watchHistory } = useWatchHistory()
  const [isDropdownOpen, setIsDropdownOpen] = useState(false)
  const [isBrowseOpen, setIsBrowseOpen] = useState(false)
  const [isScrolled, setIsScrolled] = useState(false)
  
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

  const displayName = user?.user_metadata?.full_name || user?.email?.split('@')[0] || 'Member'

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

      {/* Header Actions: Search & Library Sync / Auth */}
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

        <button
          className="text-button"
          type="button"
          onClick={user ? () => setIsDropdownOpen((prev) => !prev) : openAuthModal}
        >
          {user ? displayName : 'Library sync'}
        </button>

        {/* User Profile Dropdown when authenticated */}
        {user && isDropdownOpen && (
          <div className="user-profile-menu" ref={dropdownRef}>
            <div className="user-profile-header">
              <strong>{displayName}</strong>
              <small>{user.email}</small>
            </div>
            <button
              type="button"
              className="user-profile-item"
              onClick={() => {
                setActiveTab('watchlist')
                setIsDropdownOpen(false)
              }}
            >
              <Bookmark size={14} /> Watchlist ({watchlist.length})
            </button>
            <button
              type="button"
              className="user-profile-item"
              onClick={() => {
                setActiveTab('history')
                setIsDropdownOpen(false)
              }}
            >
              <History size={14} /> History ({watchHistory.length})
            </button>
            <button
              type="button"
              className="user-profile-item text-danger"
              onClick={() => {
                signOut()
                setIsDropdownOpen(false)
              }}
            >
              <LogOut size={14} /> Sign Out
            </button>
          </div>
        )}
      </div>
    </header>
  )
}
