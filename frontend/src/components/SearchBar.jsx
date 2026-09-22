import React, { useState, useEffect, useRef } from 'react'
import { Search, X, Loader2, Sparkles, Film, Star } from 'lucide-react'
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

export default function SearchBar({ onSearch, isLoading, currentQuery }) {
  const [inputValue, setInputValue] = useState(currentQuery || '')
  const [suggestions, setSuggestions] = useState([])
  const [isDropdownOpen, setIsDropdownOpen] = useState(false)
  const [isFetchingSuggestions, setIsFetchingSuggestions] = useState(false)
  const containerRef = useRef(null)

  // Sync input value if external currentQuery changes
  useEffect(() => {
    if (currentQuery && currentQuery !== inputValue) {
      setInputValue(currentQuery)
    }
  }, [currentQuery])

  // Debounced live autocomplete query to TMDb
  useEffect(() => {
    const trimmed = inputValue.trim()
    if (trimmed.length < 2) {
      setSuggestions([])
      setIsDropdownOpen(false)
      return
    }

    const timer = setTimeout(async () => {
      setIsFetchingSuggestions(true)
      try {
        const results = await getSearchSuggestions(trimmed, 5)
        setSuggestions(results)
        setIsDropdownOpen(results.length > 0)
      } catch {
        setSuggestions([])
        setIsDropdownOpen(false)
      } finally {
        setIsFetchingSuggestions(false)
      }
    }, 220)

    return () => clearTimeout(timer)
  }, [inputValue])

  // Close dropdown on outside click
  useEffect(() => {
    const handleClickOutside = (e) => {
      if (containerRef.current && !containerRef.current.contains(e.target)) {
        setIsDropdownOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  const handleSubmit = (e) => {
    e?.preventDefault()
    setIsDropdownOpen(false)
    if (inputValue.trim()) {
      onSearch(inputValue.trim())
    }
  }

  const handleSelectSuggestion = (item) => {
    const titleToSearch = item.title
    setInputValue(titleToSearch)
    setIsDropdownOpen(false)
    onSearch(titleToSearch)
  }

  const handleClear = () => {
    setInputValue('')
    setSuggestions([])
    setIsDropdownOpen(false)
  }

  const handleChipClick = (suggestion) => {
    setInputValue(suggestion)
    setIsDropdownOpen(false)
    onSearch(suggestion)
  }

  return (
    <div className="search-section" ref={containerRef}>
      <div className="search-wrapper">
        <form className="search-bar-container" onSubmit={handleSubmit}>
          <div className="search-icon-wrapper">
            <Search size={20} className="text-muted" />
          </div>
          <input
            type="text"
            className="search-input"
            placeholder="Search movies, series, anime, or 4K releases..."
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onFocus={() => {
              if (suggestions.length > 0) setIsDropdownOpen(true)
            }}
          />
          {inputValue && (
            <button
              type="button"
              className="search-clear-btn"
              onClick={handleClear}
              title="Clear"
            >
              <X size={16} />
            </button>
          )}
          <button
            type="submit"
            className="btn btn-primary btn-search-submit"
            disabled={isLoading || !inputValue.trim()}
          >
            {isLoading ? (
              <>
                <Loader2 size={16} className="animate-spin" />
                <span>Searching</span>
              </>
            ) : (
              <span>Search</span>
            )}
          </button>
        </form>

        {/* Live TMDb Autocomplete Suggestions Dropdown */}
        {isDropdownOpen && suggestions.length > 0 && (
          <div className="search-autocomplete-dropdown">
            <div className="autocomplete-header">
              <span className="autocomplete-title">Verified Titles (TMDb)</span>
              {isFetchingSuggestions && <Loader2 size={12} className="animate-spin text-muted" />}
            </div>
            {suggestions.map((item) => (
              <button
                key={item.id || item.title}
                type="button"
                className="search-suggestion-item"
                onClick={() => handleSelectSuggestion(item)}
              >
                {item.poster_url ? (
                  <img
                    src={item.poster_url}
                    alt={item.title}
                    className="suggestion-poster"
                    loading="lazy"
                  />
                ) : (
                  <div className="suggestion-poster-placeholder">
                    <Film size={18} />
                  </div>
                )}
                <div className="suggestion-info">
                  <span className="suggestion-title">{item.title}</span>
                  <div className="suggestion-meta">
                    {item.year && <span className="suggestion-badge-year">{item.year}</span>}
                    {item.rating && (
                      <span className="suggestion-rating">
                        <Star size={11} fill="#f59e0b" /> {item.rating}
                      </span>
                    )}
                  </div>
                </div>
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Suggestion Chips */}
      <div className="search-suggestions">
        <span className="suggestions-label">
          <Sparkles size={13} className="text-red" /> Quick search:
        </span>
        <div className="chips-list">
          {QUICK_SUGGESTIONS.map((item) => (
            <button
              key={item}
              className={`chip ${currentQuery === item ? 'active' : ''}`}
              onClick={() => handleChipClick(item)}
            >
              {item}
            </button>
          ))}
        </div>
      </div>
    </div>
  )
}
