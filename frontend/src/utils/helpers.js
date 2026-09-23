/**
 * Utility helpers for formatting metadata, resolutions, sizes, and poster themes
 */

// Parse candidate title to extract cleaned movie title, year, resolution, and audio
export function parseMovieMetadata(rawTitle, rawDetails = '') {
  const combined = `${rawTitle} ${rawDetails}`

  // Year regex (1900 - 2099)
  const yearMatch = combined.match(/\b(19\d\d|20\d\d)\b/)
  const year = yearMatch ? yearMatch[1] : ''

  // Resolution detection
  let resolution = '1080P'
  if (/\b(4k|2160p|uhd)\b/i.test(combined)) {
    resolution = '4K UHD'
  } else if (/\b(1080p|fhd)\b/i.test(combined)) {
    resolution = '1080P'
  } else if (/\b(720p|hd)\b/i.test(combined)) {
    resolution = '720P'
  } else if (/\b(480p|sd)\b/i.test(combined)) {
    resolution = '480P'
  }

  // Codec / Quality detection
  const tags = []
  if (/hevc|x265|h\.?265/i.test(combined)) tags.push('HEVC')
  if (/hdr|dolby|dovi/i.test(combined)) tags.push('HDR')
  if (/dual\s*audio|multi/i.test(combined)) tags.push('Dual Audio')
  if (/remux|bluray/i.test(combined)) tags.push('BluRay')

  // Clean title
  let cleanTitle = rawTitle
    .replace(/\[\s*[\d\.]+\s*(?:MB|GB|GiB|MiB)\s*\]/gi, '')
    .replace(/\.(?:mkv|mp4|avi|webm|mov)$/i, '')
    .replace(/\b(?:mkv|mp4|avi|webm|mov)\b/gi, '')
    .replace(/(\d{4})(?=\d{3,4}p)/g, '$1 ')
    .replace(/@[\w\d_]+/g, '')
    .replace(/\b\d*(?:tamilmv|tamilblasters|cinemavilla|moviesda|filmywap|cineforge|spoty_xbot)[\w\.-]*/gi, '')
    .replace(/\[.*?\]|\(.*?\)/g, '')
    .replace(/\b(1080p|720p|480p|2160p|4k|uhd|hevc|x264|x265|bluray|web-?dl|webrip|hdrip|hdtv|esubs?|dual\s*audio|multi\s*sub|proper|repack|org\s*audio)\b.*/i, '')
    .replace(/[._\-–—]/g, ' ')
    .replace(/\s+/g, ' ')
    .trim()

  if (year && cleanTitle.endsWith(year)) {
    cleanTitle = cleanTitle.slice(0, -year.length).trim()
  }

  if (!cleanTitle || cleanTitle.length < 2) {
    cleanTitle = rawTitle.replace(/[._]/g, ' ').trim()
  }

  // Extract file size if available in details or title
  const sizeMatch = combined.match(/(\d+(\.\d+)?\s*(GB|MB|GiB|MiB))/i)
  const fileSize = sizeMatch ? sizeMatch[0] : ''

  return {
    cleanTitle,
    year,
    resolution,
    fileSize,
    tags: tags.slice(0, 3),
  }
}

// Generate consistent cinematic gradient colors based on string hash
export function getPosterGradient(title) {
  const gradients = [
    'linear-gradient(135deg, #1f0b0b 0%, #3d1414 50%, #141414 100%)',
    'linear-gradient(135deg, #0d1b2a 0%, #1b263b 50%, #141414 100%)',
    'linear-gradient(135deg, #1b122c 0%, #2e1c4a 50%, #141414 100%)',
    'linear-gradient(135deg, #142217 0%, #1e3a24 50%, #141414 100%)',
    'linear-gradient(135deg, #2b1704 0%, #4a2707 50%, #141414 100%)',
  ]
  let hash = 0
  for (let i = 0; i < title.length; i++) {
    hash = title.charCodeAt(i) + ((hash << 5) - hash)
  }
  return gradients[Math.abs(hash) % gradients.length]
}

// Format bytes to human readable
export function formatBytes(bytes, decimals = 2) {
  if (!bytes || bytes === 0) return '0 B'
  const k = 1024
  const dm = decimals < 0 ? 0 : decimals
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i]
}

// Wrap TMDb image paths with Cloudflare wsrv.nl image proxy to bypass ISP throttling and convert to WebP
export function getOptimizedImageUrl(rawPath, size = 'w500') {
  if (!rawPath) return null
  let fullUrl = String(rawPath).trim()
  if (fullUrl.startsWith('/')) {
    fullUrl = `https://image.tmdb.org/t/p/${size}${fullUrl}`
  } else if (!fullUrl.startsWith('http://') && !fullUrl.startsWith('https://')) {
    fullUrl = `https://image.tmdb.org/t/p/${size}/${fullUrl}`
  }

  // If already proxied via wsrv.nl, return as is
  if (fullUrl.includes('wsrv.nl')) return fullUrl

  // Proxy through Cloudflare-backed wsrv.nl edge CDN
  return `https://wsrv.nl/?url=${encodeURIComponent(fullUrl)}&output=webp`
}
