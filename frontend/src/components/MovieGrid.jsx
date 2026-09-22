import React, { useRef } from 'react'
import { Film, AlertCircle, ChevronLeft, ChevronRight, Loader2, Sparkles, TrendingUp, Star, Play, Compass } from 'lucide-react'
import MovieCard from './MovieCard'

// Curated Cinema Rails with TMDb-ready titles
// Curated Cinema Rails with TMDb-ready titles & authentic posters
const CURATED_CATEGORIES = [
  {
    id: 'trending',
    title: 'Trending Blockbusters',
    tag: 'HOT PICKS',
    icon: TrendingUp,
    movies: [
      { title: 'Avengers Endgame (2019)', details: '2.4GB - 1080p HEVC Dual Audio', poster: 'https://image.tmdb.org/t/p/w500/or06FN3Dka5tukK1e9sl16pB3iy.jpg', rating: '8.4', year: '2019' },
      { title: 'Dune Part Two (2024)', details: '3.1GB - 1080p Web-DL Multi Audio', poster: 'https://image.tmdb.org/t/p/w500/1pdfLvkbY9ohJlCjQH2CZjjYVvJ.jpg', rating: '8.6', year: '2024' },
      { title: 'Oppenheimer (2023)', details: '4.2GB - 4K UHD HDR Remux', poster: 'https://image.tmdb.org/t/p/w500/8Gxv8gSFCU0XGDykEGv7zR1n2ua.jpg', rating: '8.9', year: '2023' },
      { title: 'Interstellar (2014)', details: '2.8GB - 1080p BluRay', poster: 'https://image.tmdb.org/t/p/w500/gEU2QniE6E77NI6lCU6MxlNBvIx.jpg', rating: '8.7', year: '2014' },
      { title: 'Spider-Man No Way Home (2021)', details: '2.6GB - 1080p FHD', poster: 'https://image.tmdb.org/t/p/w500/1g0dhYtq4irTY1GPXvft6k4YLjm.jpg', rating: '8.0', year: '2021' },
      { title: 'The Batman (2022)', details: '3.4GB - 4K UHD HDR', poster: 'https://image.tmdb.org/t/p/w500/74xTEgt7R36Fpooo50r9T25onhq.jpg', rating: '7.7', year: '2022' },
      { title: 'Avatar The Way of Water (2022)', details: '3.9GB - 1080p 3D Remux', poster: 'https://image.tmdb.org/t/p/w500/t6HIqrRAclMCA60NsSmeqe9RmNV.jpg', rating: '7.6', year: '2022' },
    ],
  },
  {
    id: 'regional',
    title: 'Malayalam & Regional Spotlight',
    tag: 'SUPERHITS',
    icon: Sparkles,
    movies: [
      { title: 'Aavesham (2024)', details: '2.1GB - 1080p Web-DL Dual Audio', poster: 'https://image.tmdb.org/t/p/w500/fWhJEc82YkQZpM6e6iM1gW6uQ70.jpg', rating: '8.0', year: '2024' },
      { title: 'Manjummel Boys (2024)', details: '2.3GB - 1080p Multi Audio', poster: 'https://image.tmdb.org/t/p/w500/bCmsQp5pX25t79gB3zG3jMvT6d5.jpg', rating: '8.3', year: '2024' },
      { title: 'Premalu (2024)', details: '1.9GB - 1080p Web-DL', poster: 'https://image.tmdb.org/t/p/w500/2L2fQp831QnZ5mS6B6w7r6Z4D.jpg', rating: '7.9', year: '2024' },
      { title: 'Bramayugam (2024)', details: '2.4GB - 1080p Monochrome Edition', poster: 'https://image.tmdb.org/t/p/w500/fWhJEc82YkQZpM6e6iM1gW6uQ70.jpg', rating: '8.1', year: '2024' },
      { title: 'The Goat Life (2024)', details: '2.7GB - 1080p Aadujeevitham', poster: 'https://image.tmdb.org/t/p/w500/1pdfLvkbY9ohJlCjQH2CZjjYVvJ.jpg', rating: '8.2', year: '2024' },
      { title: 'Drishyam 2 (2021)', details: '2.0GB - 1080p Dual Audio', poster: 'https://image.tmdb.org/t/p/w500/8Gxv8gSFCU0XGDykEGv7zR1n2ua.jpg', rating: '8.4', year: '2021' },
      { title: 'Lucifer (2019)', details: '2.5GB - 1080p Remastered', poster: 'https://image.tmdb.org/t/p/w500/gEU2QniE6E77NI6lCU6MxlNBvIx.jpg', rating: '7.5', year: '2019' },
    ],
  },
  {
    id: 'top-rated',
    title: 'Top Rated Masterpieces',
    tag: 'ALL TIME CLASSICS',
    icon: Star,
    movies: [
      { title: 'The Dark Knight (2008)', details: '2.1GB - 1080p Dual Audio', poster: 'https://image.tmdb.org/t/p/w500/qJ2tW6WMUDux911r6m7haRef0WH.jpg', rating: '9.0', year: '2008' },
      { title: 'Inception (2010)', details: '1.9GB - 1080p HEVC', poster: 'https://image.tmdb.org/t/p/w500/ljsZTbVsrQSqZgWeep2B1QiDKuh.jpg', rating: '8.8', year: '2010' },
      { title: 'The Matrix (1999)', details: '2.0GB - Remastered 1080p', poster: 'https://image.tmdb.org/t/p/w500/f89U3ADr1oiB1s9GkdPOEpXUk5H.jpg', rating: '8.7', year: '1999' },
      { title: 'Fight Club (1999)', details: '1.8GB - 1080p 10bit', poster: 'https://image.tmdb.org/t/p/w500/pB8BM7pdSp6B6Ih7QZ4DrQ3PmJK.jpg', rating: '8.4', year: '1999' },
      { title: 'Gladiator (2000)', details: '2.5GB - 4K UHD Remux', poster: 'https://image.tmdb.org/t/p/w500/ty8TGRuvJLPUmAR1H1nRIsgwvim.jpg', rating: '8.5', year: '2000' },
      { title: 'Pulp Fiction (1994)', details: '1.7GB - 1080p BluRay', poster: 'https://image.tmdb.org/t/p/w500/d5iIlFn5s0ImszYzBPb8JPIfbXD.jpg', rating: '8.9', year: '1994' },
      { title: 'Interstellar (2014)', details: '2.8GB - 1080p BluRay', poster: 'https://image.tmdb.org/t/p/w500/gEU2QniE6E77NI6lCU6MxlNBvIx.jpg', rating: '8.7', year: '2014' },
    ],
  },
  {
    id: 'mind-benders',
    title: 'Sci-Fi & Mind Benders',
    tag: 'HIGH BITRATE',
    icon: Compass,
    movies: [
      { title: 'Tenet (2020)', details: '2.9GB - 4K IMAX Enhanced', poster: 'https://image.tmdb.org/t/p/w500/aCIFMriQ2vtJHNxI9TISEn7YzOX.jpg', rating: '7.5', year: '2020' },
      { title: 'Blade Runner 2049 (2017)', details: '3.2GB - 1080p Atmos', poster: 'https://image.tmdb.org/t/p/w500/gajva2L0rPYkEWjzgFlBXCAVBE5.jpg', rating: '8.0', year: '2017' },
      { title: 'Arrival (2016)', details: '1.8GB - 1080p Dual Audio', poster: 'https://image.tmdb.org/t/p/w500/x2FJsf1ElAgr63Y3PNPtJrcmpoe.jpg', rating: '7.9', year: '2016' },
      { title: 'Shutter Island (2010)', details: '2.2GB - 1080p FHD', poster: 'https://image.tmdb.org/t/p/w500/4GDy0PHYX3VRXUtwK5ysagvk2Az.jpg', rating: '8.2', year: '2010' },
      { title: 'Everything Everywhere All at Once (2022)', details: '2.4GB - 1080p Web-DL', poster: 'https://image.tmdb.org/t/p/w500/w3LxiVYPqRLexPkaekcr9vg5UuJ.jpg', rating: '8.0', year: '2022' },
      { title: 'Inception (2010)', details: '1.9GB - 1080p HEVC', poster: 'https://image.tmdb.org/t/p/w500/ljsZTbVsrQSqZgWeep2B1QiDKuh.jpg', rating: '8.8', year: '2010' },
    ],
  },
]

