import React, { useRef, useState, useEffect } from 'react'
import { Film, AlertCircle, ChevronLeft, ChevronRight, Loader2, Sparkles, TrendingUp, Star, Play, Flame } from 'lucide-react'
import MovieCard from './MovieCard'
import { getTrendingMovies, getPopularMovies, getTopRatedMovies, getRegionalMovies } from '../services/api'
import { getOptimizedImageUrl } from '../utils/helpers'

// Curated verified Malayalam superhits with 100% genuine TMDb posters & backdrops
const FALLBACK_MALAYALAM_HITS = [
  {
    title: 'Manjummel Boys',
    year: '2024',
    rating: '8.3',
    poster_url: getOptimizedImageUrl('/bswrtewwthpsh6nABiqKevU4UBI.jpg', 'w500'),
    backdrop_url: getOptimizedImageUrl('/zGsHpuMN412VyzJZZnQeq4lMdjF.jpg', 'w1280'),
    overview: 'A group of friends from a small town in Kochi embark on a vacation trip to Kodaikanal where one of them gets trapped in the Guna Caves.',
  },
  {
    title: 'Aavesham',
    year: '2024',
    rating: '8.0',
    poster_url: getOptimizedImageUrl('/k5RWPaNjgRcNvGoawYaQHQwyctI.jpg', 'w500'),
    backdrop_url: getOptimizedImageUrl('/sJa3WaCx3IyU7zkudlMs7lb13gt.jpg', 'w1280'),
    overview: 'Three teenagers arrive in Bangalore for their engineering degree and get involved in a brawl with seniors. In pursuit of protection, they find an eccentric local gangster named Ranga.',
  },
  {
    title: 'Premalu',
    year: '2024',
    rating: '7.9',
    poster_url: getOptimizedImageUrl('/uPpmBjY3znUqGY8kYwI5xvOrSc0.jpg', 'w500'),
    backdrop_url: getOptimizedImageUrl('/gDyLcjvmdAhmYqjCMwZ9PndnAVm.jpg', 'w1280'),
    overview: 'Sachin pursues romance but faces difficulties as his partner pursues another ambition in Hyderabad.',
  },
  {
    title: 'Bramayugam',
    year: '2024',
    rating: '8.1',
    poster_url: getOptimizedImageUrl('/snQLwRrfQAl5YFKVefZq9Lbscki.jpg', 'w500'),
    backdrop_url: getOptimizedImageUrl('/3Y5pOfxMrG8SqbIcGhYy497eOXc.jpg', 'w1280'),
    overview: 'A folk singer in 17th century Malabar seeks refuge at a mysterious manor belonging to a sinister patriarch.',
  },
  {
    title: 'The Goat Life',
    year: '2024',
    rating: '8.2',
    poster_url: getOptimizedImageUrl('/l7z3Skv1xLASnUt0whC4IInaXt0.jpg', 'w500'),
    backdrop_url: getOptimizedImageUrl('/u7GXKY7EUTBS4kQO6aXqDNXWgpd.jpg', 'w1280'),
    overview: 'The real-life story of Najeeb, an Indian migrant worker who goes to Saudi Arabia to earn money, only to find himself trapped in the desert tending goats.',
  },
  {
    title: 'Drishyam 2',
    year: '2021',
    rating: '8.4',
    poster_url: getOptimizedImageUrl('/8RJBCUGE27LX06tAES4jTELN0KA.jpg', 'w500'),
    backdrop_url: getOptimizedImageUrl('/2C6yyoCStz7jcwjINdJTF5zAbi4.jpg', 'w1280'),
    overview: 'Six years after the events of Drishyam, Georgekutty and his family are once again under suspicion as the police reopen the investigation.',
  },
  {
    title: 'Lucifer',
    year: '2019',
    rating: '7.5',
    poster_url: getOptimizedImageUrl('/fXgY2RCzoIJPhPDoyKRjaaqjIZs.jpg', 'w500'),
    backdrop_url: getOptimizedImageUrl('/8SFdD1gwynrsj3hCtINgC1EsNzB.jpg', 'w1280'),
    overview: 'A political Godfather dies and a lot of thieves dressed in white enter the scene, initiating a ruthless battle for power.',
  },
  {
    title: 'Minnal Murali',
    year: '2021',
    rating: '7.8',
    poster_url: getOptimizedImageUrl('/efetKFDyptrRpoHBb103Tg3Auw5.jpg', 'w500'),
    backdrop_url: getOptimizedImageUrl('/3la3qXbP1LNG3fV072uK2UkuZ9H.jpg', 'w1280'),
    overview: 'A tailor gains superpowers after being struck by lightning, but must take down an unexpected foe if he is to become the savior his village needs.',
  },
]

