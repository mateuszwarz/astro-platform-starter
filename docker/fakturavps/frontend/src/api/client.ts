import axios from 'axios'

/**
 * Tokeny przechowywane w pamięci (in-memory) zamiast localStorage.
 * localStorage jest podatne na XSS — każdy skrypt na stronie mógłby odczytać token.
 * In-memory: tokeny żyją tylko w czasie sesji przeglądarki i nie są dostępne z JS innych skryptów.
 *
 * Refresh token przechowywany w sessionStorage (nie localStorage) — czyszczony przy zamknięciu karty.
 * Access token tylko w pamięci — odtwarzany z refresh tokenu po przeładowaniu.
 */

let _accessToken: string | null = null

export const tokenStore = {
  setAccessToken(token: string) {
    _accessToken = token
  },
  getAccessToken(): string | null {
    return _accessToken
  },
  setRefreshToken(token: string) {
    // sessionStorage — usuwane po zamknięciu karty/okna
    sessionStorage.setItem('rt', token)
  },
  getRefreshToken(): string | null {
    return sessionStorage.getItem('rt')
  },
  clear() {
    _accessToken = null
    sessionStorage.removeItem('rt')
  },
}

const apiClient = axios.create({
  baseURL: '/api/v1',
  headers: { 'Content-Type': 'application/json' },
  timeout: 15000,
  withCredentials: false,
})

// ── Request interceptor: dodaj Bearer token ────────────────────────────────
apiClient.interceptors.request.use((config) => {
  const token = tokenStore.getAccessToken()
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// ── Response interceptor: auto-refresh po 401 ─────────────────────────────
let isRefreshing = false
let failedQueue: Array<{ resolve: (v: string) => void; reject: (e: unknown) => void }> = []

const processQueue = (error: unknown, token: string | null = null) => {
  failedQueue.forEach(({ resolve, reject }) => {
    if (error) reject(error)
    else resolve(token!)
  })
  failedQueue = []
}

apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config

    if (error.response?.status === 401 && !originalRequest._retry) {
      if (isRefreshing) {
        return new Promise((resolve, reject) => {
          failedQueue.push({ resolve, reject })
        }).then((token) => {
          originalRequest.headers.Authorization = `Bearer ${token}`
          return apiClient(originalRequest)
        })
      }

      originalRequest._retry = true
      isRefreshing = true

      const refreshToken = tokenStore.getRefreshToken()
      if (!refreshToken) {
        tokenStore.clear()
        window.location.href = '/login'
        return Promise.reject(error)
      }

      try {
        const response = await axios.post('/api/v1/auth/refresh', {
          refresh_token: refreshToken,
        }, { timeout: 10000 })
        const newToken = response.data.access_token
        tokenStore.setAccessToken(newToken)
        processQueue(null, newToken)
        originalRequest.headers.Authorization = `Bearer ${newToken}`
        return apiClient(originalRequest)
      } catch (err) {
        processQueue(err, null)
        tokenStore.clear()
        window.location.href = '/login'
        return Promise.reject(err)
      } finally {
        isRefreshing = false
      }
    }

    return Promise.reject(error)
  }
)

export default apiClient
