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

const defaultZones: Zone[] = [
  { name: 'Zone_1', density: 0.85, label: 'North Plaza', capacity: 12000 },
  { name: 'Zone_2', density: 0.72, label: 'East Concourse', capacity: 11500 },
  { name: 'Zone_3', density: 0.92, label: 'South Ramp', capacity: 11800 },
  { name: 'Zone_4', density: 0.54, label: 'West Gate Queue', capacity: 12200 },
  { name: 'Zone_5', density: 0.88, label: 'Transit Bridge', capacity: 11000 },
  {
    name: 'Zone_6',
    density: 0.45,
    label: 'Accessible Services',
    capacity: 11300,
  },
  { name: 'Zone_7', density: 0.61, label: 'Club Level', capacity: 11600 },
  {
    name: 'Zone_8',
    density: 0.95,
    label: 'South Exit Corridor',
    capacity: 11567,
  },
];

const defaultActions: OpsAction[] = [
  {
    id: 101,
    title: 'Divert North Plaza Entry to East Gate',
    description:
      'Zone 1 has reached 100% capacity. Redirect incoming fans to Gate B.',
    reasoning:
      'Critical bottleneck detected at Gate A entry path. Diverting flow prevents crowd crushing.',
    priority: 'critical',
    status: 'pending',
    recommended_by: 'sentinel',
    affected_zones: ['Zone_1', 'Zone_2'],
    affected_population: 4500,
    time_to_impact_min: 5,
    created_at: new Date().toISOString(),
  },
  {
    id: 102,
    title: 'Open South Ramp Exit Gates',
    description:
      'South Ramp (Zone 3) density has exceeded 90%. Open overflow gates.',
    reasoning:
      'Rapid accumulation of post-match crowd is creating a static congestion wave.',
    priority: 'high',
    status: 'pending',
    recommended_by: 'sentinel',
    affected_zones: ['Zone_3'],
    affected_population: 3200,
    time_to_impact_min: 12,
    created_at: new Date(Date.now() - 120000).toISOString(),
  },
];

const defaultAuditLogs: AuditLogEntry[] = [
  {
    id: 1,
    user_id: 1,
    username: 'organizer',
    action_type: 'ops_action_approved',
    target_id: '101',
    details: { title: 'Divert North Plaza Entry to East Gate' },
    timestamp: new Date(Date.now() - 60000).toISOString(),
  },
];

export const api = {
  health: () =>
    getJson<{ status: string; mode: string }>(`${API_BASE}/healthz`, {
      status: 'unknown',
      mode: 'demo',
    }),

  zones: async () => {
    const zones = await getJson<Zone[]>(`${API_BASE}/demo/zones`, []);
    if (zones.length) cacheOffline('zones', zones);
    const cached = getOffline<Zone[]>('zones', []);
    return cached.length ? cached : defaultZones;
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

  actions: async () => {
    let list: OpsAction[] = [];
    if (hasRealToken()) {
      list = await getJson<OpsAction[]>(`${API_BASE}/ops/actions`, [], true);
    } else {
      list = await getJson<OpsAction[]>(`${API_BASE}/demo/ops/actions`, []);
    }
    if (list.length) {
      cacheOffline('actions', list);
      return list;
    }
    return getOffline<OpsAction[]>('actions', defaultActions);
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
        transit_split: {
          metro: 0.35,
          bus: 0.2,
          rideshare: 0.25,
          walk: 0.15,
          shuttle: 0.05,
        },
        estimated_co2_kg: 450.2,
        sustainability_score: 72,
        eco_tips: [
          'Promote Gate D rail shuttle while rideshare queues are saturated.',
          'Send refill-station reminders to sections with high bottled-water purchases.',
          'Dispatch waste volunteers to bins above 80% before the final whistle surge.',
        ],
        waste_bin_fill_pct: { Bin_A: 0.4, Bin_B: 0.75, Bin_C: 0.2 },
        water_refill_usage: 1200,
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
    getJson<DensityHistoryPoint[]>(`${API_BASE}/demo/density-history`, [
      { time: '20:00', density: 0.45 },
      { time: '20:10', density: 0.55 },
      { time: '20:20', density: 0.72 },
      { time: '20:30', density: 0.85 },
      { time: '20:40', density: 0.9 },
      { time: '20:50', density: 0.88 },
    ]),

  efficiency: () =>
    getJson<EfficiencyMetrics>(
      `${API_BASE}/ops/efficiency`,
      getOffline<EfficiencyMetrics>('efficiency', {
        cache_hits: 154,
        cache_misses: 82,
        flash_calls: 198,
        pro_calls: 38,
        cache_hit_rate_pct: 65.2,
        estimated_cost_usd: 1.14,
        estimated_tokens_saved: 77000,
        routing_strategy: 'cost_optimized',
      }),
      true
    ),

  auditLogs: async () => {
    let logs: AuditLogEntry[] = [];
    if (hasRealToken()) {
      logs = await getJson<AuditLogEntry[]>(`${API_BASE}/ops/audit`, [], true);
    }
    if (logs.length) {
      cacheOffline('audit_logs', logs);
      return logs;
    }
    return getOffline<AuditLogEntry[]>('audit_logs', defaultAuditLogs);
  },

  approveAction: async (id: number) => {
    const url = hasRealToken()
      ? `${API_BASE}/ops/actions/${id}/approve`
      : `${API_BASE}/demo/ops/actions/${id}/approve`;
    const res = await postJson<OpsAction, null>(url, {}, null, hasRealToken());

    const list = getOffline<OpsAction[]>('actions', defaultActions);
    const updated = list.map((a) =>
      a.id === id ? { ...a, status: 'approved' as const } : a
    );
    cacheOffline('actions', updated);

    const user = auth.getUser();
    const logs = getOffline<AuditLogEntry[]>('audit_logs', defaultAuditLogs);
    const newLog: AuditLogEntry = {
      id: Date.now(),
      user_id: user?.id || 1,
      username: user?.username || 'organizer',
      action_type: 'ops_action_approved',
      target_id: String(id),
      details: { title: list.find((a) => a.id === id)?.title || 'Action' },
      timestamp: new Date().toISOString(),
    };
    cacheOffline('audit_logs', [newLog, ...logs]);

    return res;
  },

  rejectAction: async (id: number, reason: string) => {
    const url = hasRealToken()
      ? `${API_BASE}/ops/actions/${id}/reject`
      : `${API_BASE}/demo/ops/actions/${id}/reject`;
    const res = await postJson<OpsAction, null>(
      url,
      { reason },
      null,
      hasRealToken()
    );

    const list = getOffline<OpsAction[]>('actions', defaultActions);
    const updated = list.map((a) =>
      a.id === id ? { ...a, status: 'rejected' as const } : a
    );
    cacheOffline('actions', updated);

    const user = auth.getUser();
    const logs = getOffline<AuditLogEntry[]>('audit_logs', defaultAuditLogs);
    const newLog: AuditLogEntry = {
      id: Date.now(),
      user_id: user?.id || 1,
      username: user?.username || 'organizer',
      action_type: 'ops_action_rejected',
      target_id: String(id),
      details: {
        title: list.find((a) => a.id === id)?.title || 'Action',
        reason,
      },
      timestamp: new Date().toISOString(),
    };
    cacheOffline('audit_logs', [newLog, ...logs]);

    return res;
  },
};
