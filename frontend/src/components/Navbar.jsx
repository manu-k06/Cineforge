import React, { useState, useRef, useEffect } from 'react'
import { Bookmark, LogOut, User, ChevronDown, UserPlus, Sparkles } from 'lucide-react'
import { useAuth } from '../context/AuthContext'
import { useWatchHistory } from '../context/WatchHistoryContext'
import { getAvatarSrc, getAvatarInfo } from '../utils/avatars'
import AvatarPickerModal from './AvatarPickerModal'

export default function Navbar({ onSearchClick, isBackendOnline, activeTab, setActiveTab }) {
  const { user, profile, openAuthModal, signOut, updateProfile } = useAuth()
  const { watchlist } = useWatchHistory()
  const [isDropdownOpen, setIsDropdownOpen] = useState(false)
  const [isBrowseOpen, setIsBrowseOpen] = useState(false)
  const [isScrolled, setIsScrolled] = useState(false)
  const [isAvatarPickerOpen, setIsAvatarPickerOpen] = useState(false)

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

  const currentAvatarId = profile?.avatar_id || (typeof window !== 'undefined' ? localStorage.getItem('cineforge_user_avatar') : null) || 'spider_man'
  const currentAvatarSrc = getAvatarSrc(currentAvatarId)
  const currentAvatarInfo = getAvatarInfo(currentAvatarId)

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
        />
        <div className="brand-text">
          <span className="brand-title">CINEFORGE</span>
        </div>
      </div>

      {/* Main Navigation Links */}
      <nav className="site-nav" aria-label="Primary navigation">
        <button
          className={`nav-link ${activeTab === 'home' ? 'is-active' : ''}`}
          type="button"
          onClick={() => setActiveTab('home')}
        >
          Home
        </button>

        <button
          className={`nav-link ${activeTab === 'library' ? 'is-active' : ''}`}
          type="button"
          onClick={() => setActiveTab('library')}
        >
          Movies
        </button>

        {/* Series Dropdown */}
        <div className="nav-dropdown" ref={browseRef}>
          <button
            className={`nav-link nav-dropdown-trigger ${activeTab === 'series' ? 'is-active' : ''}`}
            type="button"
            onClick={() => setIsBrowseOpen((prev) => !prev)}
            aria-expanded={isBrowseOpen}
          >
            <span>Series</span>
            <ChevronDown size={14} className={`nav-chevron ${isBrowseOpen ? 'is-rotated' : ''}`} />
          </button>

          {isBrowseOpen && (
            <div className="nav-dropdown-menu">
              <button
                type="button"
                className="dropdown-item"
                onClick={() => {
                  setActiveTab('series')
                  setIsBrowseOpen(false)
                }}
              >
                All Series
              </button>
              <button
                type="button"
                className="dropdown-item"
                onClick={() => {
                  setActiveTab('series')
                  setIsBrowseOpen(false)
                }}
              >
                Anime Series
              </button>
              <button
                type="button"
                className="dropdown-item"
                onClick={() => {
                  setActiveTab('series')
                  setIsBrowseOpen(false)
                }}
              >
                Docuseries
              </button>
            </div>
          )}
        </div>

        <button
          className={`nav-link ${activeTab === 'watchlist' ? 'is-active' : ''}`}
          type="button"
          onClick={() => setActiveTab('watchlist')}
        >
          Watchlist
          {watchlist.length > 0 && (
            <span className="nav-badge">{watchlist.length}</span>
          )}
        </button>

        <button
          className={`nav-link ${activeTab === 'community' ? 'is-active' : ''}`}
          type="button"
          onClick={() => setActiveTab('community')}
        >
          Community
        </button>
      </nav>

      {/* Right Actions: Search + Profile & Auth Menu */}
      <div className="nav-actions">
        <button
          className="search-pill-button"
          type="button"
          onClick={onSearchClick}
          aria-label="Search Cineforge"
          title="Search movies, TV shows, anime (Press /)"
        >
          <span className="search-pill-icon">⌕</span>
          <span className="search-pill-text">Search titles...</span>
          <kbd className="search-pill-shortcut">/</kbd>
        </button>

        <button
          className="icon-button mobile-search-button"
          type="button"
          onClick={onSearchClick}
          aria-label="Search"
          title="Search movies and series"
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
                src={currentAvatarSrc}
                alt={currentAvatarInfo.name}
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
              <div
                style={{ position: 'relative', cursor: 'pointer' }}
                onClick={() => setIsAvatarPickerOpen(true)}
                title="Click to choose a superhero avatar"
              >
                <div className="user-hero-avatar">
                  <img
                    src={currentAvatarSrc}
                    alt={currentAvatarInfo.name}
                    className="user-hero-avatar-img"
                  />
                </div>
                <div
                  style={{
                    position: 'absolute',
                    bottom: '-2px',
                    right: '-2px',
                    width: '18px',
                    height: '18px',
                    borderRadius: '50%',
                    backgroundColor: '#E50000',
                    border: '2px solid #11131a',
                    color: '#ffffff',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    boxShadow: '0 2px 6px rgba(0,0,0,0.5)',
                  }}
                  title="Change superhero avatar"
                >
                  <Sparkles size={10} />
                </div>
              </div>

              <div className="user-hero-info">
                <strong className="user-hero-name">{displayName}</strong>
                <span className="user-hero-email" title={user.email}>{user.email}</span>
                <button
                  type="button"
                  onClick={() => setIsAvatarPickerOpen(true)}
                  style={{
                    background: 'none',
                    border: 'none',
                    color: '#E50000',
                    fontSize: '11px',
                    fontWeight: '600',
                    cursor: 'pointer',
                    padding: '2px 0 0',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '4px',
                  }}
                >
                  <span>Avatar: {currentAvatarInfo.name}</span>
                  <span style={{ fontSize: '10px', opacity: 0.8 }}>✎</span>
                </button>
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

      {/* Superhero Avatar Picker Modal */}
      <AvatarPickerModal
        isOpen={isAvatarPickerOpen}
        onClose={() => setIsAvatarPickerOpen(false)}
        currentAvatarId={currentAvatarId}
        onSelectAvatar={(newAvatarId) => {
          updateProfile({ avatarId: newAvatarId })
        }}
      />
    </header>
  )
}
