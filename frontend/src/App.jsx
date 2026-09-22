import React, { useState, useEffect, useRef } from 'react'
import Navbar from './components/Navbar'
import HeroBanner from './components/HeroBanner'
import SearchBar from './components/SearchBar'
import MovieGrid from './components/MovieGrid'
import VersionPickerModal from './components/VersionPickerModal'
import DeliveryModal from './components/DeliveryModal'
import WatchPage from './components/WatchPage'
import AuthModal from './components/AuthModal'
import { useAuth } from './context/AuthContext'
import { searchMovies, deliverCandidate, getBackendHealth, getTrendingMovies } from './services/api'
import { parseMovieMetadata } from './utils/helpers'

export default function App() {
  const { isAuthModalOpen, closeAuthModal } = useAuth()
  const [currentView, setCurrentView] = useState('browse') // 'browse' | 'watch'
  const [activeTab, setActiveTab] = useState('home')
  const [isBackendOnline, setIsBackendOnline] = useState(true)

  // Search state
  const [searchQuery, setSearchQuery] = useState('')
  const [rawCandidates, setRawCandidates] = useState([])
  const [groupedCandidates, setGroupedCandidates] = useState([])
  const [metadataEnrichment, setMetadataEnrichment] = useState({})
  const [page, setPage] = useState(1)
  const [totalPages, setTotalPages] = useState(1)
  const [hasNextPage, setHasNextPage] = useState(false)
  const [isSearching, setIsSearching] = useState(false)
  const [searchError, setSearchError] = useState(null)
  const [aiInterpretation, setAiInterpretation] = useState(null)
  const [isCached, setIsCached] = useState(false)


  // Delivery & Cinema Watch state
  const [selectedGroup, setSelectedGroup] = useState(null)
  const [activeMovieGroup, setActiveMovieGroup] = useState(null)
  const [candidateInDelivery, setCandidateInDelivery] = useState(null)
  const [activeCandidate, setActiveCandidate] = useState(null)
  const [deliveryError, setDeliveryError] = useState(null)
  const [activeDelivery, setActiveDelivery] = useState(null)

  const searchBarRef = useRef(null)

  // Health check on mount and interval
  useEffect(() => {
    const check = async () => {
      const ok = await getBackendHealth()
      setIsBackendOnline(ok)
    }
    check()
    const interval = setInterval(check, 15000)
    return () => clearInterval(interval)
  }, [])

  // When clicking Trending tab, load top trending movies from TMDb
  useEffect(() => {
    if (activeTab === 'trending') {
      setIsSearching(true)
      getTrendingMovies('week', 1)
        .then((data) => {
          if (data && data.results && data.results.length > 0) {
            const enrichment = {}
            const groups = data.results.map((m) => {
              enrichment[m.title] = m
              return {
                title: m.title,
                metadata: m,
                candidates: [
                  {
                    title: m.title,
                    display_text: `${m.title} (${m.year || '2024'}) - Stream Available`,
                    quality: '1080P',
                    container: 'mp4',
                    language: 'Dual Audio',
                  },
                ],
              }
            })
            setMetadataEnrichment(enrichment)
            setGroupedCandidates(groups)
            setRawCandidates(groups.flatMap((g) => g.candidates))
            setSearchQuery('Trending Movies')
          }
        })
        .catch((e) => console.error('Failed to load trending movies:', e))
        .finally(() => setIsSearching(false))
    }
  }, [activeTab])


  // Fallback helper to group candidates by title if not grouped by backend
  const fallbackGroupCandidates = (candidates) => {
    const groups = new Map()

    candidates.forEach((cand) => {
      const meta = parseMovieMetadata(cand.title, cand.display_text || cand.size || '')
      const key = meta.cleanTitle.toLowerCase()

      if (!groups.has(key)) {
        groups.set(key, {
          title: meta.cleanTitle,
          candidates: [],
        })
      }
      groups.get(key).candidates.push(cand)
    })

    return Array.from(groups.values())
  }

  // Search executor
  const handleSearch = async (query, pageNum = 1, useAi = true) => {
    if (!query.trim()) return

    // If on watch page, switch back to browse
    if (currentView === 'watch') {
      setCurrentView('browse')
    }

    setIsSearching(true)
    setSearchError(null)
    setSearchQuery(query)
    setPage(pageNum)

    try {
      const data = await searchMovies(query, pageNum, useAi)
      const candidates = data.candidates || []
      setRawCandidates(candidates)
      setAiInterpretation(data.ai_interpretation || null)
      setIsCached(Boolean(data.is_cached))
      setMetadataEnrichment(data.metadata_enrichment || {})

      // Use backend title_groups if available, else fallback

      if (data.title_groups && Object.keys(data.title_groups).length > 0) {
        const groups = Object.entries(data.title_groups).map(([title, cands]) => ({
          title,
          candidates: cands,
        }))
        setGroupedCandidates(groups)
      } else {
        setGroupedCandidates(fallbackGroupCandidates(candidates))
      }

      if (data.pagination) {
        setTotalPages(data.pagination.total_pages || 1)
        setHasNextPage(Boolean(data.pagination.has_next))
      } else {
        setTotalPages(1)
        setHasNextPage(false)
      }
    } catch (err) {
      console.error('Search failed:', err)
      setSearchError(err.message || 'Failed to search Telegram bot')
      setRawCandidates([])
      setGroupedCandidates([])
    } finally {
      setIsSearching(false)
    }
  }

  // Handle movie selection from grid
  const handleSelectMovie = (group) => {
    setActiveMovieGroup(group)
    if (group.candidates && group.candidates.length > 1) {
      setSelectedGroup(group)
    } else {
      const single = group.candidates ? group.candidates[0] : group
      startDelivery(single, group)
    }
  }

  // Start the 3-step stream delivery pipeline
  const startDelivery = async (candidate, group = null) => {
    setSelectedGroup(null)
    setCandidateInDelivery(candidate)
    setDeliveryError(null)
    if (group) {
      setActiveMovieGroup(group)
    }

    try {
      const result = await deliverCandidate(candidate)
      if (!result.candidate_title) {
        result.candidate_title = candidate.title
      }
      setCandidateInDelivery(null)
      setActiveCandidate(candidate)
      setActiveDelivery(result)
      setCurrentView('watch') // Transition into dedicated cinema watch page!
      window.scrollTo({ top: 0, behavior: 'smooth' })
    } catch (err) {
      console.error('Delivery pipeline failed:', err)
      setDeliveryError(err.message || 'Stream generation failed. Please try another release.')
    }
  }

  // Hero Quick Play
  const handleHeroQuickPlay = (query) => {
    handleSearch(query, 1)
  }

  const handleScrollToSearch = () => {
    if (currentView === 'watch') {
      setCurrentView('browse')
    }
    searchBarRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  return (
    <div className="app-container">
      {/* StreamVibe Navigation Header */}
      <Navbar
        onSearchClick={handleScrollToSearch}
        isBackendOnline={isBackendOnline}
        activeTab={activeTab}
        setActiveTab={(tab) => {
          setActiveTab(tab)
          setCurrentView('browse')
          if (tab === 'home') {
            setSearchQuery('')
            setRawCandidates([])
            setGroupedCandidates([])
            setAiInterpretation(null)
            setIsCached(false)
          }
        }}
      />

      <main className="main-content">
        {/* Dedicated OTT Cinema Watch Page */}
        {currentView === 'watch' && activeDelivery ? (
          <WatchPage
            delivery={activeDelivery}
            candidate={activeCandidate}
            group={activeMovieGroup}
            onBack={() => setCurrentView('browse')}
            onSwitchVersion={(ver) => startDelivery(ver, activeMovieGroup)}
          />
        ) : (
          /* Browse & Discovery View */
          <div className="browse-view-container">
            {/* Hero Showcase (full bleed when not searching) */}
            {!searchQuery && (
              <HeroBanner onQuickPlay={handleHeroQuickPlay} />
            )}

            <div className="browse-body-container">
              {/* Search Bar Section */}
              <div ref={searchBarRef} className="search-bar-wrapper">
                <SearchBar
                  onSearch={(q) => handleSearch(q, 1)}
                  isLoading={isSearching}
                  currentQuery={searchQuery}
                />
              </div>

              {/* Results / Discovery Movie Grid */}
              <MovieGrid
                items={rawCandidates}
                groupedItems={groupedCandidates}
                metadataEnrichment={metadataEnrichment}
                isLoading={isSearching}
                searchQuery={searchQuery}
                page={page}
                totalPages={totalPages}
                hasNextPage={hasNextPage}
                onPageChange={(newPage) => handleSearch(searchQuery, newPage)}
                onSelectMovie={handleSelectMovie}
                onQuickSearch={(q) => handleSearch(q, 1)}
              />
            </div>
          </div>
        )}
      </main>

      {/* Version Picker Modal */}
      {selectedGroup && (
        <VersionPickerModal
          group={selectedGroup}
          onClose={() => setSelectedGroup(null)}
          onSelectCandidate={(cand) => startDelivery(cand, selectedGroup)}
        />
      )}

      {/* Delivery Pipeline Modal */}
      {candidateInDelivery && (
        <DeliveryModal
          candidate={candidateInDelivery}
          error={deliveryError}
          onClose={() => {
            setCandidateInDelivery(null)
            setDeliveryError(null)
          }}
          onRetry={() => startDelivery(candidateInDelivery, activeMovieGroup)}
        />
      )}

      {/* Supabase Authentication Modal */}
      <AuthModal
        isOpen={isAuthModalOpen}
        onClose={closeAuthModal}
      />
    </div>
  )
}

