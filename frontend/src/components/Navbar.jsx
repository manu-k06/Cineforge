import React, { useState, useRef, useEffect } from 'react'
import { Bookmark, History, LogOut, User, ChevronDown, Check } from 'lucide-react'
import { useAuth } from '../context/AuthContext'
import { useWatchHistory } from '../context/WatchHistoryContext'

export const AVATAR_PRESETS = [
  { id: 'director', icon: '🎬', label: 'Director', gradient: 'linear-gradient(135deg, #e50914, #8b0000)' },
  { id: 'astronaut', icon: '🚀', label: 'Cosmonaut', gradient: 'linear-gradient(135deg, #3b82f6, #1d4ed8)' },
  { id: 'agent', icon: '🕶️', label: 'Agent', gradient: 'linear-gradient(135deg, #8b5cf6, #5b21b6)' },
  { id: 'cinephile', icon: '🍿', label: 'Cinephile', gradient: 'linear-gradient(135deg, #f59e0b, #b45309)' },
  { id: 'neon', icon: '⚡', label: 'Neon', gradient: 'linear-gradient(135deg, #ec4899, #9d174d)' },
  { id: 'dramatic', icon: '🎭', label: 'Dramatic', gradient: 'linear-gradient(135deg, #10b981, #047857)' },
]

export default function Navbar({ onSearchClick, isBackendOnline, activeTab, setActiveTab }) {
  const { user, profile, updateProfile, openAuthModal, signOut } = useAuth()
  const { watchlist, watchHistory } = useWatchHistory()
  const [isDropdownOpen, setIsDropdownOpen] = useState(false)
  const [isBrowseOpen, setIsBrowseOpen] = useState(false)
  const [isScrolled, setIsScrolled] = useState(false)

  const [localAvatarId, setLocalAvatarId] = useState(() => {
    try {
      return localStorage.getItem('cineforge_user_avatar') || 'director'
    } catch {
      return 'director'
    }
  })

  // Prefer Supabase cloud profile avatar, fallback to local
  const activeAvatarId = profile?.avatar_id || localAvatarId

  const handleSelectAvatar = (id) => {
    setLocalAvatarId(id)
    try {
      localStorage.setItem('cineforge_user_avatar', id)
    } catch {
      // Ignore storage errors
    }
    if (updateProfile && user) {
      updateProfile({ avatarId: id })
    }
  }

  const currentAvatar = AVATAR_PRESETS.find((a) => a.id === activeAvatarId) || AVATAR_PRESETS[0]
  
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
            <div className="nav-profile-avatar-wrap" style={{ background: currentAvatar.gradient }}>
              <span className="nav-profile-avatar-emoji">{currentAvatar.icon}</span>
              <span className="nav-profile-beacon" title="Cloud Sync Active" />
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
              <div className="user-hero-avatar" style={{ background: currentAvatar.gradient }}>
                <span className="user-hero-avatar-emoji">{currentAvatar.icon}</span>
                <span className="user-hero-status-beacon" />
              </div>
              <div className="user-hero-info">
                <strong className="user-hero-name">{displayName}</strong>
                <span className="user-hero-email" title={user.email}>{user.email}</span>
                <div className="user-hero-badge">
                  <span className="user-status-dot" />
                  <span>Cloud Sync Active</span>
                </div>
              </div>
            </div>

            {/* Cinema Persona / Avatar Strip */}
            <div className="user-avatar-selector-section">
              <div className="user-avatar-section-title">
                <span>Cinema Persona</span>
                <small>Select avatar</small>
              </div>
              <div className="user-avatar-grid">
                {AVATAR_PRESETS.map((avatar) => (
                  <button
                    key={avatar.id}
                    type="button"
                    className={`user-avatar-option ${activeAvatarId === avatar.id ? 'is-selected' : ''}`}
                    style={{ background: avatar.gradient }}
                    onClick={() => handleSelectAvatar(avatar.id)}
                    title={avatar.label}
                    aria-label={avatar.label}
                  >
                    <span className="avatar-option-emoji">{avatar.icon}</span>
                    {activeAvatarId === avatar.id && (
                      <span className="avatar-option-check">
                        <Check size={9} strokeWidth={3} />
                      </span>
                    )}
                  </button>
                ))}
              </div>
            </div>

            {/* Quick Library Shortcuts */}
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
                  <Bookmark size={14} />
                </div>
                <div className="shortcut-meta">
                  <strong className="shortcut-number">{watchlist.length}</strong>
                  <span className="shortcut-name">Watchlist</span>
                </div>
              </button>

              <button
                type="button"
                className="user-shortcut-card"
                onClick={() => {
                  setActiveTab('history')
                  setIsDropdownOpen(false)
                }}
              >
                <div className="shortcut-icon-wrap history">
                  <History size={14} />
                </div>
                <div className="shortcut-meta">
                  <strong className="shortcut-number">{watchHistory.length}</strong>
                  <span className="shortcut-name">History</span>
                </div>
              </button>
            </div>

            {/* System Status & Sign Out */}
            <div className="user-profile-footer">
              <div className="user-system-row">
                <span className="system-row-label">Engine Service</span>
                <span className={`system-row-pill ${isBackendOnline ? 'online' : 'offline'}`}>
                  <span className="system-dot" />
                  {isBackendOnline ? 'Operational' : 'Connecting'}
                </span>
              </div>

              <button
                type="button"
                className="user-signout-button"
                onClick={() => {
                  signOut()
                  setIsDropdownOpen(false)
                }}
              >
                <LogOut size={13} />
                <span>Sign Out</span>
              </button>
            </div>
          </div>
        )}
      </div>
    </header>
  )
}
