import React from 'react'
import { Film, AlertCircle, ChevronLeft, ChevronRight, Loader2, Sparkles, TrendingUp } from 'lucide-react'
import MovieCard from './MovieCard'

export default function MovieGrid({
  items,
  groupedItems,
  isLoading,
  searchQuery,
  page,
  totalPages,
  hasNextPage,
  onPageChange,
  onSelectMovie,
  onQuickSearch,
}) {
  if (isLoading) {
    return (
      <div className="grid-section">
        <div className="section-header">
          <h2 className="section-title">Searching Telegram Bot...</h2>
          <span className="badge badge-red animate-pulse">
            <Loader2 size={12} className="animate-spin" /> Querying @Spoty_xbot
          </span>
        </div>
        <div className="movie-grid">
          {[1, 2, 3, 4, 5, 6, 7, 8].map((i) => (
            <div key={i} className="movie-card skeleton-card">
              <div className="skeleton skeleton-poster"></div>
              <div className="skeleton-details">
                <div className="skeleton skeleton-title"></div>
                <div className="skeleton skeleton-subtitle"></div>
              </div>
            </div>
          ))}
        </div>
      </div>
    )
  }

  // Active search with results
  if (searchQuery && items && items.length > 0) {
    return (
      <div className="grid-section">
        <div className="section-header">
          <div>
            <h2 className="section-title">
              Results for <span className="text-red">"{searchQuery}"</span>
            </h2>
            <p className="section-subtitle">
              Found {items.length} releases from Spoty Bot
            </p>
          </div>

          {/* Pagination controls */}
          {totalPages > 1 && (
            <div className="pagination-controls">
              <button
                className="btn btn-secondary btn-sm"
                disabled={page <= 1}
                onClick={() => onPageChange(page - 1)}
              >
                <ChevronLeft size={16} /> Prev
              </button>
              <span className="page-indicator">
                Page {page} of {totalPages}
              </span>
              <button
                className="btn btn-secondary btn-sm"
                disabled={!hasNextPage}
                onClick={() => onPageChange(page + 1)}
              >
                Next <ChevronRight size={16} />
              </button>
            </div>
          )}
        </div>

        <div className="movie-grid">
          {groupedItems.map((group, idx) => (
            <MovieCard
              key={idx}
              group={group}
              onSelect={onSelectMovie}
            />
          ))}
        </div>
      </div>
    )
  }

  // Active search with no results
  if (searchQuery && items && items.length === 0) {
    return (
      <div className="empty-state">
        <div className="empty-icon-wrapper">
          <AlertCircle size={48} className="text-muted" />
        </div>
        <h3 className="empty-title">No releases found for "{searchQuery}"</h3>
        <p className="empty-description">
          Check your spelling or try searching for another title, like "Avengers", "Interstellar", or "Oppenheimer".
        </p>
      </div>
    )
  }

  // Default Home State: Curated Discovery Sections
  const CURATED_CATEGORIES = [
    {
      title: 'Trending Blockbusters',
      tag: 'HOT PICKS',
      movies: [
        { title: 'Avengers Endgame (2019)', details: '2.4GB - 1080p HEVC Dual Audio' },
        { title: 'Dune Part Two (2024)', details: '3.1GB - 1080p Web-DL Multi Audio' },
        { title: 'Oppenheimer (2023)', details: '4.2GB - 4K UHD HDR Remux' },
        { title: 'Interstellar (2014)', details: '2.8GB - 1080p BluRay' },
      ],
    },
    {
      title: 'Top Rated Sci-Fi & Action',
      tag: 'HIGH BITRATE',
      movies: [
        { title: 'The Dark Knight (2008)', details: '2.1GB - 1080p Dual Audio' },
        { title: 'Inception (2010)', details: '1.9GB - 1080p HEVC' },
        { title: 'Spider-Man No Way Home (2021)', details: '2.6GB - 1080p FHD' },
        { title: 'The Matrix (1999)', details: '2.0GB - Remastered 1080p' },
      ],
    },
  ]

  return (
    <div className="curated-sections">
      {CURATED_CATEGORIES.map((cat, catIdx) => (
        <div key={catIdx} className="grid-section">
          <div className="section-header">
            <div>
              <div className="badge badge-red mb-2">
                <TrendingUp size={12} /> {cat.tag}
              </div>
              <h2 className="section-title">{cat.title}</h2>
            </div>
          </div>

          <div className="movie-grid">
            {cat.movies.map((m, idx) => (
              <div
                key={idx}
                className="curated-card"
                onClick={() => onQuickSearch(m.title.replace(/\s*\(\d+\)/, ''))}
              >
                <MovieCard
                  group={{
                    title: m.title,
                    candidates: [{ title: m.title, details: m.details }],
                  }}
                  onSelect={() => onQuickSearch(m.title.replace(/\s*\(\d+\)/, ''))}
                />
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  )
}
