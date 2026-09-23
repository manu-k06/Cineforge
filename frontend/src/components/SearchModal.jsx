import React, { useState, useEffect, useRef } from 'react'
import { Search, X, Loader2, Film, Star, ChevronDown, Check } from 'lucide-react'
import { getSearchSuggestions } from '../services/api'

const QUICK_SUGGESTIONS = [
  'Avengers',
  'Oppenheimer',
  'Interstellar',
  'Dark Knight',
  'Dune',
  'Spider-Man',
  'Breaking Bad',
  'Inception',
]

const FILTER_OPTIONS = [
  { id: 'all', label: 'Movies & TV' },
  { id: 'movie', label: 'Movies' },
  { id: 'tv', label: 'TV Shows' },
]

export default function SearchModal({ isOpen, onClose, onSearch, onSelectMovie }) {
  const [query, setQuery] = useState('')
  const [selectedFilter, setSelectedFilter] = useState(FILTER_OPTIONS[0])
  const [isFilterOpen, setIsFilterOpen] = useState(false)
  const [suggestions, setSuggestions] = useState([])
  const [isLoadingSuggestions, setIsLoadingSuggestions] = useState(false)
  const inputRef = useRef(null)
  const filterRef = useRef(null)

  // Focus input automatically when modal opens
  useEffect(() => {
    if (isOpen) {
      setTimeout(() => {
        inputRef.current?.focus()
      }, 80)
    } else {
      setQuery('')
      setSuggestions([])
      setIsFilterOpen(false)
    }
  }, [isOpen])

  // Close modal on Escape key
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'Escape') {
        if (isFilterOpen) {
          setIsFilterOpen(false)
        } else {
          onClose()
        }
      }
    }
    if (isOpen) {
      window.addEventListener('keydown', handleKeyDown)
    }
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [isOpen, isFilterOpen, onClose])

  // Close filter dropdown on outside click
  useEffect(() => {
    const handleClickOutside = (e) => {
      if (filterRef.current && !filterRef.current.contains(e.target)) {
        setIsFilterOpen(false)
      }
    }
    if (isFilterOpen) {
      document.addEventListener('mousedown', handleClickOutside)
    }
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [isFilterOpen])

  // Debounced live autocomplete
  useEffect(() => {
    const trimmed = query.trim()
    if (trimmed.length < 2) {
      setSuggestions([])
      return
    }

    const timer = setTimeout(async () => {
      setIsLoadingSuggestions(true)
      try {
        const results = await getSearchSuggestions(trimmed, 6)
        let filtered = results
        if (selectedFilter.id === 'movie') {
          filtered = results.filter((r) => r.media_type?.toLowerCase().includes('movie'))
        } else if (selectedFilter.id === 'tv') {
          filtered = results.filter((r) => r.media_type?.toLowerCase().includes('tv') || r.media_type?.toLowerCase().includes('show'))
        }
        setSuggestions(filtered)
      } catch {
        setSuggestions([])
      } finally {
        setIsLoadingSuggestions(false)
      }
    }, 180)

    return () => clearTimeout(timer)
  }, [query, selectedFilter])

  if (!isOpen) return null

  const handleSubmit = (e) => {
    e?.preventDefault()
    if (query.trim()) {
      onSearch(query.trim())
      onClose()
    }
  }

  const handleSuggestionClick = (item) => {
    if (onSelectMovie) {
      onSelectMovie({
        title: item.title,
        metadata: item,
        candidates: [
          {
            title: item.title,
            display_text: `${item.title} (${item.year || '2024'}) - 1080P Multi-Audio`,
            quality: '1080P',
            language: 'Multi-Audio',
          },
        ],
      })
    } else {
      onSearch(item.title)
    }
    onClose()
  }

  const handleChipClick = (suggestion) => {
    setQuery(suggestion)
    onSearch(suggestion)
    onClose()
  }

  return (
    <div className="search-modal-backdrop" onClick={onClose} role="dialog" aria-modal="true">
      <div
        className="search-modal-card"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Modal Header */}
        <div className="search-modal-header">
          <h3 className="search-modal-title">Search the library</h3>
          <button
            type="button"
            className="search-modal-close-btn"
            onClick={onClose}
            aria-label="Close search"
          >
            ✕
          </button>
        </div>

        {/* Input Row */}
        <form className="search-modal-input-row" onSubmit={handleSubmit}>
          <div className="search-modal-input-box">
            <Search size={18} className="search-modal-search-icon" />
            <input
              ref={inputRef}
              type="text"
              className="search-modal-input"
              placeholder="Search movies and TV shows"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
            />
            {query && (
              <button
                type="button"
                className="search-modal-clear-btn"
                onClick={() => setQuery('')}
                title="Clear input"
              >
                <X size={15} />
              </button>
            )}
          </div>

          {/* Filter Dropdown Pill */}
          <div className="search-filter-dropdown-wrap" ref={filterRef}>
            <button
              type="button"
              className="search-filter-btn"
              onClick={() => setIsFilterOpen((prev) => !prev)}
              aria-expanded={isFilterOpen}
            >
              <span>{selectedFilter.label}</span>
              <ChevronDown size={14} className={isFilterOpen ? 'rotate-180' : ''} />
            </button>

            {isFilterOpen && (
              <div className="search-filter-menu">
                {FILTER_OPTIONS.map((opt) => (
                  <button
                    key={opt.id}
                    type="button"
                    className={`search-filter-item ${opt.id === selectedFilter.id ? 'is-active' : ''}`}
                    onClick={() => {
                      setSelectedFilter(opt)
                      setIsFilterOpen(false)
                    }}
                  >
                    <span>{opt.label}</span>
                    {opt.id === selectedFilter.id && <Check size={14} className="text-ember" />}
                  </button>
                ))}
              </div>
            )}
          </div>
        </form>

        {/* Subtext info */}
        <p className="search-modal-subtext">Search by a title, person, or collection.</p>

        {/* Live Instant Results */}
        {isLoadingSuggestions && (
          <div className="search-modal-loading">
            <Loader2 size={18} className="animate-spin text-ember" />
            <span>Searching titles...</span>
          </div>
        )}

        {suggestions.length > 0 && (
          <div className="search-modal-results">
            {suggestions.map((item) => (
              <div
                key={item.id || item.title}
                className="search-modal-result-item"
                onClick={() => handleSuggestionClick(item)}
              >
                {item.poster_url ? (
                  <img
                    src={item.poster_url}
                    alt={item.title}
                    className="search-result-poster"
                    loading="lazy"
                  />
                ) : (
                  <div className="search-result-poster-fallback">
                    <Film size={18} opacity={0.4} />
                  </div>
                )}
                <div className="search-result-info">
                  <strong className="search-result-title">{item.title}</strong>
                  <div className="search-result-meta">
                    {item.rating && (
                      <span className="search-result-rating">
                        <Star size={11} fill="currentColor" /> {item.rating}
                      </span>
                    )}
                    {item.year && <span>{item.year}</span>}
                    {item.media_type && (
                      <span className="search-result-badge">{item.media_type}</span>
                    )}
                  </div>
                </div>
                <button
                  type="button"
                  className="search-result-action-btn"
                  onClick={(e) => {
                    e.stopPropagation()
                    handleSuggestionClick(item)
                  }}
                >
                  Play
                </button>
              </div>
            ))}
          </div>
        )}

        {/* Quick Search Chips */}
        {suggestions.length === 0 && !isLoadingSuggestions && (
          <div className="search-modal-quick-chips">
            <span className="quick-chips-label">Quick search:</span>
            <div className="quick-chips-list">
              {QUICK_SUGGESTIONS.map((item) => (
                <button
                  key={item}
                  type="button"
                  className="quick-chip-button"
                  onClick={() => handleChipClick(item)}
                >
                  {item}
                </button>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
