import React, { useState, useRef, useEffect } from 'react'
import {
  ArrowLeft,
  Play,
  Pause,
  RotateCcw,
  RotateCw,
  Volume2,
  Volume1,
  VolumeX,
  Maximize,
  Minimize,
  Tv,
  Download,
  Copy,
  Check,
  HardDrive,
  Film,
  AlertCircle,
  Layers,
  Star,
  Calendar,
  Globe,
  Tag,
  User,
  ExternalLink,
  ChevronLeft,
  ChevronRight,
  ThumbsUp,
  MessageSquare,
  Sparkles,
  Captions,
  CaptionsOff,
} from 'lucide-react'
import { formatBytes, parseMovieMetadata } from '../utils/helpers'
import { getMovieMetadata, getSubtitleTracks } from '../services/api'


// Default fallback metadata generator for cast & reviews matching StreamVibe aesthetic
function getMovieExtras(title) {
  const isAvengers = /avenger/i.test(title)
  const isDune = /dune/i.test(title)
  const isInterstellar = /interstellar/i.test(title)

  if (isAvengers) {
    return {
      synopsis:
        'After the devastating events of Infinity War, the universe is in ruins due to the efforts of the Mad Titan, Thanos. With the help of remaining allies, the Avengers assemble once more in order to reverse Thanos’ actions and restore balance to the universe.',
      directors: 'Anthony Russo, Joe Russo',
      music: 'Alan Silvestri',
      genres: ['Action', 'Adventure', 'Sci-Fi'],
      languages: { audio: ['English', 'Hindi', 'Tamil', 'Telugu'], subs: ['English', 'Spanish'] },
      imdbRating: '8.4',
      streamVibeRating: '4.9',
      cast: [
        { name: 'Robert Downey Jr.', role: 'Tony Stark / Iron Man', img: 'https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?q=80&w=200&auto=format&fit=crop' },
        { name: 'Chris Evans', role: 'Steve Rogers / Captain America', img: 'https://images.unsplash.com/photo-1500648767791-00dcc994a43e?q=80&w=200&auto=format&fit=crop' },
        { name: 'Mark Ruffalo', role: 'Bruce Banner / Hulk', img: 'https://images.unsplash.com/photo-1472099645785-5658abf4ff4e?q=80&w=200&auto=format&fit=crop' },
        { name: 'Chris Hemsworth', role: 'Thor Odinson', img: 'https://images.unsplash.com/photo-1519085360753-af0119f7cbe7?q=80&w=200&auto=format&fit=crop' },
        { name: 'Scarlett Johansson', role: 'Natasha Romanoff', img: 'https://images.unsplash.com/photo-1534528741775-53994a69daeb?q=80&w=200&auto=format&fit=crop' },
      ],
      reviews: [
        { author: 'Alex Morgan', rating: 5, date: '2 days ago', text: 'A monumental cinematic achievement. The culmination of 22 films delivered beyond expectations with breathtaking emotion.', likes: 142 },
        { author: 'Sarah Jenkins', rating: 5, date: '1 week ago', text: 'The final battle sequence is pure magic. Outstanding performances from Robert Downey Jr. and Chris Evans.', likes: 89 },
      ],
    }
  }

  if (isDune) {
    return {
      synopsis:
        'Paul Atreides unites with Chani and the Fremen while seeking revenge against the conspirators who destroyed his family. Facing a choice between the love of his life and the fate of the universe, he endeavors to prevent a terrible future.',
      directors: 'Denis Villeneuve',
      music: 'Hans Zimmer',
      genres: ['Sci-Fi', 'Adventure', 'Drama'],
      languages: { audio: ['English', 'Hindi', 'French'], subs: ['English', 'Arabic'] },
      imdbRating: '8.6',
      streamVibeRating: '4.8',
      cast: [
        { name: 'Timothée Chalamet', role: 'Paul Atreides', img: 'https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?q=80&w=200&auto=format&fit=crop' },
        { name: 'Zendaya', role: 'Chani', img: 'https://images.unsplash.com/photo-1534528741775-53994a69daeb?q=80&w=200&auto=format&fit=crop' },
        { name: 'Rebecca Ferguson', role: 'Lady Jessica', img: 'https://images.unsplash.com/photo-1544005313-94ddf0286df2?q=80&w=200&auto=format&fit=crop' },
        { name: 'Javier Bardem', role: 'Stilgar', img: 'https://images.unsplash.com/photo-1500648767791-00dcc994a43e?q=80&w=200&auto=format&fit=crop' },
      ],
      reviews: [
        { author: 'Marcus Vance', rating: 5, date: '3 days ago', text: 'Masterpiece of modern sci-fi. Visuals and sound design are totally unmatched.', likes: 114 },
      ],
    }
  }

  // Generic fallback
  return {
    synopsis:
      'Experience high-definition cinematic streaming straight from Telegram bots. Powered by the Cineforge streaming engine, offering high-bitrate media playback with crisp multi-channel audio.',
    directors: 'Acclaimed Filmmakers',
    music: 'Original Cinematic Score',
    genres: ['Action', 'Thriller', 'Drama'],
    languages: { audio: ['Original Audio', 'Dual Audio'], subs: ['English'] },
    imdbRating: '8.2',
    streamVibeRating: '4.7',
    cast: [
      { name: 'Lead Actor', role: 'Protagonist', img: 'https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?q=80&w=200&auto=format&fit=crop' },
      { name: 'Co-Star', role: 'Deuteragonist', img: 'https://images.unsplash.com/photo-1534528741775-53994a69daeb?q=80&w=200&auto=format&fit=crop' },
      { name: 'Supporting Cast', role: 'Allies & Foes', img: 'https://images.unsplash.com/photo-1500648767791-00dcc994a43e?q=80&w=200&auto=format&fit=crop' },
    ],
    reviews: [
      { author: 'CinephileX', rating: 5, date: 'Yesterday', text: 'Superb quality and seamless streaming without any buffering or remux delays.', likes: 56 },
    ],
  }
}

