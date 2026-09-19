/**
 * Browser-local companion data.
 *
 * The API returns scan records without change scores or thumbnails, so the
 * history screen keeps a small local cache keyed by scan id. Nothing here is a
 * source of truth; it only makes the timeline readable between sessions.
 */

const USER_KEY = 'spectraderm.user_id'
const CACHE_KEY = 'spectraderm.scan_cache'

function read(key, fallback) {
  try {
    const raw = window.localStorage.getItem(key)
    return raw ? JSON.parse(raw) : fallback
  } catch {
    return fallback
  }
}

function write(key, value) {
  try {
    window.localStorage.setItem(key, JSON.stringify(value))
  } catch {
    /* storage unavailable (private mode, quota) — the app still works */
  }
}

export const store = {
  getUserId: () => {
    try {
      return window.localStorage.getItem(USER_KEY)
    } catch {
      return null
    }
  },

  setUserId: (userId) => {
    try {
      window.localStorage.setItem(USER_KEY, userId)
    } catch {
      /* ignore */
    }
  },

  clearUser: () => {
    try {
      window.localStorage.removeItem(USER_KEY)
      window.localStorage.removeItem(CACHE_KEY)
    } catch {
      /* ignore */
    }
  },

  getScanCache: () => read(CACHE_KEY, {}),

  getScanEntry: (scanId) => read(CACHE_KEY, {})[scanId] || null,

  saveScanEntry: (scanId, entry) => {
    const cache = read(CACHE_KEY, {})
    cache[scanId] = { ...(cache[scanId] || {}), ...entry }
    write(CACHE_KEY, cache)
  },

  dropScanEntry: (scanId) => {
    const cache = read(CACHE_KEY, {})
    delete cache[scanId]
    write(CACHE_KEY, cache)
  },
}

/** Downscaled data URL so history thumbnails never blow past the storage quota. */
export function makeThumbnail(file, size = 160) {
  return new Promise((resolve) => {
    const reader = new FileReader()
    reader.onerror = () => resolve(null)
    reader.onload = () => {
      const image = new Image()
      image.onerror = () => resolve(null)
      image.onload = () => {
        const side = Math.min(image.width, image.height)
        const canvas = document.createElement('canvas')
        canvas.width = size
        canvas.height = size
        const context = canvas.getContext('2d')
        context.drawImage(
          image,
          (image.width - side) / 2,
          (image.height - side) / 2,
          side,
          side,
          0,
          0,
          size,
          size,
        )
        resolve(canvas.toDataURL('image/jpeg', 0.7))
      }
      image.src = reader.result
    }
    reader.readAsDataURL(file)
  })
}