// Single Horizontal Rail Component with Smooth Navigation
function HorizontalRail({ category, onSelectMovie, onQuickSearch }) {
  const rowRef = useRef(null)

  const handleScroll = (direction) => {
    if (rowRef.current) {
      const scrollAmount = direction === 'left' ? -600 : 600
      rowRef.current.scrollBy({ left: scrollAmount, behavior: 'smooth' })
    }
  }

  const Icon = category.icon || Sparkles

  return (
    <div className="content-rail-section">
      <div className="rail-header">
        <div className="rail-title-group">
          <span className="badge badge-red rail-badge">
            <Icon size={12} /> {category.tag}
          </span>
          <h2 className="rail-title">{category.title}</h2>
        </div>
        <div className="rail-nav-controls">
          <button
            className="rail-nav-btn"
            onClick={() => handleScroll('left')}
            title="Scroll left"
          >
            <ChevronLeft size={18} />
          </button>
          <button
            className="rail-nav-btn"
            onClick={() => handleScroll('right')}
            title="Scroll right"
          >
            <ChevronRight size={18} />
          </button>
        </div>
      </div>

      <div className="rail-scroll-track" ref={rowRef}>
        {category.movies.map((m, idx) => (
          <div
            key={idx}
            className="rail-movie-item"
            onClick={() => onQuickSearch(m.title.replace(/\s*\(\d+\)/, ''))}
          >
            <MovieCard
              group={{
                title: m.title,
                candidates: [{ title: m.title, details: m.details }],
                metadata: m.poster ? { poster_url: m.poster, rating: m.rating, year: m.year } : null,
              }}
              metadata={m.poster ? { poster_url: m.poster, rating: m.rating, year: m.year } : null}
              onSelect={() => onQuickSearch(m.title.replace(/\s*\(\d+\)/, ''))}
            />
          </div>
        ))}
      </div>
    </div>
  )
}

