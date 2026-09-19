/**
 * Thin client for the SpectraDerm FastAPI service.
 *
 * Every function here maps 1:1 to a route in spectraderm/api/routes. No screen
 * builds a URL by hand, so if the backend changes the change lands in one file.
 */

const BASE = import.meta.env.VITE_API_BASE_URL || '/api/v1'

export class ApiError extends Error {
  constructor(code, message, status) {
    super(message)
    this.name = 'ApiError'
    this.code = code
    this.status = status
  }
}

async function request(path, { method = 'GET', body, query, signal } = {}) {
  const url = new URL(`${BASE}${path}`, window.location.origin)
  Object.entries(query || {}).forEach(([key, value]) => {
    if (value !== undefined && value !== null) url.searchParams.set(key, value)
  })

  let response
  try {
    response = await fetch(url, {
      method,
      signal,
      headers: body instanceof FormData ? undefined : { 'Content-Type': 'application/json' },
      body: body instanceof FormData ? body : body ? JSON.stringify(body) : undefined,
    })
  } catch (error) {
    if (error.name === 'AbortError') throw error
    throw new ApiError(
      'NETWORK_UNREACHABLE',
      'The SpectraDerm service did not respond. Check that the API is running, then try again.',
      0,
    )
  }

  if (response.status === 204) return null

  const payload = await response.json().catch(() => null)
  if (!response.ok) {
    const detail = payload && payload.error ? payload.error : {}
    throw new ApiError(
      detail.code || 'UNEXPECTED_ERROR',
      detail.message || 'The request could not be completed.',
      response.status,
    )
  }
  return payload
}

export const api = {
  health: () => fetch('/health').then((r) => r.ok),

  createUser: (generalConsent = true, locationConsent = false) =>
    request('/users', {
      method: 'POST',
      body: { general_consent: generalConsent, location_consent: locationConsent },
    }),

  getUser: (userId) => request(`/users/${userId}`),

  updateConsent: (userId, patch) =>
    request(`/users/${userId}/consent`, { method: 'PATCH', body: patch }),

  uploadImage: (userId, file) => {
    const form = new FormData()
    form.append('file', file)
    return request(`/users/${userId}/image-artifacts`, { method: 'POST', body: form })
  },

  createScan: (userId, imageReference) =>
    request(`/users/${userId}/scans`, {
      method: 'POST',
      body: { image_reference: imageReference },
    }),

  listScans: (userId) => request(`/users/${userId}/scans`),

  history: (userId) => request(`/users/${userId}/history`),

  getScan: (scanId, userId) => request(`/scans/${scanId}`, { query: { user_id: userId } }),

  deleteScan: (scanId, userId) =>
    request(`/scans/${scanId}`, { method: 'DELETE', query: { user_id: userId } }),

  analyze: (scanId, userId, input = {}) =>
    request(`/scans/${scanId}/analyze`, {
      method: 'POST',
      query: { user_id: userId },
      body: { input },
    }),

  report: (scanId, userId) => request(`/scans/${scanId}/report`, { query: { user_id: userId } }),

  monitoringReport: (scanId, userId) =>
    request(`/scans/${scanId}/monitoring-report`, { query: { user_id: userId } }),

  products: (scanId, userId) => request(`/scans/${scanId}/products`, { query: { user_id: userId } }),

  referrals: (scanId, userId, location) =>
    request(`/scans/${scanId}/referrals`, {
      method: 'POST',
      query: { user_id: userId },
      body: {
        city: location.city ?? null,
        latitude: location.latitude ?? null,
        longitude: location.longitude ?? null,
        radius_km: location.radiusKm ?? 25,
      },
    }),
}
