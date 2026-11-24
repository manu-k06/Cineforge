import http from 'node:http'

// 1. Test Browser Mode (isTauri is false)
console.log('--- Test 1: Browser Mode Routing ---')
delete globalThis.window
globalThis.window = {}

const apiModule = await import('./src/services/api.js')
const browserUrl = await apiModule.resolveApiBase(true)
console.log('Browser mode resolved API base:', JSON.stringify(browserUrl))
if (browserUrl.startsWith('http://127.0.0.1:')) {
  console.error('FAIL: Browser mode unexpectedly bound to local 127.0.0.1 without Tauri!')
  process.exit(1)
} else {
  console.log('PASS: Browser mode uses existing web/Supabase discovery or fallback.')
}

// 2. Test Desktop Mode (isTauri is true) with healthy Rust mock server
console.log('\n--- Test 2: Desktop Mode Routing (Healthy Rust Backend) ---')
const requestedEndpoints = []
const testServer = http.createServer((req, res) => {
  const url = new URL(req.url, 'http://127.0.0.1')
  requestedEndpoints.push(url.pathname)

  if (url.pathname === '/health') {
    res.writeHead(200, { 'Content-Type': 'application/json' })
    res.end(JSON.stringify({ status: 'ok', service: 'cineforge-backend', engine: 'rust-axum' }))
  } else if (url.pathname === '/api/metadata/status') {
    res.writeHead(200, { 'Content-Type': 'application/json' })
    res.end(JSON.stringify({ status: 'ready', configured: true }))
  } else if (url.pathname === '/api/metadata/movie') {
    res.writeHead(200, { 'Content-Type': 'application/json' })
    res.end(
      JSON.stringify({
        title: url.searchParams.get('title') || 'Unknown',
        year: url.searchParams.get('year') || '2010',
        rating: 8.8,
        source: 'tmdb',
      })
    )
  } else if (url.pathname === '/api/metadata/trending') {
    res.writeHead(200, { 'Content-Type': 'application/json' })
    res.end(
      JSON.stringify({
        page: 1,
        total_pages: 5,
        results: [
          {
            title: 'Inception',
            year: '2010',
            rating: 8.8,
            source: 'tmdb',
            release_date: '2010-07-16',
            poster_url: 'https://image.tmdb.org/t/p/w500/mock_inception.jpg',
            vote_count: 35000,
          },
        ],
      })
    )
  } else if (url.pathname === '/api/metadata/popular') {
    res.writeHead(200, { 'Content-Type': 'application/json' })
    res.end(
      JSON.stringify({
        page: 1,
        total_pages: 5,
        results: [
          {
            title: 'Interstellar',
            year: '2014',
            rating: 8.6,
            source: 'tmdb',
            release_date: '2014-11-07',
            poster_url: 'https://image.tmdb.org/t/p/w500/mock_interstellar.jpg',
            vote_count: 32000,
          },
        ],
      })
    )
  } else if (url.pathname === '/api/metadata/top-rated') {
    res.writeHead(200, { 'Content-Type': 'application/json' })
    res.end(
      JSON.stringify({
        page: 1,
        total_pages: 5,
        results: [
          {
            title: 'The Dark Knight',
            year: '2008',
            rating: 9.0,
            source: 'tmdb',
            release_date: '2008-07-18',
            poster_url: 'https://image.tmdb.org/t/p/w500/mock_tdk.jpg',
            vote_count: 31000,
          },
        ],
      })
    )
  } else if (url.pathname === '/api/metadata/discover') {
    res.writeHead(200, { 'Content-Type': 'application/json' })
    res.end(
      JSON.stringify({
        page: 1,
        total_pages: 3,
        results: [
          {
            title: 'Manichitrathazhu',
            year: '1993',
            rating: 8.9,
            source: 'tmdb',
            release_date: '1993-12-25',
            poster_url: 'https://image.tmdb.org/t/p/w500/mock_mani.jpg',
            vote_count: 500,
          },
        ],
      })
    )
  } else if (url.pathname === '/api/telegram/auth/status') {
    res.writeHead(200, { 'Content-Type': 'application/json' })
    res.end(JSON.stringify({ connected: false, status: 'disconnected', user: null }))
  } else if (url.pathname === '/api/telegram/auth/qr/start') {
    res.writeHead(200, { 'Content-Type': 'application/json' })
    res.end(JSON.stringify({ qr_uri: 'tg://login?token=mock_123', qr_svg: '<svg></svg>', expires_in: 60 }))
  } else if (url.pathname === '/api/telegram/auth/qr/check') {
    res.writeHead(200, { 'Content-Type': 'application/json' })
    res.end(JSON.stringify({ status: 'connected', message: 'Approved', user: { id: 12345, first_name: 'TestUser' } }))
  } else if (url.pathname === '/api/telegram/auth/phone') {
    res.writeHead(200, { 'Content-Type': 'application/json' })
    res.end(JSON.stringify({ status: 'code_pending', message: 'Code sent' }))
  } else if (url.pathname === '/api/telegram/auth/code') {
    res.writeHead(200, { 'Content-Type': 'application/json' })
    res.end(JSON.stringify({ status: 'connected', message: 'Verified', user: { id: 12345, first_name: 'TestUser' } }))
  } else if (url.pathname === '/api/telegram/auth/password') {
    res.writeHead(200, { 'Content-Type': 'application/json' })
    res.end(JSON.stringify({ status: 'connected', message: '2FA verified', user: { id: 12345, first_name: 'TestUser' } }))
  } else if (url.pathname === '/api/telegram/auth/disconnect') {
    res.writeHead(200, { 'Content-Type': 'application/json' })
    res.end(JSON.stringify({ status: 'disconnected', message: 'Disconnected' }))
  } else if (url.pathname === '/api/search') {
    res.writeHead(200, { 'Content-Type': 'application/json' })
    res.end(
      JSON.stringify({
        query: url.searchParams.get('q') || 'Inception',
        candidates: [
          {
            candidate_id: 'cand-1',
            title: 'Inception (2010)',
            display_text: 'Inception 2010 1080p BluRay',
            quality: '1080P',
            container: 'mp4',
            size: '2.4 GB',
            language: 'English',
            source_bot: 'Spoty_xbot',
            callback_data: 'cb_1080p',
          },
        ],
        title_groups: {
          'Inception (2010)': [
            {
              candidate_id: 'cand-1',
              title: 'Inception (2010)',
              quality: '1080P',
              container: 'mp4',
              size: '2.4 GB',
            },
          ],
        },
        pagination: {
          current_page: 1,
          total_pages: 3,
          total_results: 15,
          has_next: true,
        },
        channel_requirement: null,
        metadata_enrichment: {},
        is_cached: false,
      })
    )
  } else if (url.pathname === '/api/search/suggestions') {
    res.writeHead(200, { 'Content-Type': 'application/json' })
    res.end(
      JSON.stringify({
        query: url.searchParams.get('q') || '',
        suggestions: [
          {
            id: 27205,
            title: 'Inception',
            year: '2010',
            rating: '8.8',
            media_type: 'movie',
            overview: 'Dream within a dream',
          },
        ],
      })
    )
  } else if (url.pathname === '/api/search/select') {
    res.writeHead(200, { 'Content-Type': 'application/json' })
    res.end(
      JSON.stringify({
        status: 'resolved',
        resolved_type: 'bot_callback',
        target_bot: 'Spoty_xbot',
        action_summary: 'Sent callback to bot',
        details: { callback_data: 'cb_1080p' },
        channel_requirement: null,
      })
    )
  } else if (url.pathname === '/api/search/deliver') {
    let bodyStr = ''
    req.on('data', (chunk) => {
      bodyStr += chunk
    })
    req.on('end', () => {
      const parsed = JSON.parse(bodyStr || '{}')
      if (parsed.candidate_id === 'cand-locked') {
        res.writeHead(403, { 'Content-Type': 'application/json' })
        res.end(
          JSON.stringify({
            detail: 'Channel membership required',
            channel_requirement: { required: true, invite_url: 'https://t.me/cineforge' },
          })
        )
        return
      }

      res.writeHead(200, { 'Content-Type': 'application/json' })
      res.end(
        JSON.stringify({
          success: true,
          candidate_title: parsed.candidate_title || 'Inception (2010)',
          delivered_chat_id: 'me',
          delivered_message_id: 1000,
          file_name: 'Inception.2010.1080p.mp4',
          mime_type: 'video/mp4',
          file_size: 10485760,
          browser_playable: true,
          container: 'mp4',
          playback_mode: 'browser',
          session_id: 'sess_1000',
          stream_url: `http://127.0.0.1:${testPort}/api/stream/1000?hash=mock_hash`,
          player_url: `http://127.0.0.1:${testPort}/api/stream/1000?hash=mock_hash`,
          watch_url: `http://127.0.0.1:${testPort}/api/stream/1000?hash=mock_hash`,
          download_url: `http://127.0.0.1:${testPort}/api/stream/1000?hash=mock_hash&d=true`,
          elapsed_seconds: 0.42,
        })
      )
    })
  } else if (url.pathname.startsWith('/api/stream/')) {
    const rangeHeader = req.headers['range']
    if (rangeHeader) {
      res.writeHead(206, {
        'Content-Type': 'video/mp4',
        'Content-Range': 'bytes 0-1023/10485760',
        'Content-Length': '1024',
        'Accept-Ranges': 'bytes',
      })
      res.end(Buffer.alloc(1024, 0))
    } else {
      res.writeHead(200, {
        'Content-Type': 'video/mp4',
        'Content-Length': '10485760',
        'Accept-Ranges': 'bytes',
      })
      res.end(Buffer.alloc(4096, 0))
    }
  } else {
    res.writeHead(404)
    res.end()
  }
})

