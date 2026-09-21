import React, { useState, useRef, useEffect } from 'react'
import { Play, Search, Bell, AlertCircle, LogIn, LogOut, Bookmark, History, User as UserIcon } from 'lucide-react'
import { useAuth } from '../context/AuthContext'

export default function Navbar({ onSearchClick, isBackendOnline, activeTab, setActiveTab }) {
  const { user, openAuthModal, signOut } = useAuth()
  const [isDropdownOpen, setIsDropdownOpen] = useState(false)
  const dropdownRef = useRef(null)

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
    <header className="streamvibe-navbar">
      <div className="navbar-inner">
        {/* Brand Logo */}
        <div className="navbar-brand" onClick={() => setActiveTab('home')}>
          <div className="brand-icon">
            <Play className="brand-play" fill="#E50000" size={18} />
          </div>
          <span className="brand-text">
            CINE<span className="brand-accent">FORGE</span>
          </span>
        </div>

        {/* Navigation Tabs */}
        <nav className="navbar-nav">
          <button 
            className={`nav-link ${activeTab === 'home' ? 'active' : ''}`}
            onClick={() => setActiveTab('home')}
          >
            Home
          </button>
          <button 
            className={`nav-link ${activeTab === 'movies' ? 'active' : ''}`}
            onClick={() => setActiveTab('movies')}
          >
            Movies
          </button>
          <button 
            className={`nav-link ${activeTab === 'shows' ? 'active' : ''}`}
            onClick={() => setActiveTab('shows')}
          >
            TV Shows
          </button>
          <button 
            className={`nav-link ${activeTab === 'trending' ? 'active' : ''}`}
            onClick={() => setActiveTab('trending')}
          >
            Trending
          </button>
        </nav>

        {/* Right Actions */}
        <div className="navbar-actions">
          {/* Status badge */}
          <div className={`backend-status ${isBackendOnline ? 'online' : 'offline'}`} title={isBackendOnline ? 'FastAPI & Bot Connected' : 'Connecting to Backend...'}>
            {isBackendOnline ? (
              <>
                <span className="status-dot"></span>
                <span className="status-label">Bot Live</span>
              </>
            ) : (
              <>
                <AlertCircle size={14} className="text-warning" />
                <span className="status-label">Reconnecting</span>
              </>
            )}
          </div>

          <button className="btn-icon" onClick={onSearchClick} title="Search library">
            <Search size={18} />
          </button>

          {/* User Auth Section */}
          {user ? (
            <div className="user-profile-container" ref={dropdownRef} style={{ position: 'relative' }}>
              <div 
                className="user-avatar" 
                title={user.email}
                onClick={() => setIsDropdownOpen(!isDropdownOpen)}
                style={{ cursor: 'pointer', border: '2px solid rgba(229, 0, 0, 0.4)' }}
              >
                <div className="avatar-placeholder" style={{ background: 'linear-gradient(135deg, #E50000, #7800ff)', color: '#fff', fontWeight: 'bold' }}>
                  {getInitials()}
                </div>
              </div>

              {/* Profile Dropdown Menu */}
              {isDropdownOpen && (
                <div
                  style={{
                    position: 'absolute',
                    top: 'calc(100% + 10px)',
                    right: 0,
                    width: '240px',
                    backgroundColor: '#11131a',
                    border: '1px solid rgba(255, 255, 255, 0.12)',
                    borderRadius: '12px',
                    boxShadow: '0 12px 30px rgba(0, 0, 0, 0.6), 0 0 20px rgba(229, 0, 0, 0.1)',
                    zIndex: 1000,
                    overflow: 'hidden',
                  }}
                >
                  {/* User info banner */}
                  <div style={{ padding: '14px 16px', borderBottom: '1px solid rgba(255, 255, 255, 0.08)' }}>
                    <div style={{ fontSize: '14px', fontWeight: '600', color: '#ffffff' }}>{displayName}</div>
                    <div style={{ fontSize: '12px', color: '#8e95a5', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {user.email}
                    </div>
                  </div>

                  {/* Menu actions */}
                  <div style={{ padding: '6px' }}>
                    <button
                      type="button"
                      onClick={() => {
                        setIsDropdownOpen(false)
                        // Trigger watchlist tab/view when available
                      }}
                      style={{
                        width: '100%',
                        padding: '9px 12px',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '10px',
                        backgroundColor: 'transparent',
                        border: 'none',
                        color: '#c5c9d3',
                        fontSize: '13px',
                        cursor: 'pointer',
                        borderRadius: '6px',
                        textAlign: 'left',
                        transition: 'background-color 0.2s',
                      }}
                      onMouseEnter={(e) => (e.currentTarget.style.backgroundColor = 'rgba(255, 255, 255, 0.05)')}
                      onMouseLeave={(e) => (e.currentTarget.style.backgroundColor = 'transparent')}
                    >
                      <Bookmark size={15} color="#8e95a5" />
                      <span>My Watchlist</span>
                      <span style={{ marginLeft: 'auto', fontSize: '10px', background: 'rgba(255, 255, 255, 0.08)', padding: '2px 6px', borderRadius: '4px', color: '#8e95a5' }}>
                        Phase 5
                      </span>
                    </button>

                    <button
                      type="button"
                      onClick={() => {
                        setIsDropdownOpen(false)
                        // Trigger history tab/view when available
                      }}
                      style={{
                        width: '100%',
                        padding: '9px 12px',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '10px',
                        backgroundColor: 'transparent',
                        border: 'none',
                        color: '#c5c9d3',
                        fontSize: '13px',
                        cursor: 'pointer',
                        borderRadius: '6px',
                        textAlign: 'left',
                        transition: 'background-color 0.2s',
                      }}
                      onMouseEnter={(e) => (e.currentTarget.style.backgroundColor = 'rgba(255, 255, 255, 0.05)')}
                      onMouseLeave={(e) => (e.currentTarget.style.backgroundColor = 'transparent')}
                    >
                      <History size={15} color="#8e95a5" />
                      <span>Watch History</span>
                      <span style={{ marginLeft: 'auto', fontSize: '10px', background: 'rgba(255, 255, 255, 0.08)', padding: '2px 6px', borderRadius: '4px', color: '#8e95a5' }}>
                        Phase 5
                      </span>
                    </button>

                    <div style={{ height: '1px', backgroundColor: 'rgba(255, 255, 255, 0.08)', margin: '4px 0' }} />

                    <button
                      onClick={() => {
                        setIsDropdownOpen(false)
                        signOut()
                      }}
                      style={{
                        width: '100%',
                        padding: '9px 12px',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '10px',
                        backgroundColor: 'transparent',
                        border: 'none',
                        color: '#ff6666',
                        fontSize: '13px',
                        cursor: 'pointer',
                        borderRadius: '6px',
                        textAlign: 'left',
                        transition: 'background-color 0.2s',
                      }}
                      onMouseEnter={(e) => (e.currentTarget.style.backgroundColor = 'rgba(229, 0, 0, 0.1)')}
                      onMouseLeave={(e) => (e.currentTarget.style.backgroundColor = 'transparent')}
                    >
                      <LogOut size={16} />
                      <span>Sign Out</span>
                    </button>
                  </div>
                </div>
              )}

            </div>
          ) : (
            <button
              onClick={openAuthModal}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                backgroundColor: '#E50000',
                color: '#ffffff',
                border: 'none',
                padding: '7px 14px',
                borderRadius: '8px',
                fontSize: '13px',
                fontWeight: '600',
                cursor: 'pointer',
                boxShadow: '0 2px 8px rgba(229, 0, 0, 0.3)',
                transition: 'all 0.2s',
              }}
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