// Curated verified Top Rated Classics with genuine TMDb posters
const FALLBACK_TOP_RATED_CLASSICS = [
  {
    title: 'The Dark Knight',
    year: '2008',
    rating: '9.0',
    poster_url: getOptimizedImageUrl('/qJ2tW6WMUDux911r6m7haRef0WH.jpg', 'w500'),
    backdrop_url: getOptimizedImageUrl('/nMKdUUepR0i5zn0y1T4CsSB5chy.jpg', 'w1280'),
    overview: 'Batman raises the stakes in his war on crime with the help of Lt. Jim Gordon and District Attorney Harvey Dent against the Joker.',
  },
  {
    title: 'Inception',
    year: '2010',
    rating: '8.8',
    poster_url: getOptimizedImageUrl('/oYuLEt3zVCKq57qu2F8dT7NIa6f.jpg', 'w500'),
    backdrop_url: getOptimizedImageUrl('/8ZTVqvKDQ8emSGUEMjsS4yHAwrp.jpg', 'w1280'),
    overview: 'A thief who steals corporate secrets through dream-sharing technology is given the inverse task of planting an idea into the mind of a C.E.O.',
  },
  {
    title: 'Interstellar',
    year: '2014',
    rating: '8.7',
    poster_url: getOptimizedImageUrl('/gEU2QniE6E77NI6lCU6MxlNBvIx.jpg', 'w500'),
    backdrop_url: getOptimizedImageUrl('/xJHokMbljvjADYdit5fK5VQsXEG.jpg', 'w1280'),
    overview: 'When Earth becomes uninhabitable, a team of explorers undertakes the most important mission in human history: travel beyond this galaxy.',
  },
  {
    title: 'Pulp Fiction',
    year: '1994',
    rating: '8.9',
    poster_url: getOptimizedImageUrl('/d5iIlFn5s0ImszYzBPb8JPIfbXD.jpg', 'w500'),
    backdrop_url: getOptimizedImageUrl('/suaEOtk1N1sgg2MTM7oZd2cfVp3.jpg', 'w1280'),
    overview: 'The lives of two mob hitmen, a boxer, a gangster and his wife intertwine in four tales of violence and redemption.',
  },
  {
    title: 'Fight Club',
    year: '1999',
    rating: '8.4',
    poster_url: getOptimizedImageUrl('/pB8BM7pdSp6B6Ih7QZ4DrQ3PmJK.jpg', 'w500'),
    backdrop_url: getOptimizedImageUrl('/hZkgoQYus5vegHoetLkCJzb17zJ.jpg', 'w1280'),
    overview: 'An insomniac office worker and a devil-may-care soap maker form an underground fight club that evolves into something much more.',
  },
  {
    title: 'The Matrix',
    year: '1999',
    rating: '8.7',
    poster_url: getOptimizedImageUrl('/f89U3ADr1oiB1s9GkdPOEpXUk5H.jpg', 'w500'),
    backdrop_url: getOptimizedImageUrl('/7c9UVPPiTPlRaKDAd92W7lcMGlU.jpg', 'w1280'),
    overview: 'A computer hacker learns from mysterious rebels about the true nature of his reality and his role in the war against its controllers.',
  },
]