await new Promise((resolve) => testServer.listen(0, '127.0.0.1', resolve))
const testPort = testServer.address().port
console.log(`Mock Rust Axum server running on http://127.0.0.1:${testPort}`)

// Mock Tauri internals
globalThis.window.__TAURI_INTERNALS__ = {
  invoke: async (cmd) => {
    if (cmd === 'get_backend_info') {
      return {
        status: 'online',
        host: '127.0.0.1',
        port: testPort,
        api_url: `http://127.0.0.1:${testPort}`,
        engine: 'rust-axum',
      }
    }
    throw new Error(`Unknown command ${cmd}`)
  },
}

const desktopUrl = await apiModule.resolveApiBase(true)
console.log('Desktop mode resolved API base:', desktopUrl)
if (desktopUrl === `http://127.0.0.1:${testPort}`) {
  console.log('PASS: Desktop mode correctly resolved to local Rust backend!')
} else {
  console.error(`FAIL: Expected http://127.0.0.1:${testPort}, got ${desktopUrl}`)
  process.exit(1)
}

// Verify checkRustBackendHealth
const health = await apiModule.checkRustBackendHealth()
console.log('Desktop health check result:', health)
if (health && health.status === 'ok') {
  console.log('PASS: checkRustBackendHealth succeeded.')
} else {
  console.error('FAIL: checkRustBackendHealth failed.')
  process.exit(1)
}

