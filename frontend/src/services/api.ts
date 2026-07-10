import type {
  NavigationResult,
  ChatResult,
  OpsAction,
  Zone,
  SustainabilityData,
  User,
  UserRole,
  CrowdAlert,
  TransitRecommendation,
} from '../types';
import { decodeJwtPayload } from '../utils/jwt';

const API_BASE = (import.meta.env.VITE_API_URL || '') + '/api/v1';
const TOKEN_KEY = 'arenapulse_token';
const USER_KEY = 'arenapulse_user';
const CACHE_KEY = 'arenapulse_offline_cache';

export interface AuthToken {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface EfficiencyMetrics {
  cache_hits: number;
  cache_misses: number;
  flash_calls: number;
  pro_calls: number;
  cache_hit_rate_pct: number;
  estimated_cost_usd: number;
  estimated_tokens_saved: number;
  routing_strategy: string;
}

export interface AuditLogEntry {
  id: number;
  user_id: number | null;
  username: string | null;
  action_type: string;
  target_id: string | null;
  details: Record<string, unknown>;
  timestamp: string;
}

export interface DensityHistoryPoint {
  time: string;
  density: number;
}

function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

function hasRealToken(): boolean {
  const token = getToken();
  return Boolean(token && token !== 'demo-token');
}

function authHeaders(): HeadersInit {
  const token = getToken();
  return token && token !== 'demo-token'
    ? { Authorization: `Bearer ${token}` }
    : {};
}

function cacheOffline(key: string, data: unknown) {
  try {
    const cache = JSON.parse(localStorage.getItem(CACHE_KEY) || '{}');
    cache[key] = { data, ts: Date.now() };
    localStorage.setItem(CACHE_KEY, JSON.stringify(cache));
  } catch {
    // ignore storage errors
  }
}

function getOffline<T>(key: string, fallback: T): T {
  try {
    const cache = JSON.parse(localStorage.getItem(CACHE_KEY) || '{}');
    return cache[key]?.data ?? fallback;
  } catch {
    return fallback;
  }
}

const FETCH_TIMEOUT_MS = 10000;

async function fetchWithTimeout(
  url: string,
  options: RequestInit = {}
): Promise<Response> {
  const controller = new AbortController();
  const id = setTimeout(() => controller.abort(), FETCH_TIMEOUT_MS);
  try {
    return await fetch(url, { ...options, signal: controller.signal });
  } finally {
    clearTimeout(id);
  }
}

async function getJson<T>(url: string, fallback: T, auth = false): Promise<T> {
  try {
    const response = await fetchWithTimeout(url, {
      headers: auth ? authHeaders() : {},
    });
    if (response.ok) {
      return await response.json();
    }
  } catch {
    // fall through to offline cache
  }
  return getOffline(url, fallback);
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
    });
    if (response.ok) {
      return await response.json();
    }
  } catch {
    // ignore
  }
  return fallback;
}

function userFromToken(token: string, username: string): User | null {
  const payload = decodeJwtPayload(token);
  if (!payload?.role) return null;
  return {
    id: Number(payload.sub) || 0,
    username: payload.username || username,
    email: `${payload.username || username}@arenapulse.local`,
    role: payload.role,
  };
}

