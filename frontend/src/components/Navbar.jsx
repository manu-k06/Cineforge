import React, { useState, useRef, useEffect } from 'react'
import { Play, Search, Bell, AlertCircle, LogIn, LogOut, Bookmark, History, Sparkles } from 'lucide-react'
import { useAuth } from '../context/AuthContext'

export default function Navbar({ onSearchClick, isBackendOnline, activeTab, setActiveTab }) {
  const { user, openAuthModal, signOut } = useAuth()
  const [isDropdownOpen, setIsDropdownOpen] = useState(false)
  const [isScrolled, setIsScrolled] = useState(false)
  const dropdownRef = useRef(null)

  // Track scroll position to transition navbar from transparent to frosted blur
  useEffect(() => {
    const handleScroll = () => {
      setIsScrolled(window.scrollY > 20)
    }
    window.addEventListener('scroll', handleScroll, { passive: true })
    return () => window.removeEventListener('scroll', handleScroll)
  }, [])

  // Close dropdown on click outside
  useEffect(() => {
    const handleClickOutside = (e) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target)) {
        setIsDropdownOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  // Derive display initials
  const getInitials = () => {
    if (!user) return 'CF'
    const name = user.user_metadata?.full_name || ''
    if (name) {
      const parts = name.trim().split(' ')
      if (parts.length >= 2) {
        return (parts[0][0] + parts[1][0]).toUpperCase()
      }
      return parts[0].slice(0, 2).toUpperCase()
    }
    return (user.email || 'CF').slice(0, 2).toUpperCase()
  }

  const displayName = user?.user_metadata?.full_name || user?.email?.split('@')[0] || 'Member'

  return (
    <header className={`streamvibe-navbar ${isScrolled ? 'scrolled' : 'transparent-header'}`}>
      <div className="navbar-inner">
        {/* Left Section: Brand Logo + Sleek Navigation Links */}
        <div className="navbar-left">
          <div className="navbar-brand" onClick={() => setActiveTab('home')}>
            <div className="brand-icon">
              <Play className="brand-play" fill="#E50914" size={16} />
            </div>
            <span className="brand-text">
              CINE<span className="brand-accent">FORGE</span>
            </span>
          </div>

          <nav className="navbar-nav-links">
            <button
              className={`nav-tab-link ${activeTab === 'home' ? 'active' : ''}`}
              onClick={() => setActiveTab('home')}
            >
              Home
            </button>
            <button
              className={`nav-tab-link ${activeTab === 'movies' ? 'active' : ''}`}
              onClick={() => setActiveTab('movies')}
            >
              Movies
            </button>
            <button
              className={`nav-tab-link ${activeTab === 'shows' ? 'active' : ''}`}
              onClick={() => setActiveTab('shows')}
            >
              TV Shows
            </button>
            <button
              className={`nav-tab-link ${activeTab === 'trending' ? 'active' : ''}`}
              onClick={() => setActiveTab('trending')}
            >
              Trending
            </button>
          </nav>
        </div>

        {/* Right Section: Search Trigger, Live Node Status, and User Profile */}
        <div className="navbar-right">
          {/* Quick Search Trigger */}
          <button
            className="nav-action-search"
            onClick={onSearchClick}
            title="Search movies, shows, or actors"
            aria-label="Search"
          >
            <Search size={18} />
          </button>

          {/* Node Health Status Indicator */}
          <div
            className={`network-indicator ${isBackendOnline ? 'online' : 'offline'}`}
            title={isBackendOnline ? 'Streaming Nodes Online' : 'Connecting to Stream Nodes...'}
          >
            <span className="indicator-dot"></span>
          </div>

          {/* User Profile / Auth */}
          {user ? (
            <div className="user-profile-container" ref={dropdownRef} style={{ position: 'relative' }}>
              <div
                className="user-avatar"
                title={user.email}
                onClick={() => setIsDropdownOpen(!isDropdownOpen)}
              >
                <div className="avatar-placeholder">
                  {getInitials()}
                </div>
              </div>

              {/* Profile Dropdown Menu */}
              {isDropdownOpen && (
                <div className="navbar-profile-dropdown">
                  <div className="dropdown-user-header">
                    <div className="dropdown-user-name">{displayName}</div>
                    <div className="dropdown-user-email">{user.email}</div>
                  </div>

                  <div className="dropdown-menu-list">
                    <button
                      type="button"
                      className="dropdown-menu-item"
                      onClick={() => setIsDropdownOpen(false)}
                    >
                      <Bookmark size={15} color="#8e95a5" />
                      <span>My Watchlist</span>
                    </button>

                    <button
                      type="button"
                      className="dropdown-menu-item"
                      onClick={() => setIsDropdownOpen(false)}
                    >
                      <History size={15} color="#8e95a5" />
                      <span>Watch History</span>
                    </button>

                    <div className="dropdown-divider" />

                    <button
                      type="button"
                      className="dropdown-menu-item text-danger"
                      onClick={() => {
                        setIsDropdownOpen(false)
                        signOut()
                      }}
                    >
                      <LogOut size={15} />
                      <span>Sign Out</span>
                    </button>
                  </div>
                </div>
              )}
            </div>
          ) : (
            <button
              className="btn-nav-signin"
              onClick={openAuthModal}
            >
              <LogIn size={15} />
              <span>Sign In</span>
            </button>
          )}
        </div>
      </div>
    </header>
  )
}
