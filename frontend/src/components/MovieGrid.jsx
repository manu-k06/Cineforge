import React, { useRef, useState, useEffect } from 'react'
import { Film, AlertCircle, ChevronLeft, ChevronRight, Loader2, Sparkles, TrendingUp, Star, Play, Flame } from 'lucide-react'
import MovieCard from './MovieCard'
import { getTrendingMovies, getPopularMovies, getTopRatedMovies, getRegionalMovies } from '../services/api'

// Single Horizontal Rail Component with Smooth Navigation
function HorizontalRail({ category, onSelectMovie, onQuickSearch }) {
  const rowRef = useRef(null)

  const handleScroll = (direction) => {
    if (rowRef.current) {
      const scrollAmount = direction === 'left' ? -650 : 650
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
            aria-label="Scroll left"
          >
            <ChevronLeft size={18} />
          </button>
          <button
            className="rail-nav-btn"
            onClick={() => handleScroll('right')}
            title="Scroll right"
            aria-label="Scroll right"
          >
            <ChevronRight size={18} />
          </button>
        </div>
      </div>

      <div className="rail-scroll-track" ref={rowRef}>
        {category.movies.map((m, idx) => (
          <div
            key={m.tmdb_id || `${m.title}-${idx}`}
            className="rail-movie-item"
            onClick={() => onQuickSearch(m.title)}
          >
            <MovieCard
              group={{
                title: m.title,
                candidates: [
                  {
                    title: m.title,
                    details: `${m.year || '2026'} • ★ ${m.rating ? Number(m.rating).toFixed(1) : '8.0'} • Ultra HD`,
                    quality: '1080p FHD',
                    language: 'Multi-Audio',
                  },
                ],
                metadata: {
                  poster_url: m.poster_url,
                  backdrop_url: m.backdrop_url,
                  rating: m.rating ? Number(m.rating).toFixed(1) : null,
                  year: m.year,
                  overview: m.overview,
                },
              }}
              metadata={{
                poster_url: m.poster_url,
                backdrop_url: m.backdrop_url,
                rating: m.rating ? Number(m.rating).toFixed(1) : null,
                year: m.year,
                overview: m.overview,
              }}
              onSelect={() => onQuickSearch(m.title)}
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
  const [rails, setRails] = useState([])
  const [isLoadingRails, setIsLoadingRails] = useState(true)

  // Fetch live, real-time movie rails from TMDb on mount
  useEffect(() => {
    let isMounted = true

    async function fetchAllRails() {
      try {
        setIsLoadingRails(true)

        // Request live data from backend/TMDb
        const [trendingRes, popularRes, topRatedRes, regionalRes] = await Promise.allSettled([
          getTrendingMovies('day', 1),
          getPopularMovies(1),
          getTopRatedMovies(1),
          getRegionalMovies('ml', 1),
        ])

        if (!isMounted) return

        const trendingMovies =
          trendingRes.status === 'fulfilled' && trendingRes.value?.results?.length
            ? trendingRes.value.results.filter((m) => m.poster_url)
            : []

        const popularMovies =
          popularRes.status === 'fulfilled' && popularRes.value?.results?.length
            ? popularRes.value.results.filter((m) => m.poster_url)
            : []

        const topRatedMovies =
          topRatedRes.status === 'fulfilled' && topRatedRes.value?.results?.length
            ? topRatedRes.value.results.filter((m) => m.poster_url)
            : []

        const regionalMovies =
          regionalRes.status === 'fulfilled' && regionalRes.value?.results?.length
            ? regionalRes.value.results.filter((m) => m.poster_url)
            : []

        // Assemble 4 dynamic rails with live, fresh movies
        const dynamicRails = [
          {
            id: 'trending-today',
            title: 'Trending Today',
            tag: 'LIVE TRENDING',
            icon: Flame,
            movies: trendingMovies.slice(0, 16),
          },
          {
            id: 'popular-theatres',
            title: 'Popular in Theatres',
            tag: 'NOW SHOWING',
            icon: TrendingUp,
            movies:
              popularMovies.length > 0
                ? popularMovies.slice(0, 16)
                : trendingMovies.slice(4, 20),
          },
          {
            id: 'regional-spotlight',
            title: 'Malayalam & Regional Spotlight',
            tag: 'REGIONAL HITS',
            icon: Sparkles,
            movies:
              regionalMovies.length > 0
                ? regionalMovies.slice(0, 16)
                : trendingMovies.slice(8, 20),
          },
          {
            id: 'top-rated-masterpieces',
            title: 'Top Rated Masterpieces',
            tag: 'CRITICS CHOICE',
            icon: Star,
            movies:
              topRatedMovies.length > 0
                ? topRatedMovies.slice(0, 16)
                : trendingMovies.slice(0, 14),
          },
        ].filter((r) => r.movies && r.movies.length > 0)

        setRails(dynamicRails)
      } catch (err) {
        console.error('Failed to load discovery rails:', err)
      } finally {
        if (isMounted) setIsLoadingRails(false)
      }
    }

    fetchAllRails()

    return () => {
      isMounted = false
    }
  }, [])

  // Loading State during search
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

        {/* Featured Top Match Showcase Card */}
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

        {/* Dynamic Recommended Rails when few matches */}
        {groupedItems.length <= 3 && rails.length > 0 && (
          <div className="related-discovery-section">
            <HorizontalRail
              category={rails[0]}
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

  // Loading state for rails on initial load
  if (isLoadingRails && rails.length === 0) {
    return (
      <div className="curated-discovery-rails">
        {[1, 2].map((railIdx) => (
          <div key={railIdx} className="content-rail-section">
            <div className="rail-header">
              <div
                style={{
                  width: '240px',
                  height: '28px',
                  background: 'rgba(255,255,255,0.08)',
                  borderRadius: '6px',
                }}
                className="skeleton"
              />
            </div>
            <div className="rail-scroll-track" style={{ overflow: 'hidden' }}>
              {[1, 2, 3, 4, 5, 6].map((i) => (
                <div key={i} className="rail-movie-item">
                  <div className="movie-card skeleton-card">
                    <div className="skeleton skeleton-poster"></div>
                    <div className="skeleton-details">
                      <div className="skeleton skeleton-title"></div>
                      <div className="skeleton skeleton-subtitle"></div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
    )
  }

  // Default Home State: Fully Dynamic TMDb Discovery Rails
  return (
    <div className="curated-discovery-rails">
      {rails.map((cat) => (
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