export const auth = {
  getUser(): User | null {
    try {
      const raw = localStorage.getItem(USER_KEY);
      return raw ? JSON.parse(raw) : null;
    } catch {
      return null;
    }
  },

  isLoggedIn(): boolean {
    return Boolean(getToken());
  },

  logout() {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
  },

  async login(username: string, password: string): Promise<User | null> {
    try {
      const response = await fetchWithTimeout(`${API_BASE}/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password }),
      });
      if (response.ok) {
        const token: AuthToken = await response.json();
        localStorage.setItem(TOKEN_KEY, token.access_token);
        localStorage.setItem('arenapulse_refresh', token.refresh_token);
        const user = userFromToken(token.access_token, username);
        if (user) {
          localStorage.setItem(USER_KEY, JSON.stringify(user));
          return user;
        }
      }
    } catch {
      // network/fetch failure, fall through to demo check
    }

    // Fallback to local demo login if API is offline/unavailable or returns error
    const lowerUser = username.trim().toLowerCase();
    if (
      password === 'password' &&
      ['organizer', 'volunteer', 'fan'].includes(lowerUser)
    ) {
      const demoUser: User = {
        id: 1,
        username: lowerUser,
        email: `${lowerUser}@demo.local`,
        role: lowerUser as UserRole,
      };
      localStorage.setItem(TOKEN_KEY, 'demo-token');
      localStorage.setItem(USER_KEY, JSON.stringify(demoUser));
      return demoUser;
    }
    return null;
  },

  async refresh(): Promise<boolean> {
    const refreshToken = localStorage.getItem('arenapulse_refresh');
    if (!refreshToken) return false;
    try {
      const response = await fetchWithTimeout(`${API_BASE}/auth/refresh`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh_token: refreshToken }),
      });
      if (!response.ok) return false;
      const token: AuthToken = await response.json();
      localStorage.setItem(TOKEN_KEY, token.access_token);
      localStorage.setItem('arenapulse_refresh', token.refresh_token);
      const user = auth.getUser();
      if (user) {
        const updated = userFromToken(token.access_token, user.username);
        if (updated) localStorage.setItem(USER_KEY, JSON.stringify(updated));
      }
      return true;
    } catch {
      return false;
    }
  },
};

export const api = {
  health: () =>
    getJson<{ status: string; mode: string }>(`${API_BASE}/healthz`, {
      status: 'unknown',
      mode: 'demo',
    }),

  zones: async () => {
    const zones = await getJson<Zone[]>(`${API_BASE}/demo/zones`, []);
    if (zones.length) cacheOffline('zones', zones);
    return zones.length ? zones : getOffline<Zone[]>('zones', []);
  },

  navigate: async (
    start: string,
    intent: string,
    stepFree: boolean,
    language: string
  ) => {
    const body = {
      start_location: start,
      destination_intent: intent,
      step_free: stepFree,
      language,
    };
    const fallback = getOffline<NavigationResult>('last_route', {
      path: [],
      total_distance_m: 0,
      total_time_s: 0,
      step_free: stepFree,
      explanation: 'Unable to route.',
    });
    const result = await postJson<NavigationResult>(
      `${API_BASE}/navigate`,
      body,
      null as unknown as NavigationResult
    );
    if (result) {
      cacheOffline('last_route', result);
      return result;
    }
    const demo = await postJson<NavigationResult>(
      `${API_BASE}/demo/navigate`,
      body,
      fallback
    );
    cacheOffline('last_route', demo);
    return demo;
  },

  chat: async (message: string, language: string, sessionId?: string) => {
    const body = { message, language, session_id: sessionId || 'web' };
    const fallback: ChatResult = {
      response: 'Service temporarily unavailable.',
      sources: [],
      detected_intent: 'general',
      language,
    };
    const result = await postJson<ChatResult>(
      `${API_BASE}/concierge/chat`,
      body,
      null as unknown as ChatResult
    );
    if (result) return result;
    return postJson<ChatResult>(
      `${API_BASE}/demo/concierge/chat`,
      body,
      fallback
    );
  },

  actions: () => {
    if (hasRealToken()) {
      return getJson<OpsAction[]>(`${API_BASE}/ops/actions`, [], true);
    }
    return getJson<OpsAction[]>(
      `${API_BASE}/demo/ops/actions`,
      getOffline<OpsAction[]>('actions', [])
    );
  },

  alerts: () => {
    if (hasRealToken()) {
      return getJson<CrowdAlert[]>(`${API_BASE}/ops/alerts`, [], true);
    }
    return Promise.resolve([] as CrowdAlert[]);
  },

  sustainability: async () => {
    const data = await getJson<SustainabilityData>(
      `${API_BASE}/sustainability/summary`,
      {
        transit_split: {},
        sustainability_score: 0,
        eco_tips: [],
      }
    );
    cacheOffline('sustainability', data);
    return data;
  },

  wasteBins: () =>
    getJson<{ bins: Record<string, number>; water_refill_usage: number }>(
      `${API_BASE}/sustainability/waste-bins`,
      { bins: {}, water_refill_usage: 0 }
    ),

  transit: (gate: string, destination = 'downtown', language = 'en') =>
    getJson<TransitRecommendation>(
      `${API_BASE}/sustainability/transit?gate=${encodeURIComponent(gate)}&destination=${encodeURIComponent(destination)}&language=${encodeURIComponent(language)}`,
      {
        best_mode: 'metro',
        best_wait_min: 5,
        co2_saved_kg: 0.65,
        nudge: 'Take public transit to reduce CO₂.',
        alternatives: [],
      }
    ),

  densityHistory: () =>
    getJson<DensityHistoryPoint[]>(`${API_BASE}/demo/density-history`, []),

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

  auditLogs: () => getJson<AuditLogEntry[]>(`${API_BASE}/ops/audit`, [], true),

  approveAction: (id: number) => {
    const url = hasRealToken()
      ? `${API_BASE}/ops/actions/${id}/approve`
      : `${API_BASE}/demo/ops/actions/${id}/approve`;
    return postJson<OpsAction, null>(url, {}, null, hasRealToken());
  },

  rejectAction: (id: number, reason: string) => {
    const url = hasRealToken()
      ? `${API_BASE}/ops/actions/${id}/reject`
      : `${API_BASE}/demo/ops/actions/${id}/reject`;
    return postJson<OpsAction, null>(url, { reason }, null, hasRealToken());
  },
};