// Verify Desktop Metadata routing to Rust backend
console.log('\n--- Test 3: Desktop Metadata Routing to Local Rust Backend ---')
const statusRes = await apiModule.getMetadataStatus()
console.log('Metadata status:', statusRes)
if (statusRes.status !== 'ready' || !statusRes.configured) {
  console.error('FAIL: Expected status ready from local backend, got', statusRes)
  process.exit(1)
}

const movieMeta = await apiModule.getMovieMetadata('Inception', 2010)
console.log('Movie metadata result:', movieMeta.title, movieMeta.year)
if (movieMeta.title !== 'Inception') {
  console.error('FAIL: Expected Inception movie metadata, got', movieMeta)
  process.exit(1)
}

const trending = await apiModule.getTrendingMovies('week', 1)
console.log('Trending movies result count:', trending.results?.length)
if (!trending.results || trending.results.length === 0) {
  console.error('FAIL: Expected trending movies from local backend, got', trending)
  process.exit(1)
}

const popular = await apiModule.getPopularMovies(1)
console.log('Popular movies result count:', popular.results?.length)
if (!popular.results || popular.results.length === 0) {
  console.error('FAIL: Expected popular movies from local backend, got', popular)
  process.exit(1)
}

const topRated = await apiModule.getTopRatedMovies(1)
console.log('Top rated movies result count:', topRated.results?.length)
if (!topRated.results || topRated.results.length === 0) {
  console.error('FAIL: Expected top rated movies from local backend, got', topRated)
  process.exit(1)
}