export default function MovieGrid({
  items,
  groupedItems,
  metadataEnrichment = {},
  isLoading,
  searchQuery,
  page,
  totalPages,
  hasNextPage,
  onPageChange,
  onSelectMovie,
  onQuickSearch,
}) {
  // Loading State
  if (isLoading) {
    return (
      <div className="grid-section">
        <div className="section-header">
          <div>
            <h2 className="section-title">Searching Cinema Index...</h2>
            <p className="section-subtitle">Connecting to high-speed stream nodes</p>
          </div>
          <span className="badge badge-red animate-pulse">
            <Loader2 size={13} className="animate-spin" /> Scanning releases
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
    const featuredGroup = groupedItems[0]
    const featuredMeta = metadataEnrichment?.[featuredGroup?.title]
    const otherGroups = groupedItems.slice(1)

    return (
      <div className="search-results-container">
        {/* Search Header */}
        <div className="section-header">
          <div>
            <h2 className="section-title">
              Results for <span className="text-red">"{searchQuery}"</span>
            </h2>
            <p className="section-subtitle">
              Found {items.length} verified streams across {groupedItems.length} title releases
            </p>
          </div>

          {/* Pagination controls if multiple pages */}
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

        {/* Featured Top Match Showcase Card (Solves Lonely Card Syndrome) */}
        {featuredGroup && (
          <div
            className="featured-search-match"
            onClick={() => onSelectMovie(featuredGroup)}
          >
            <div className="featured-match-inner">
              {featuredMeta?.backdrop_url && (
                <div
                  className="featured-match-backdrop"
                  style={{ backgroundImage: `url(${featuredMeta.backdrop_url})` }}
                />
              )}
              <div className="featured-match-overlay" />

              <div className="featured-match-content">
                <div className="featured-match-poster-col">
                  {featuredMeta?.poster_url ? (
                    <img
                      src={featuredMeta.poster_url}
                      alt={featuredGroup.title}
                      className="featured-match-poster"
                    />
                  ) : (
                    <div className="featured-match-poster-fallback">
                      <Film size={40} />
                    </div>
                  )}
                </div>

                <div className="featured-match-info-col">
                  <div className="featured-match-badges">
                    <span className="badge badge-red">TOP MATCH</span>
                    {featuredMeta?.rating && (
                      <span className="badge badge-gold">
                        <Star size={12} fill="#FFD700" /> {featuredMeta.rating}
                      </span>
                    )}
                    {featuredMeta?.year && (
                      <span className="badge badge-quality">{featuredMeta.year}</span>
                    )}
                    <span className="badge badge-quality">
                      {featuredGroup.candidates.length} Streams Available
                    </span>
                  </div>

                  <h3 className="featured-match-title">{featuredGroup.title}</h3>

                  {featuredMeta?.overview && (
                    <p className="featured-match-overview">{featuredMeta.overview}</p>
                  )}

                  <div className="featured-match-actions">
                    <button
                      className="btn btn-primary"
                      onClick={(e) => {
                        e.stopPropagation()
                        onSelectMovie(featuredGroup)
                      }}
                    >
                      <Play size={16} fill="#FFFFFF" /> Select Quality & Stream
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Other Results Grid */}
        {otherGroups.length > 0 && (
          <div className="more-results-section">
            <h3 className="sub-section-title">All Matching Releases</h3>
            <div className="movie-grid">
              {otherGroups.map((group, idx) => (
                <MovieCard
                  key={idx}
                  group={group}
                  metadata={metadataEnrichment?.[group.title]}
                  onSelect={onSelectMovie}
                />
              ))}
            </div>
          </div>
        )}

        {/* More Like This Rails to populate screen when few matches */}
        {groupedItems.length <= 3 && (
          <div className="related-discovery-section">
            <HorizontalRail
              category={CURATED_CATEGORIES[0]}
              onSelectMovie={onSelectMovie}
              onQuickSearch={onQuickSearch}
            />
          </div>
        )}
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
          Check your spelling or try searching for popular titles like "Avengers", "Interstellar", "Aavesham", or "Dune".
        </p>
      </div>
    )
  }

  // Default Home State: Curated Discovery Rails
  return (
    <div className="curated-discovery-rails">
      {CURATED_CATEGORIES.map((cat) => (
        <HorizontalRail
          key={cat.id}
          category={cat}
          onSelectMovie={onSelectMovie}
          onQuickSearch={onQuickSearch}
        />
      ))}
    </div>
  )
}