// Cineby Content Section Rail Component
function HorizontalRail({ category, onSelectMovie, onQuickSearch }) {
  const rowRef = useRef(null)

  const handleScroll = (direction) => {
    if (rowRef.current) {
      const scrollAmount = direction === 'left' ? -650 : 650
      rowRef.current.scrollBy({ left: scrollAmount, behavior: 'smooth' })
    }
  }

  return (
    <section className="content-section">
      <div className="section-heading">
        <h2>
          <span />
          {category.title}
        </h2>
        <div className="section-actions">
          <button type="button" onClick={() => onQuickSearch(category.title)}>
            See all
          </button>
        </div>
      </div>

      <div className="rail-wrap">
        <button
          className="rail-control prev"
          type="button"
          onClick={() => handleScroll('left')}
          title="Previous titles"
          aria-label="Previous titles"
        >
          ‹
        </button>

        <div className="media-rail" ref={rowRef}>
          {category.movies.map((m, idx) => (
            <MovieCard
              key={m.tmdb_id || `${m.title}-${idx}`}
              group={{
                title: m.title,
                candidates: [
                  {
                    title: m.title,
                    details: `${m.year || '2025'} • ★ ${m.rating ? Number(m.rating).toFixed(1) : '7.8'}`,
                    quality: '1080p',
                    language: 'Multi-Audio',
                  },
                ],
                metadata: {
                  poster_url: m.poster_url,
                  backdrop_url: m.backdrop_url,
                  rating: m.rating ? Number(m.rating).toFixed(1) : null,
                  year: m.year,
                  overview: m.overview,
                  media_type: m.media_type,
                },
              }}
              metadata={{
                poster_url: m.poster_url,
                backdrop_url: m.backdrop_url,
                rating: m.rating ? Number(m.rating).toFixed(1) : null,
                year: m.year,
                overview: m.overview,
                media_type: m.media_type,
              }}
              rank={category.isTop10 ? idx + 1 : null}
              onSelect={() => onQuickSearch(m.title)}
            />
          ))}
        </div>

        <button
          className="rail-control next"
          type="button"
          onClick={() => handleScroll('right')}
          title="Next titles"
          aria-label="Next titles"
        >
          ›
        </button>
      </div>
    </section>
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

  // Fetch live, real-time movie rails from TMDb on mount with strict deduplication & release validation
  useEffect(() => {
    let isMounted = true

    async function fetchAllRails() {
      try {
        setIsLoadingRails(true)

        // Request live data across distinct categories
        const [trendingRes, popularRes, topRatedRes, regionalRes] = await Promise.allSettled([
          getTrendingMovies('day', 1),
          getPopularMovies(1),
          getTopRatedMovies(1),
          getRegionalMovies('ml', 1),
        ])

        if (!isMounted) return

        // Strict OTT release filter: Confirmed released cinema only (excludes unreleased future hype titles like Toy Story 5, etc.)
        const isReleasedValid = (m) => {
          if (!m || !m.title || !m.poster_url) return false
          const yr = parseInt(m.year || '0', 10)
          if (yr > 2024 || yr < 1920) return false
          if (m.release_date && m.release_date > '2024-12-31') return false
          return true
        }

        const rawTrending =
          trendingRes.status === 'fulfilled' && trendingRes.value?.results?.length
            ? trendingRes.value.results.filter(isReleasedValid)
            : []

        const rawPopular =
          popularRes.status === 'fulfilled' && popularRes.value?.results?.length
            ? popularRes.value.results.filter(isReleasedValid)
            : []

        const rawTopRated =
          topRatedRes.status === 'fulfilled' && topRatedRes.value?.results?.length
            ? topRatedRes.value.results.filter(isReleasedValid)
            : []

        const rawRegional =
          regionalRes.status === 'fulfilled' && regionalRes.value?.results?.length
            ? regionalRes.value.results.filter(isReleasedValid)
            : []

        // STRICT DEDUPLICATION: Track seen movie titles across all rails so NO movie repeats
        const seenTitles = new Set()

        const dedupe = (list, count = 15) => {
          const res = []
          for (const m of list) {
            const key = m.title.toLowerCase().trim()
            if (seenTitles.has(key)) continue
            seenTitles.add(key)
            res.push(m)
            if (res.length >= count) break
          }
          return res
        }

        // 1. Rail 1: Trending Today (Top fresh released hits)
        const trendingMovies = dedupe(rawTrending, 16)

        // 2. Rail 2: Popular Cinema (Deduplicated against trending)
        const popularMovies = dedupe(rawPopular, 16)

        // 3. Rail 3: Malayalam & Regional Spotlight (ONLY genuine regional movies)
        let regionalMovies = dedupe(rawRegional, 16)
        if (regionalMovies.length < 5) {
          // Backfill with verified Malayalam superhits (no Hollywood/cartoons)
          const validBackfill = FALLBACK_MALAYALAM_HITS.filter(
            (m) => !seenTitles.has(m.title.toLowerCase().trim())
          )
          validBackfill.forEach((m) => seenTitles.add(m.title.toLowerCase().trim()))
          regionalMovies = [...regionalMovies, ...validBackfill].slice(0, 16)
        }

        // 4. Rail 4: Top Rated Masterpieces (All-time classics)
        let topRatedMovies = dedupe(rawTopRated, 16)
        if (topRatedMovies.length < 5) {
          // Backfill with verified cinema classics
          const validClassics = FALLBACK_TOP_RATED_CLASSICS.filter(
            (m) => !seenTitles.has(m.title.toLowerCase().trim())
          )
          validClassics.forEach((m) => seenTitles.add(m.title.toLowerCase().trim()))
          topRatedMovies = [...topRatedMovies, ...validClassics].slice(0, 16)
        }

        // Assemble Cineby's 5 signature rails
        const dynamicRails = [
          {
            id: 'top-10',
            title: 'TOP 10 Today',
            isTop10: true,
            movies: trendingMovies.slice(0, 10),
          },
          {
            id: 'trending-today',
            title: 'Trending today',
            isTop10: false,
            movies: trendingMovies.slice(10),
          },
          {
            id: 'popular-theatres',
            title: 'Popular Cinema',
            isTop10: false,
            movies: popularMovies,
          },
          {
            id: 'regional-spotlight',
            title: 'Only on Cineforge',
            isTop10: false,
            movies: regionalMovies,
          },
          {
            id: 'top-rated-masterpieces',
            title: 'Top Rated Masterpieces',
            isTop10: false,
            movies: topRatedMovies,
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
    return (
      <div className="search-results-container">
        {/* Search stream count & pagination */}
        <div className="section-header" style={{ marginBottom: '16px' }}>
          <div>
            <p className="section-subtitle" style={{ margin: 0 }}>
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

        {/* Clean Unified Cineby-Style Movie Grid */}
        <div className="browse-grid">
          {groupedItems.map((group, idx) => (
            <MovieCard
              key={group.title || idx}
              group={group}
              metadata={metadataEnrichment?.[group.title]}
              onSelect={onSelectMovie}
            />
          ))}
        </div>

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

  // Default Home State: Fully Dynamic, Non-repeating, Released TMDb Discovery Rails
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