const regional = await apiModule.getRegionalMovies('ml', 1)
console.log('Regional movies result count:', regional.results?.length)
if (!regional.results || regional.results.length === 0) {
  console.error('FAIL: Expected regional movies from local backend, got', regional)
  process.exit(1)
}

console.log('Endpoints requested on local Rust server:', requestedEndpoints)
const expectedEndpoints = [
  '/health',
  '/api/metadata/status',
  '/api/metadata/movie',
  '/api/metadata/trending',
  '/api/metadata/popular',
  '/api/metadata/top-rated',
  '/api/metadata/discover',
]
for (const exp of expectedEndpoints) {
  if (!requestedEndpoints.includes(exp)) {
    console.error(`FAIL: Expected endpoint ${exp} was not requested on local Rust server!`)
    process.exit(1)
  }
}
console.log('PASS: All desktop metadata requests reached the local backend!')

// Test 3.5: Desktop Telegram Auth Routing
console.log('\n--- Test 3.5: Desktop Telegram Auth Routing to Local Rust Backend ---')
const tgStatus = await apiModule.getTelegramAuthStatus()
console.log('Telegram status result:', tgStatus)
if (tgStatus.connected !== false) {
  console.error('FAIL: Expected disconnected status, got', tgStatus)
  process.exit(1)
}

const tgQr = await apiModule.startTelegramQr()
console.log('Telegram QR result:', tgQr.qr_uri)
if (!tgQr.qr_uri.startsWith('tg://login?token=')) {
  console.error('FAIL: Expected QR uri, got', tgQr)
  process.exit(1)
}

const tgQrCheck = await apiModule.checkTelegramQr()
console.log('Telegram QR check result:', tgQrCheck.status)
if (tgQrCheck.status !== 'connected') {
  console.error('FAIL: Expected connected on QR check, got', tgQrCheck)
  process.exit(1)
}

const tgPhone = await apiModule.requestTelegramPhoneCode('+1234567890')
console.log('Telegram phone request result:', tgPhone.status)
if (tgPhone.status !== 'code_pending') {
  console.error('FAIL: Expected code_pending, got', tgPhone)
  process.exit(1)
}

const tgCode = await apiModule.submitTelegramCode('12345')
console.log('Telegram code submit result:', tgCode.status)
if (tgCode.status !== 'connected') {
  console.error('FAIL: Expected connected on code submit, got', tgCode)
  process.exit(1)
}

const tgPwd = await apiModule.submitTelegramPassword('mypassword')
console.log('Telegram password submit result:', tgPwd.status)
if (tgPwd.status !== 'connected') {
  console.error('FAIL: Expected connected on password submit, got', tgPwd)
  process.exit(1)
}

const tgDisc = await apiModule.disconnectTelegram()
console.log('Telegram disconnect result:', tgDisc.status)
if (tgDisc.status !== 'disconnected') {
  console.error('FAIL: Expected disconnected on disconnect, got', tgDisc)
  process.exit(1)
}

const tgEndpoints = [
  '/api/telegram/auth/status',
  '/api/telegram/auth/qr/start',
  '/api/telegram/auth/qr/check',
  '/api/telegram/auth/phone',
  '/api/telegram/auth/code',
  '/api/telegram/auth/password',
  '/api/telegram/auth/disconnect',
]
for (const exp of tgEndpoints) {
  if (!requestedEndpoints.includes(exp)) {
    console.error(`FAIL: Expected endpoint ${exp} was not requested on local Rust server!`)
    process.exit(1)
  }
}
console.log('PASS: All desktop Telegram auth requests reached the local backend!')

