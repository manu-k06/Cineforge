import React, { useState, useRef, useEffect } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { Bookmark, LogOut, User, ChevronDown, UserPlus } from 'lucide-react'
import { useAuth } from '../context/AuthContext'
import { useWatchHistory } from '../context/WatchHistoryContext'
import { getAvatarSrc, getAvatarInfo } from '../utils/avatars'
import AvatarPickerModal from './AvatarPickerModal'
import TelegramConnectModal from './TelegramConnectModal'
import { isDesktopApp, getTelegramAuthStatus } from '../services/api'

export default function Navbar({ onSearchClick, isBackendOnline, activeTab, setActiveTab }) {
  const navigate = useNavigate()
  const location = useLocation()
  const { user, profile, openAuthModal, signOut, updateProfile } = useAuth()
  const { watchlist } = useWatchHistory()
  const [isDropdownOpen, setIsDropdownOpen] = useState(false)
  const [isBrowseOpen, setIsBrowseOpen] = useState(false)
  const [isScrolled, setIsScrolled] = useState(false)
  const [isAvatarPickerOpen, setIsAvatarPickerOpen] = useState(false)
  const [isTelegramModalOpen, setIsTelegramModalOpen] = useState(() => {
    if (typeof window !== 'undefined') {
      const params = new URLSearchParams(window.location.search)
      return params.get('open_telegram') === '1' || params.get('open_qr') === '1'
    }
    return false
  })
  const [telegramStatus, setTelegramStatus] = useState(() => {
    if (typeof window !== 'undefined') {
      const param = new URLSearchParams(window.location.search).get('telegram')
      if (param === 'connected') {
        return {
          connected: true,
          status: 'connected',
          user: { first_name: 'Alex', last_name: 'V', username: 'alex_cineforge', phone: '+1 555 0199' },
        }
      }
    }
    return null
  })

  // Fetch desktop Telegram auth status if running in desktop environment
  useEffect(() => {
    if (isDesktopApp()) {
      getTelegramAuthStatus()
        .then((status) => setTelegramStatus(status))
        .catch(() => {})
    }
  }, [])

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

  const handleNav = (path, tab) => {
    if (setActiveTab) setActiveTab(tab)
    navigate(path)
  }

  return (
    <header className={`site-header ${isScrolled ? 'is-scrolled' : ''}`}>
      {/* Brand: Aperture Mark + Cineforge */}
      <div className="brand" onClick={() => handleNav('/', 'home')} title="Cineforge Home">
        <img
          className="brand-image"
          src="/assets/images/aperture-mark.png"
          alt="Cineforge"
          onError={(e) => {
            e.target.style.display = 'none'
          }}
        />
        <span>Cineforge</span>
      </div>

      {/* Primary Nav */}
      <nav className="primary-nav" aria-label="Primary navigation">
        <button
          className={activeTab === 'home' ? 'is-active' : ''}
          onClick={() => handleNav('/', 'home')}
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
                    handleNav('/movies', 'movies')
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
                    handleNav('/series', 'shows')
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
                    handleNav('/history', 'history')
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
                    handleNav('/watchlist', 'watchlist')
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

        {/* Telegram Connect Pill (Desktop App or preview mode) */}
        {(isDesktopApp() || Boolean(typeof window !== 'undefined' && (new URLSearchParams(window.location.search).get('telegram') || new URLSearchParams(window.location.search).get('open_telegram') || new URLSearchParams(window.location.search).get('open_qr')))) && (
          <button
            type="button"
            data-testid="telegram-connect-btn"
            onClick={() => setIsTelegramModalOpen(true)}
            title={
              telegramStatus?.connected
                ? `Telegram Connected: ${telegramStatus?.user?.first_name || 'Account'} (${telegramStatus?.user?.username ? '@' + telegramStatus.user.username : 'Active'})`
                : 'Connect your personal Telegram account'
            }
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '7px',
              padding: '6px 14px',
              borderRadius: '20px',
              border: `1px solid ${telegramStatus?.connected ? 'rgba(34, 197, 94, 0.3)' : 'rgba(0, 136, 204, 0.3)'}`,
              backgroundColor: telegramStatus?.connected ? 'rgba(34, 197, 94, 0.12)' : 'rgba(0, 136, 204, 0.12)',
              color: telegramStatus?.connected ? '#4ade80' : '#38bdf8',
              fontSize: '0.82rem',
              fontWeight: 500,
              cursor: 'pointer',
              transition: 'all 0.2s ease',
            }}
          >
            <span
              style={{
                width: '7px',
                height: '7px',
                borderRadius: '50%',
                backgroundColor: telegramStatus?.connected ? '#22c55e' : '#0284c7',
                boxShadow: telegramStatus?.connected ? '0 0 6px #22c55e' : 'none',
                display: 'inline-block',
              }}
            />
            <span>
              {telegramStatus?.connected
                ? (telegramStatus?.user?.first_name || 'Telegram')
                : 'Connect Telegram'}
            </span>
          </button>
        )}

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
            onClick={() => {
              const currentPath = location.pathname + location.search
              const redirectParam = !currentPath.startsWith('/login') && !currentPath.startsWith('/signup')
                ? `?redirect=${encodeURIComponent(currentPath)}`
                : ''
              navigate(`/login${redirectParam}`)
            }}
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
                className="user-hero-avatar"
                onClick={() => setIsAvatarPickerOpen(true)}
                style={{ cursor: 'pointer' }}
                title="Click to choose a superhero avatar"
              >
                <img
                  src={currentAvatarSrc}
                  alt={currentAvatarInfo.name}
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
                  handleNav('/watchlist', 'watchlist')
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
                  const currentPath = location.pathname + location.search
                  const redirectParam = !currentPath.startsWith('/login') && !currentPath.startsWith('/signup')
                    ? `?redirect=${encodeURIComponent(currentPath)}`
                    : ''
                  navigate(`/login${redirectParam}`)
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

      {/* Telegram Connect Modal (Desktop App) */}
      <TelegramConnectModal
        isOpen={isTelegramModalOpen}
        onClose={() => setIsTelegramModalOpen(false)}
        onStatusChange={(status) => setTelegramStatus(status)}
      />
    </header>
  )
}
