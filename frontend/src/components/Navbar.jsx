import React from 'react'
import { Play, Search, Bell, Film, CheckCircle2, AlertCircle } from 'lucide-react'

export default function Navbar({ onSearchClick, isBackendOnline, activeTab, setActiveTab }) {
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
          <button className="btn-icon" title="Notifications">
            <Bell size={18} />
          </button>
          <div className="user-avatar" title="Account">
            <div className="avatar-placeholder">CF</div>
          </div>
        </div>
      </div>
    </header>
  )
}
