import React, { useState } from 'react'
import { Search, X, Loader2, Sparkles } from 'lucide-react'

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

  const handleSubmit = (e) => {
    e?.preventDefault()
    if (inputValue.trim()) {
      onSearch(inputValue.trim())
    }
  }

  const handleClear = () => {
    setInputValue('')
  }

  const handleChipClick = (suggestion) => {
    setInputValue(suggestion)
    onSearch(suggestion)
  }

  return (
    <div className="search-section">
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