// Test 3.6: Desktop Telegram Search & Candidate Selection Routing
console.log('\n--- Test 3.6: Desktop Telegram Search & Candidate Selection Routing ---')
const searchResults = await apiModule.searchMovies('Inception', 1)
console.log('Search candidates count:', searchResults.candidates?.length)
if (!searchResults.candidates || searchResults.candidates.length === 0) {
  console.error('FAIL: Expected search candidates from local backend, got', searchResults)
  process.exit(1)
}

const suggestions = await apiModule.getSearchSuggestions('Incep', 5)
console.log('Search suggestions count:', suggestions.length)
if (!suggestions || suggestions.length === 0) {
  console.error('FAIL: Expected suggestions from local backend, got', suggestions)
  process.exit(1)
}

const selectedCand = await apiModule.selectCandidate(searchResults.candidates[0])
console.log('Candidate selection status:', selectedCand.status)
if (selectedCand.status !== 'resolved') {
  console.error('FAIL: Expected resolved selection, got', selectedCand)
  process.exit(1)
}

const searchEndpoints = [
  '/api/search',
  '/api/search/suggestions',
  '/api/search/select',
]
for (const exp of searchEndpoints) {
  if (!requestedEndpoints.includes(exp)) {
    console.error(`FAIL: Expected endpoint ${exp} was not requested on local Rust server!`)
    process.exit(1)
  }
}
console.log('PASS: All desktop search and candidate selection requests reached the local backend!')

// Test 3.7: Desktop Telegram Delivery & Progressive Streaming Routing
console.log('\n--- Test 3.7: Desktop Telegram Delivery & Progressive Streaming Routing ---')
const deliveryResult = await apiModule.deliverCandidate({
  candidate_id: 'cand-1',
  title: 'Inception (2010)',
  source_bot: 'Spoty_xbot',
  source_message_id: 1000,
  callback_data: 'cb_1080p',
  quality: '1080P',
})
console.log('Candidate delivery result:', deliveryResult.success, deliveryResult.stream_url)
if (!deliveryResult.success || !deliveryResult.stream_url.startsWith(`http://127.0.0.1:${testPort}/api/stream/`)) {
  console.error('FAIL: Expected local streamer URL from deliverCandidate, got', deliveryResult)
  process.exit(1)
}

// Verify byte-range streaming proxy
const rangeRes = await fetch(deliveryResult.stream_url, {
  headers: { Range: 'bytes=0-1023' },
})
console.log('Stream byte range response status:', rangeRes.status)
if (rangeRes.status !== 206) {
  console.error(`FAIL: Expected HTTP 206 Partial Content, got ${rangeRes.status}`)
  process.exit(1)
}
const contentRange = rangeRes.headers.get('content-range')
console.log('Content-Range header:', contentRange)
if (!contentRange || !contentRange.includes('bytes 0-1023/')) {
  console.error('FAIL: Missing or invalid Content-Range header:', contentRange)
  process.exit(1)
}

// Verify desktop error propagation (no silent fallback to BigBuckBunny)
try {
  await apiModule.deliverCandidate({
    candidate_id: 'cand-locked',
    title: 'Locked Movie',
    source_bot: 'Spoty_xbot',
  })
  console.error('FAIL: deliverCandidate in desktop mode should have thrown an error on 403 Forbidden!')
  process.exit(1)
} catch (err) {
  console.log('PASS: Desktop mode threw clear error for locked candidate:', err.message)
  if (!err.channel_requirement) {
    console.error('FAIL: Expected channel_requirement to be attached to error!')
    process.exit(1)
  }
}
console.log('PASS: Desktop Telegram delivery and byte-range streaming routing verified!')

// 4. Test Desktop Mode Error Handling (Unhealthy / Offline Rust Backend)
console.log('\n--- Test 4: Desktop Mode Error Handling (Offline Backend) ---')
testServer.closeAllConnections?.()
await new Promise((resolve) => testServer.close(resolve))

try {
  await apiModule.resolveApiBase(true)
  console.error('FAIL: Desktop mode should have thrown an error when local backend is offline!')
  process.exit(1)
} catch (err) {
  console.log('PASS: Desktop mode correctly rejected fallback and threw error:', err.message)
}

console.log('\nAll desktop & browser routing tests passed successfully!')