export default function WatchPage({
  delivery,
  candidate,
  group,
  onBack,
  onSwitchVersion,
}) {
  const [isPlaying, setIsPlaying] = useState(true)
  const [currentTime, setCurrentTime] = useState(0)
  const [duration, setDuration] = useState(0)
  const [volume, setVolume] = useState(1)
  const [isMuted, setIsMuted] = useState(false)
  const [isFullscreen, setIsFullscreen] = useState(false)
  const [controlsVisible, setControlsVisible] = useState(true)
  const [copied, setCopied] = useState(false)
  const [hasPlaybackError, setHasPlaybackError] = useState(false)

  const videoRef = useRef(null)
  const playerContainerRef = useRef(null)
  const hideTimeoutRef = useRef(null)

  const title = delivery.candidate_title || candidate?.title || delivery.file_name || 'Movie'
  const meta = parseMovieMetadata(title, candidate?.display_text || candidate?.details || '')
  const extras = getMovieExtras(title)

  const [tmdbData, setTmdbData] = useState(null)

  useEffect(() => {
    getMovieMetadata(meta.cleanTitle, meta.year)
      .then((data) => {
        if (data && data.source !== 'fallback') {
          setTmdbData(data)
        }
      })
      .catch(() => {})
  }, [meta.cleanTitle, meta.year])

  // Subtitle & WebVTT State
  const [subtitleTracks, setSubtitleTracks] = useState([])
  const [selectedTrackId, setSelectedTrackId] = useState(null)
  const [isSubtitleMenuOpen, setIsSubtitleMenuOpen] = useState(false)
  const [subtitleOffset, setSubtitleOffset] = useState(0)
  const [isLoadingSubtitles, setIsLoadingSubtitles] = useState(false)
  const subtitleMenuRef = useRef(null)

  // Fetch available subtitle tracks
  useEffect(() => {
    if (!delivery.stream_url) return
    setIsLoadingSubtitles(true)
    getSubtitleTracks(delivery.stream_url, meta.cleanTitle, meta.year)
      .then((res) => {
        const tracks = res?.tracks || []
        setSubtitleTracks(tracks)
        const defaultTrack = tracks.find((t) => t.is_default)
        if (defaultTrack) {
          setSelectedTrackId(defaultTrack.id)
        }
      })
      .catch(() => {
        setSubtitleTracks([])
      })
      .finally(() => {
        setIsLoadingSubtitles(false)
      })
  }, [delivery.stream_url, meta.cleanTitle, meta.year])

  // Close subtitle menu on outside click
  useEffect(() => {
    const handleClickOutside = (e) => {
      if (subtitleMenuRef.current && !subtitleMenuRef.current.contains(e.target)) {
        setIsSubtitleMenuOpen(false)
      }
    }
    if (isSubtitleMenuOpen) {
      document.addEventListener('mousedown', handleClickOutside)
    }
    return () => {
      document.removeEventListener('mousedown', handleClickOutside)
    }
  }, [isSubtitleMenuOpen])

  // Programmatically sync TextTrack visibility
  useEffect(() => {
    if (videoRef.current && videoRef.current.textTracks) {
      for (let i = 0; i < videoRef.current.textTracks.length; i++) {
        const tt = videoRef.current.textTracks[i]
        tt.mode = selectedTrackId ? 'showing' : 'disabled'
      }
    }
  }, [selectedTrackId])

  const handleTrackLoad = (e) => {
    const track = e.target.track
    if (track) {
      track.mode = 'hidden'
      const syncActiveCues = () => {
        if (track.activeCues && track.activeCues.length > 0) {
          const text = Array.from(track.activeCues)
            .map((c) => c.text)
            .join('\n')
          setActiveCueText(text)
        } else {
          setActiveCueText('')
        }
      }
      track.oncuechange = syncActiveCues
      if (subtitleOffset !== 0 && track.cues) {
        for (let j = 0; j < track.cues.length; j++) {
          const cue = track.cues[j]
          cue.startTime += subtitleOffset
          cue.endTime += subtitleOffset
        }
      }
      syncActiveCues()
    }
  }

  const handleOffsetChange = (delta) => {
    const newOffset = Math.round((subtitleOffset + delta) * 10) / 10
    setSubtitleOffset(newOffset)
    if (videoRef.current && videoRef.current.textTracks) {
      for (let i = 0; i < videoRef.current.textTracks.length; i++) {
        const track = videoRef.current.textTracks[i]
        if (track.cues) {
          for (let j = 0; j < track.cues.length; j++) {
            const cue = track.cues[j]
            cue.startTime += delta
            cue.endTime += delta
          }
        }
      }
    }
  }

  const handleResetOffset = () => {
    const delta = -subtitleOffset
    handleOffsetChange(delta)
  }

  const activeSubtitleTrack = subtitleTracks.find((t) => t.id === selectedTrackId) || null
  const [subtitleBlobUrl, setSubtitleBlobUrl] = useState(null)
  const [isLoadingVtt, setIsLoadingVtt] = useState(false)
  const [activeCueText, setActiveCueText] = useState('')

  // Fetch VTT content and create a local same-origin Blob URL to bypass browser cross-origin track blocking
  useEffect(() => {
    if (!activeSubtitleTrack?.vtt_url) {
      setSubtitleBlobUrl(null)
      return
    }

    let isMounted = true
    let createdUrl = null
    setIsLoadingVtt(true)

    fetch(activeSubtitleTrack.vtt_url)
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`)
        return res.text()
      })
      .then((vttText) => {
        if (!isMounted) return
        const blob = new Blob([vttText], { type: 'text/vtt;charset=utf-8' })
        createdUrl = URL.createObjectURL(blob)
        setSubtitleBlobUrl(createdUrl)
      })
      .catch((err) => {
        console.warn('Failed to load subtitle VTT into blob:', err)
        if (isMounted) setSubtitleBlobUrl(null)
      })
      .finally(() => {
        if (isMounted) setIsLoadingVtt(false)
      })

    return () => {
      isMounted = false
      if (createdUrl) {
        URL.revokeObjectURL(createdUrl)
      }
    }
  }, [activeSubtitleTrack?.vtt_url])

  const synopsis = tmdbData?.overview || extras.synopsis
  const directors = tmdbData?.directors?.length > 0 ? tmdbData.directors.join(', ') : extras.directors
  const genres = tmdbData?.genres?.length > 0 ? tmdbData.genres : extras.genres
  const rating = tmdbData?.rating ? tmdbData.rating.toString() : extras.imdbRating
  const backdropUrl = tmdbData?.backdrop_url || null
  const castList =
    tmdbData?.cast?.length > 0
      ? tmdbData.cast.map((c) => ({
          name: c.name,
          role: c.character,
          img:
            c.profile_url ||
            'https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?q=80&w=200&auto=format&fit=crop',
        }))
      : extras.cast

  const effectiveWatchUrl = delivery.watch_url || delivery.player_url || delivery.stream_url
  const effectiveDownloadUrl = delivery.download_url || `${delivery.stream_url}&d=true`


  // Autohide controls on inactivity
  const handleMouseMove = () => {
    setControlsVisible(true)
    if (hideTimeoutRef.current) clearTimeout(hideTimeoutRef.current)
    if (isPlaying) {
      hideTimeoutRef.current = setTimeout(() => {
        setControlsVisible(false)
      }, 3500)
    }
  }

  useEffect(() => {
    return () => {
      if (hideTimeoutRef.current) clearTimeout(hideTimeoutRef.current)
    }
  }, [isPlaying])

  // Video event handlers
  const handleTimeUpdate = () => {
    if (videoRef.current) {
      setCurrentTime(videoRef.current.currentTime)
      if (selectedTrackId && videoRef.current.textTracks) {
        for (let i = 0; i < videoRef.current.textTracks.length; i++) {
          const tt = videoRef.current.textTracks[i]
          if (tt.mode === 'hidden' || tt.mode === 'showing') {
            if (tt.activeCues && tt.activeCues.length > 0) {
              const text = Array.from(tt.activeCues)
                .map((c) => c.text)
                .join('\n')
              setActiveCueText(text)
              return
            }
          }
        }
        setActiveCueText('')
      }
    }
  }

  const handleLoadedMetadata = () => {
    if (videoRef.current) {
      setDuration(videoRef.current.duration)
      videoRef.current.play().then(() => setIsPlaying(true)).catch(() => setIsPlaying(false))
    }
  }

  const togglePlay = () => {
    if (!videoRef.current) return
    if (isPlaying) {
      videoRef.current.pause()
      setIsPlaying(false)
      setControlsVisible(true)
    } else {
      videoRef.current.play()
      setIsPlaying(true)
    }
  }

  const handleSeek = (e) => {
    const time = parseFloat(e.target.value)
    setCurrentTime(time)
    if (videoRef.current) {
      videoRef.current.currentTime = time
    }
  }

  const skipTime = (seconds) => {
    if (videoRef.current) {
      videoRef.current.currentTime = Math.max(0, Math.min(duration, videoRef.current.currentTime + seconds))
    }
  }

  const handleVolumeChange = (e) => {
    const val = parseFloat(e.target.value)
    setVolume(val)
    if (videoRef.current) {
      videoRef.current.volume = val
      videoRef.current.muted = val === 0
      setIsMuted(val === 0)
    }
  }

  const toggleMute = () => {
    if (!videoRef.current) return
    if (isMuted) {
      videoRef.current.muted = false
      setIsMuted(false)
      videoRef.current.volume = volume || 0.5
    } else {
      videoRef.current.muted = true
      setIsMuted(true)
    }
  }

  const toggleFullscreen = () => {
    if (!playerContainerRef.current) return
    if (!document.fullscreenElement) {
      playerContainerRef.current.requestFullscreen().catch(() => {})
      setIsFullscreen(true)
    } else {
      document.exitFullscreen().catch(() => {})
      setIsFullscreen(false)
    }
  }

  const formatTime = (secs) => {
    if (isNaN(secs) || secs < 0) return '00:00'
    const h = Math.floor(secs / 3600)
    const m = Math.floor((secs % 3600) / 60)
    const s = Math.floor(secs % 60)
    if (h > 0) {
      return `${h}:${m < 10 ? '0' : ''}${m}:${s < 10 ? '0' : ''}${s}`
    }
    return `${m < 10 ? '0' : ''}${m}:${s < 10 ? '0' : ''}${s}`
  }

  const handleCopyLink = () => {
    const url = delivery.stream_url || delivery.watch_url
    if (url) {
      navigator.clipboard.writeText(url)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    }
  }

  const versions = group?.candidates || []
  const progressPercent = duration > 0 ? (currentTime / duration) * 100 : 0

  return (
    <div className="streamvibe-watch-container" style={{ position: 'relative' }}>
      {/* TMDb Ambient Backdrop Banner */}
      {backdropUrl && (
        <div
          style={{
            position: 'absolute',
            top: 0,
            left: 0,
            right: 0,
            height: '520px',
            backgroundImage: `url(${backdropUrl})`,
            backgroundSize: 'cover',
            backgroundPosition: 'center top',
            opacity: 0.18,
            filter: 'blur(20px)',
            pointerEvents: 'none',
            zIndex: 0,
            maskImage: 'linear-gradient(to bottom, rgba(0,0,0,1) 0%, rgba(0,0,0,0) 100%)',
            WebkitMaskImage: 'linear-gradient(to bottom, rgba(0,0,0,1) 0%, rgba(0,0,0,0) 100%)',
          }}
        />
      )}

      {/* Top Header & Breadcrumbs */}
      <div className="watch-nav-header" style={{ position: 'relative', zIndex: 1 }}>
        <button className="btn btn-secondary btn-back-ott" onClick={onBack}>
          <ArrowLeft size={18} />
          <span>Back to Browse</span>
        </button>

        <div className="watch-breadcrumbs-ott">
          <span className="crumb-link" onClick={onBack}>Movies & Shows</span>
          <span className="crumb-sep">/</span>
          <span className="crumb-active">{meta.cleanTitle}</span>
          {meta.year && <span className="crumb-year">({meta.year})</span>}
        </div>
      </div>

      {/* STREAMVIBE CUSTOM THEATER PLAYER */}
      <div
        ref={playerContainerRef}
        className={`streamvibe-player-box ${isFullscreen ? 'fullscreen-mode' : ''}`}
        onMouseMove={handleMouseMove}
        onMouseLeave={() => isPlaying && setControlsVisible(false)}
      >
        {/* Ambient Red Glow */}
        <div className="player-ambient-glow" />

        {/* Video Element */}
        <video
          ref={videoRef}
          className="streamvibe-video"
          src={delivery.stream_url}
          playsInline
          autoPlay
          onTimeUpdate={handleTimeUpdate}
          onLoadedMetadata={handleLoadedMetadata}
          onError={() => setHasPlaybackError(true)}
          onClick={togglePlay}
        >
          {activeSubtitleTrack && subtitleBlobUrl && (
            <track
              key={`${activeSubtitleTrack.id}-${subtitleBlobUrl}`}
              kind="subtitles"
              label={activeSubtitleTrack.label}
              srcLang={activeSubtitleTrack.language}
              src={subtitleBlobUrl}
              default
              onLoad={handleTrackLoad}
            />
          )}
        </video>

        {/* Big Center Play/Pause Button on Idle/Pause */}
        {(!isPlaying || controlsVisible) && !hasPlaybackError && (
          <div className="center-play-button-overlay" onClick={togglePlay}>
            <button className="center-play-btn" title={isPlaying ? 'Pause' : 'Play'}>
              {isPlaying ? (
                <Pause size={32} fill="#FFFFFF" color="#FFFFFF" />
              ) : (
                <Play size={32} fill="#FFFFFF" color="#FFFFFF" className="translate-play" />
              )}
            </button>
          </div>
        )}

        {/* StreamVibe Subtitle Overlay */}
        {activeCueText && (
          <div className={`streamvibe-subtitle-overlay ${controlsVisible ? 'with-controls' : 'no-controls'}`}>
            <span className="subtitle-text-bubble">{activeCueText}</span>
          </div>
        )}

        {/* Custom StreamVibe Controls Overlay */}
        <div className={`streamvibe-controls-bar ${controlsVisible ? 'visible' : 'hidden'}`}>
          {/* StreamVibe Red Scrub Progress Bar */}
          <div className="scrub-container">
            <input
              type="range"
              className="streamvibe-scrub"
              min="0"
              max={duration || 100}
              value={currentTime}
              onChange={handleSeek}
              style={{
                background: `linear-gradient(to right, #E50000 ${progressPercent}%, rgba(255,255,255,0.2) ${progressPercent}%)`,
              }}
            />
          </div>

          {/* Bottom Controls Row */}
          <div className="controls-row">
            {/* Left Controls: Play, Skip, Volume, Timestamps */}
            <div className="controls-left">
              <button className="ctrl-btn" onClick={togglePlay} title={isPlaying ? 'Pause' : 'Play'}>
                {isPlaying ? <Pause size={20} fill="#FFFFFF" /> : <Play size={20} fill="#FFFFFF" />}
              </button>

              <button className="ctrl-btn" onClick={() => skipTime(-10)} title="Rewind 10s">
                <RotateCcw size={18} />
              </button>

              <button className="ctrl-btn" onClick={() => skipTime(10)} title="Forward 10s">
                <RotateCw size={18} />
              </button>

              <div className="volume-group">
                <button className="ctrl-btn" onClick={toggleMute} title={isMuted ? 'Unmute' : 'Mute'}>
                  {isMuted || volume === 0 ? <VolumeX size={18} /> : volume < 0.5 ? <Volume1 size={18} /> : <Volume2 size={18} />}
                </button>
                <input
                  type="range"
                  className="volume-slider"
                  min="0"
                  max="1"
                  step="0.05"
                  value={isMuted ? 0 : volume}
                  onChange={handleVolumeChange}
                  style={{
                    background: `linear-gradient(to right, #E50000 ${(isMuted ? 0 : volume) * 100}%, rgba(255,255,255,0.2) ${(isMuted ? 0 : volume) * 100}%)`,
                  }}
                />
              </div>

              <div className="time-display">
                <span className="time-current">{formatTime(currentTime)}</span>
                <span className="time-sep">/</span>
                <span className="time-duration">{formatTime(duration)}</span>
              </div>
            </div>

            {/* Right Controls: Quality, CC Subtitles, Bot Web Player, Fullscreen */}
            <div className="controls-right">
              <span className="badge badge-quality badge-ctrl">
                {meta.resolution || '1080P'}
              </span>

              {/* Subtitles & Captions Menu */}
              <div className="subtitles-ctrl-wrapper" ref={subtitleMenuRef}>
                <button
                  className={`ctrl-btn ${selectedTrackId ? 'active-red' : ''}`}
                  onClick={() => setIsSubtitleMenuOpen(!isSubtitleMenuOpen)}
                  title={selectedTrackId ? `Subtitles: ${activeSubtitleTrack?.label || 'On'}` : 'Subtitles / Closed Captions'}
                >
                  {selectedTrackId ? <Captions size={19} /> : <CaptionsOff size={19} />}
                </button>

                {isSubtitleMenuOpen && (
                  <div className="subtitles-glass-menu">
                    <div className="subtitles-menu-header">
                      <div className="header-left">
                        <Captions size={15} className="text-primary" />
                        <span className="subtitles-menu-title">Subtitles & Audio</span>
                      </div>
                      {subtitleTracks.length > 0 && (
                        <span className="subtitles-count">{subtitleTracks.length} available</span>
                      )}
                    </div>

                    <div className="subtitles-track-list">
                      <button
                        className={`subtitle-track-item ${selectedTrackId === null ? 'active' : ''}`}
                        onClick={() => {
                          setSelectedTrackId(null)
                          setActiveCueText('')
                          setIsSubtitleMenuOpen(false)
                        }}
                      >
                        <div className="track-info">
                          <span className="track-label">Off</span>
                          <span className="track-sub">Captions disabled</span>
                        </div>
                        {selectedTrackId === null && <Check size={16} className="text-primary" />}
                      </button>

                      {isLoadingSubtitles && (
                        <div className="subtitles-loading-state">
                          <Sparkles size={14} className="spin-icon text-primary" />
                          <span>Detecting embedded subtitle tracks...</span>
                        </div>
                      )}

                      {isLoadingVtt && (
                        <div className="subtitles-loading-state">
                          <Sparkles size={14} className="spin-icon text-primary" />
                          <span>Syncing WebVTT captions...</span>
                        </div>
                      )}

                      {subtitleTracks.map((track) => {
                        const isSelected = selectedTrackId === track.id
                        return (
                          <button
                            key={track.id}
                            className={`subtitle-track-item ${isSelected ? 'active' : ''}`}
                            onClick={() => {
                              setSelectedTrackId(track.id)
                              setIsSubtitleMenuOpen(false)
                            }}
                          >
                            <div className="track-info">
                              <span className="track-label">{track.label}</span>
                              <div className="track-tags">
                                <span className="track-badge-lang">{track.language?.toUpperCase() || 'EN'}</span>
                                <span className={`track-badge-source ${track.type}`}>
                                  {track.type === 'embedded' ? 'Embedded' : 'Sync'}
                                </span>
                                {track.codec && <span className="track-badge-codec">{track.codec}</span>}
                              </div>
                            </div>
                            {isSelected && <Check size={16} className="text-primary" />}
                          </button>
                        )
                      })}
                    </div>

                    {/* Manual Timing Sync Offset */}
                    {selectedTrackId && (
                      <div className="subtitles-offset-section">
                        <div className="offset-label-row">
                          <span className="offset-title">Timing Sync</span>
                          <span className={`offset-value ${subtitleOffset !== 0 ? 'active' : ''}`}>
                            {subtitleOffset === 0
                              ? '0.0s'
                              : `${subtitleOffset > 0 ? '+' : ''}${subtitleOffset.toFixed(1)}s`}
                          </span>
                        </div>
                        <div className="offset-buttons-row">
                          <button
                            type="button"
                            className="btn-offset"
                            onClick={(e) => {
                              e.stopPropagation()
                              handleOffsetChange(-0.5)
                            }}
                            title="Appear 0.5s earlier (-0.5s)"
                          >
                            -0.5s
                          </button>
                          <button
                            type="button"
                            className="btn-offset btn-offset-reset"
                            onClick={(e) => {
                              e.stopPropagation()
                              handleResetOffset()
                            }}
                            disabled={subtitleOffset === 0}
                            title="Reset offset to 0.0s"
                          >
                            Reset
                          </button>
                          <button
                            type="button"
                            className="btn-offset"
                            onClick={(e) => {
                              e.stopPropagation()
                              handleOffsetChange(0.5)
                            }}
                            title="Appear 0.5s later (+0.5s)"
                          >
                            +0.5s
                          </button>
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>

              <a
                href={effectiveWatchUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="ctrl-btn"
                title="Open in Bot Web Player (External)"
              >
                <Tv size={18} />
              </a>

              <button className="ctrl-btn" onClick={toggleFullscreen} title={isFullscreen ? 'Exit Fullscreen' : 'Fullscreen'}>
                {isFullscreen ? <Minimize size={20} /> : <Maximize size={20} />}
              </button>
            </div>
          </div>
        </div>

        {/* Fallback Overlay for MKV / Unsupported Browser Codecs */}
        {hasPlaybackError && (
          <div className="streamvibe-player-error">
            <div className="error-card">
              <AlertCircle size={40} className="text-warning mb-2" />
              <h3>Direct Browser Playback Restricted</h3>
              <p>
                This video container (MKV) or video codec (HEVC) cannot be natively decoded by your browser.
                Click below to stream with the bot's web player or open in VLC.
              </p>
              <div className="error-buttons">
                <a
                  href={effectiveWatchUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="btn btn-primary"
                >
                  <Tv size={16} /> Open in Bot Web Player
                </a>
                <a
                  href={effectiveDownloadUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="btn btn-secondary"
                >
                  <Download size={16} /> Download Video ({formatBytes(delivery.file_size)})
                </a>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Stream Actions Toolbar */}
      <div className="stream-action-bar">
        <div className="action-bar-left">
          <a
            href={effectiveWatchUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="btn btn-primary"
          >
            <ExternalLink size={16} /> Open in Web Player
          </a>

          {delivery.download_url && (
            <a
              href={delivery.download_url}
              target="_blank"
              rel="noopener noreferrer"
              className="btn btn-secondary"
            >
              <Download size={16} /> Download
            </a>
          )}

          <button className="btn btn-secondary" onClick={handleCopyLink}>
            {copied ? (
              <>
                <Check size={16} className="text-success" />
                <span>Copied!</span>
              </>
            ) : (
              <>
                <Copy size={16} />
                <span>Copy Stream Link</span>
              </>
            )}
          </button>
        </div>

        <div className="action-bar-right">
          <span className="badge badge-quality">{delivery.mime_type || 'Video'}</span>
          <span className="stream-badge-bot">Powered by @stre89d_bot</span>
        </div>
      </div>

      {/* STREAMVIBE 2-COLUMN MOVIE DETAILS SECTION */}
      <div className="streamvibe-details-grid">
        {/* Left Column: Description, Cast, Reviews */}
        <div className="details-left-pane">
          {/* Description Section */}
          <div className="ott-card description-card">
            <h3 className="ott-section-title">Description</h3>
            <p className="ott-description-text">{synopsis}</p>
          </div>

          {/* Cast Carousel Section */}
          <div className="ott-card cast-card">
            <div className="ott-card-header">
              <h3 className="ott-section-title">Cast</h3>
              <div className="cast-nav-arrows">
                <button className="arrow-btn" title="Previous Cast">
                  <ChevronLeft size={16} />
                </button>
                <button className="arrow-btn" title="Next Cast">
                  <ChevronRight size={16} />
                </button>
              </div>
            </div>

            <div className="cast-carousel">
              {castList.map((actor, idx) => (
                <div key={idx} className="cast-member-card">
                  <div className="actor-img-box">
                    <img src={actor.img} alt={actor.name} className="actor-img" />
                  </div>
                  <span className="actor-name">{actor.name}</span>
                  <span className="actor-role">{actor.role}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Reviews Section */}
          <div className="ott-card reviews-card">
            <div className="ott-card-header">
              <div>
                <h3 className="ott-section-title">Reviews</h3>
                <span className="reviews-sub">What audiences are saying</span>
              </div>
              <button className="btn btn-secondary btn-sm">
                <MessageSquare size={14} /> Add Your Review
              </button>
            </div>

            <div className="reviews-list">
              {extras.reviews.map((rev, idx) => (
                <div key={idx} className="review-item-card">
                  <div className="review-header">
                    <div className="reviewer-info">
                      <div className="reviewer-avatar">{rev.author.slice(0, 2).toUpperCase()}</div>
                      <div>
                        <h4 className="reviewer-name">{rev.author}</h4>
                        <span className="review-date">{rev.date}</span>
                      </div>
                    </div>
                    <div className="review-stars">
                      {[...Array(5)].map((_, i) => (
                        <Star key={i} size={14} fill="#E50000" color="#E50000" />
                      ))}
                    </div>
                  </div>
                  <p className="review-text">{rev.text}</p>
                  <div className="review-footer">
                    <button className="btn-like">
                      <ThumbsUp size={13} /> {rev.likes}
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Right Column: Metadata Cards & Quality Switcher */}
        <div className="details-right-pane">
          {/* Release Year */}
          <div className="ott-info-card">
            <div className="info-card-header">
              <Calendar size={16} className="text-muted" />
              <span>Released Year</span>
            </div>
            <h4 className="info-card-value">{tmdbData?.year || meta.year || '2024'}</h4>
          </div>

          {/* Available Languages */}
          <div className="ott-info-card">
            <div className="info-card-header">
              <Globe size={16} className="text-muted" />
              <span>Available Languages</span>
            </div>
            <div className="languages-pills">
              {extras.languages.audio.map((lang) => (
                <span key={lang} className="badge">
                  {lang}
                </span>
              ))}
            </div>
          </div>

          {/* Ratings Card */}
          <div className="ott-info-card">
            <div className="info-card-header">
              <Star size={16} className="text-muted" />
              <span>Ratings</span>
            </div>
            <div className="ratings-grid">
              <div className="rating-box">
                <span className="rating-label">IMDb / TMDb</span>
                <div className="rating-score">
                  <Star size={14} fill="#FFD700" color="#FFD700" />
                  <span>{rating}</span>
                </div>
              </div>
              <div className="rating-box">
                <span className="rating-label">StreamVibe</span>
                <div className="rating-score">
                  <Star size={14} fill="#E50000" color="#E50000" />
                  <span>{extras.streamVibeRating}</span>
                </div>
              </div>
            </div>
          </div>

          {/* Genres */}
          <div className="ott-info-card">
            <div className="info-card-header">
              <Tag size={16} className="text-muted" />
              <span>Genres</span>
            </div>
            <div className="genres-pills">
              {genres.map((g) => (
                <span key={g} className="badge badge-quality">
                  {g}
                </span>
              ))}
            </div>
          </div>

          {/* Director & Music */}
          <div className="ott-info-card">
            <div className="info-card-header">
              <User size={16} className="text-muted" />
              <span>Director</span>
            </div>
            <h4 className="info-card-value text-sm">{directors}</h4>
            <div className="info-card-header mt-3">
              <Film size={16} className="text-muted" />
              <span>Music</span>
            </div>
            <h4 className="info-card-value text-sm">{extras.music}</h4>
          </div>


          {/* ON-THE-FLY RELEASES & QUALITY SWITCHER (Cineforge Power Feature) */}
          {versions.length > 1 && (
            <div className="ott-info-card versions-switcher-card">
              <div className="info-card-header">
                <Layers size={16} className="text-red" />
                <span>Available Releases ({versions.length})</span>
              </div>
              <p className="switcher-hint">
                Switch quality or audio tracks directly:
              </p>

              <div className="releases-list">
                {versions.map((ver, idx) => {
                  const verMeta = parseMovieMetadata(ver.title, ver.display_text || ver.size || '')
                  const isCurrent = (candidate?.candidate_id === ver.candidate_id) || (ver.title === candidate?.title)

                  return (
                    <div
                      key={ver.candidate_id || idx}
                      className={`release-item ${isCurrent ? 'active' : ''}`}
                      onClick={() => !isCurrent && onSwitchVersion(ver)}
                    >
                      <div className="release-left">
                        <div className="release-badges">
                          <span className="badge badge-quality">{ver.quality || verMeta.resolution}</span>
                          {(ver.size || verMeta.fileSize) && (
                            <span className="badge badge-sm">{ver.size || verMeta.fileSize}</span>
                          )}
                          {isCurrent && <span className="badge badge-red badge-sm">PLAYING</span>}
                        </div>
                        <span className="release-name" title={ver.display_text || ver.title}>
                          {ver.display_text || ver.title}
                        </span>
                      </div>
                      {!isCurrent && (
                        <button className="btn btn-secondary btn-sm btn-switch">
                          <Play size={10} fill="#FFFFFF" /> Switch
                        </button>
                      )}
                    </div>
                  )
                })}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
