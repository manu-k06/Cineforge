import React, { useState, useEffect, useRef } from 'react'
import Navbar from './components/Navbar'
import HeroBanner from './components/HeroBanner'
import SearchBar from './components/SearchBar'
import MovieGrid from './components/MovieGrid'
import VersionPickerModal from './components/VersionPickerModal'
import DeliveryModal from './components/DeliveryModal'
import PlayerModal from './components/PlayerModal'
import { searchMovies, deliverCandidate, getBackendHealth } from './services/api'
import { parseMovieMetadata } from './utils/helpers'

export default function App() {
  const [activeTab, setActiveTab] = useState('home')
  const [isBackendOnline, setIsBackendOnline] = useState(true)

  // Search state
  const [searchQuery, setSearchQuery] = useState('')
  const [rawCandidates, setRawCandidates] = useState([])
  const [groupedCandidates, setGroupedCandidates] = useState([])
  const [page, setPage] = useState(1)
  const [totalPages, setTotalPages] = useState(1)
  const [hasNextPage, setHasNextPage] = useState(false)
  const [isSearching, setIsSearching] = useState(false)
  const [searchError, setSearchError] = useState(null)

  // Delivery & Modals state
  const [selectedGroup, setSelectedGroup] = useState(null)
  const [candidateInDelivery, setCandidateInDelivery] = useState(null)
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
  const handleSearch = async (query, pageNum = 1) => {
    if (!query.trim()) return

    setIsSearching(true)
    setSearchError(null)
    setSearchQuery(query)
    setPage(pageNum)

    try {
      const data = await searchMovies(query, pageNum)
      const candidates = data.candidates || []
      setRawCandidates(candidates)

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
    if (group.candidates && group.candidates.length > 1) {
      setSelectedGroup(group)
    } else {
      const single = group.candidates ? group.candidates[0] : group
      startDelivery(single)
    }
  }

  // Start the 3-step stream delivery pipeline
  const startDelivery = async (candidate) => {
    setSelectedGroup(null)
    setCandidateInDelivery(candidate)
    setDeliveryError(null)

    try {
      const result = await deliverCandidate(candidate)
      if (!result.candidate_title) {
        result.candidate_title = candidate.title
      }
      setCandidateInDelivery(null)
      setActiveDelivery(result)
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
          if (tab === 'home') {
            setSearchQuery('')
            setRawCandidates([])
            setGroupedCandidates([])
          }
        }}
      />

      <main className="main-content">
        {/* Hero Showcase (shown when not actively searching) */}
        {!searchQuery && (
          <HeroBanner onQuickPlay={handleHeroQuickPlay} />
        )}

        {/* Search Bar Section */}
        <div ref={searchBarRef}>
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
          isLoading={isSearching}
          searchQuery={searchQuery}
          page={page}
          totalPages={totalPages}
          hasNextPage={hasNextPage}
          onPageChange={(newPage) => handleSearch(searchQuery, newPage)}
          onSelectMovie={handleSelectMovie}
          onQuickSearch={(q) => handleSearch(q, 1)}
        />
      </main>

      {/* Version Picker Modal */}
      {selectedGroup && (
        <VersionPickerModal
          group={selectedGroup}
          onClose={() => setSelectedGroup(null)}
          onSelectCandidate={startDelivery}
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
          onRetry={() => startDelivery(candidateInDelivery)}
        />
      )}

      {/* Video Player Modal */}
      {activeDelivery && (
        <PlayerModal
          delivery={activeDelivery}
          onClose={() => setActiveDelivery(null)}
        />
      )}
    </div>
  )
}
