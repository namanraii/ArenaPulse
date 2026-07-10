import type {
  NavigationResult,
  ChatResult,
  OpsAction,
  Zone,
  SustainabilityData,
  User,
  UserRole,
} from '../types'

const API_BASE = (import.meta.env.VITE_API_URL || '') + '/api/v1'
const TOKEN_KEY = 'arenapulse_token'
const USER_KEY = 'arenapulse_user'
const CACHE_KEY = 'arenapulse_offline_cache'

export interface AuthToken {
  access_token: string
  refresh_token: string
  token_type: string
}

export interface EfficiencyMetrics {
  cache_hits: number
  cache_misses: number
  flash_calls: number
  pro_calls: number
  cache_hit_rate_pct: number
  estimated_cost_usd: number
  estimated_tokens_saved: number
  routing_strategy: string
}

export interface AuditLogEntry {
  id: number
  user_id: number | null
  username: string | null
  action_type: string
  target_id: string | null
  details: Record<string, unknown>
  timestamp: string
}

function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY)
}

function authHeaders(): HeadersInit {
  const token = getToken()
  return token ? { Authorization: `Bearer ${token}` } : {}
}

function cacheOffline(key: string, data: unknown) {
  try {
    const cache = JSON.parse(localStorage.getItem(CACHE_KEY) || '{}')
    cache[key] = { data, ts: Date.now() }
    localStorage.setItem(CACHE_KEY, JSON.stringify(cache))
  } catch {
    // ignore storage errors
  }
}

function getOffline<T>(key: string, fallback: T): T {
  try {
    const cache = JSON.parse(localStorage.getItem(CACHE_KEY) || '{}')
    return cache[key]?.data ?? fallback
  } catch {
    return fallback
  }
}

const FETCH_TIMEOUT_MS = 10000;

async function fetchWithTimeout(url: string, options: RequestInit = {}): Promise<Response> {
  const controller = new AbortController();
  const id = setTimeout(() => controller.abort(), FETCH_TIMEOUT_MS);
  try {
    const response = await fetch(url, { ...options, signal: controller.signal });
    return response;
  } finally {
    clearTimeout(id);
  }
}

async function getJson<T>(url: string, fallback: T, auth = false): Promise<T> {
  try {
    const response = await fetchWithTimeout(url, {
      headers: auth ? authHeaders() : {},
    })
    if (response.ok) {
      const data = await response.json()
      return data
    }
  } catch {
    // fall through to offline cache
  }
  return getOffline(url, fallback)
}

async function postJson<T, F = T>(
  url: string,
  body: unknown,
  fallback: F,
  auth = false
): Promise<T | F> {
  try {
    const response = await fetchWithTimeout(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(auth ? authHeaders() : {}),
      },
      body: JSON.stringify(body),
    })
    if (response.ok) {
      return await response.json()
    }
  } catch {
    // ignore
  }
  return fallback
}

export const auth = {
  getUser(): User | null {
    try {
      const raw = localStorage.getItem(USER_KEY)
      return raw ? JSON.parse(raw) : null
    } catch {
      return null
    }
  },

  isLoggedIn(): boolean {
    return Boolean(getToken())
  },

  logout() {
    localStorage.removeItem(TOKEN_KEY)
    localStorage.removeItem(USER_KEY)
  },

  async login(username: string, password: string, role: UserRole): Promise<User | null> {
    try {
      const response = await fetchWithTimeout(`${API_BASE}/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password })
      })
      if (!response.ok) {
        throw new Error('Login failed');
      }
      const token: AuthToken = await response.json()
      localStorage.setItem(TOKEN_KEY, token.access_token)
      const user: User = {
        id: 0,
        username,
        email: `${username}@arenapulse.local`,
        role,
      }
      localStorage.setItem(USER_KEY, JSON.stringify(user))
      return user
    } catch {
      // Demo fallback when backend auth unavailable
      const demoUser: User = {
        id: 1,
        username: username || role,
        email: `${role}@demo.local`,
        role,
      }
      localStorage.setItem(TOKEN_KEY, 'demo-token')
      localStorage.setItem(USER_KEY, JSON.stringify(demoUser))
      return demoUser
    }
  },
}

export const api = {
  health: () =>
    getJson<{ status: string; mode: string }>(`${API_BASE}/healthz`, {
      status: 'unknown',
      mode: 'demo',
    }),

  zones: async () => {
    const zones = await getJson<Zone[]>(`${API_BASE}/demo/zones`, [])
    if (zones.length) cacheOffline('zones', zones)
    return zones.length ? zones : getOffline<Zone[]>('zones', [])
  },

  navigate: async (start: string, intent: string, stepFree: boolean, language: string) => {
    const result = await postJson<NavigationResult>(
      `${API_BASE}/demo/navigate`,
      { start_location: start, destination_intent: intent, step_free: stepFree, language },
      getOffline<NavigationResult>('last_route', {
        path: [],
        total_distance_m: 0,
        total_time_s: 0,
        step_free: stepFree,
        explanation: 'Unable to route.',
      })
    )
    cacheOffline('last_route', result)
    return result
  },

  chat: (message: string, language: string, sessionId?: string) =>
    postJson<ChatResult>(
      `${API_BASE}/demo/concierge/chat`,
      { message, language, session_id: sessionId || 'web' },
      {
        response: 'Service temporarily unavailable.',
        sources: [],
        detected_intent: 'general',
        language,
      }
    ),

  actions: () =>
    getJson<OpsAction[]>(`${API_BASE}/demo/ops/actions`, getOffline<OpsAction[]>('actions', [])),

  sustainability: async () => {
    const data = await getJson<SustainabilityData>(`${API_BASE}/sustainability/summary`, {
      transit_split: {},
      sustainability_score: 0,
      eco_tips: [],
    })
    cacheOffline('sustainability', data)
    return data
  },

  efficiency: () =>
    getJson<EfficiencyMetrics>(
      `${API_BASE}/ops/efficiency`,
      getOffline<EfficiencyMetrics>('efficiency', {
        cache_hits: 0,
        cache_misses: 0,
        flash_calls: 0,
        pro_calls: 0,
        cache_hit_rate_pct: 0,
        estimated_cost_usd: 0,
        estimated_tokens_saved: 0,
        routing_strategy: 'Flash for fan chat; Pro for ops reasoning',
      }),
      true
    ),

  auditLogs: () =>
    getJson<AuditLogEntry[]>(`${API_BASE}/ops/audit`, [], true),

  approveAction: (id: number) => {
    const token = getToken()
    const isDemo = token === 'demo-token'
    return postJson<OpsAction, null>(
      isDemo ? `${API_BASE}/demo/ops/actions/${id}/approve` : `${API_BASE}/ops/actions/${id}/approve`,
      {},
      null,
      !isDemo
    )
  },

  rejectAction: (id: number, reason: string) => {
    const token = getToken()
    const isDemo = token === 'demo-token'
    const url = isDemo
      ? `${API_BASE}/demo/ops/actions/${id}/reject`
      : `${API_BASE}/ops/actions/${id}/reject`
    return postJson<OpsAction, null>(url, { reason }, null, !isDemo)
  },
}
