import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Activity,
  AlertTriangle,
  Check,
  X,
  ShieldCheck,
  Clock,
  Users,
  Leaf,
  LogOut,
  FileText,
  WifiOff,
  Zap,
  Megaphone,
} from 'lucide-react';
import { LiveStadiumMap } from '../components/LiveStadiumMap';
import { DashboardCharts } from '../components/DashboardCharts';
import { useWebSocket } from '../hooks/useWebSocket';
import {
  api,
  auth,
  type AuditLogEntry,
  type EfficiencyMetrics,
} from '../services/api';
import type { OpsAction, Zone, SustainabilityData } from '../types';
import { getDensityClass } from '../utils/constants';

const PRIORITY_ORDER = { critical: 0, high: 1, medium: 2, low: 3 };

export function OpsDashboard() {
  const navigate = useNavigate();
  const user = auth.getUser();
  const isVolunteer = user?.role === 'volunteer';
  const isOrganizer = user?.role === 'organizer';

  const [actions, setActions] = useState<OpsAction[]>([]);
  const [sustain, setSustain] = useState<SustainabilityData | null>(null);
  const [efficiency, setEfficiency] = useState<EfficiencyMetrics | null>(null);
  const [tab, setTab] = useState<
    'overview' | 'actions' | 'sustainability' | 'audit' | 'efficiency'
  >('overview');
  const [auditLogs, setAuditLogs] = useState<AuditLogEntry[]>([]);
  const [error, setError] = useState<string | null>(null);

  const ws = useWebSocket();

  useEffect(() => {
    document.title = 'Ops Dashboard | ArenaPulse';
    if (!auth.isLoggedIn()) {
      navigate('/login');
    }
  }, [navigate]);

  const loadData = useCallback(async () => {
    try {
      setError(null);
      const [a, s, e, logs] = await Promise.all([
        api.actions(),
        api.sustainability(),
        api.efficiency(),
        api.auditLogs(),
      ]);
      setActions(a);
      setSustain(s);
      setEfficiency(e);
      setAuditLogs(logs);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to load data');
    }
  }, []);

  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 10000);
    return () => clearInterval(interval);
  }, []);

  const approve = useCallback(
    async (id: number) => {
      if (!isOrganizer) return;
      try {
        setError(null);
        await api.approveAction(id);
        loadData();
      } catch (err: unknown) {
        setError(
          err instanceof Error ? err.message : 'Failed to approve action'
        );
      }
    },
    [isOrganizer, loadData]
  );

  const reject = useCallback(
    async (id: number) => {
      if (!isOrganizer) return;
      try {
        setError(null);
        await api.rejectAction(id, 'Overridden by control room');
        loadData();
      } catch (err: unknown) {
        setError(
          err instanceof Error ? err.message : 'Failed to reject action'
        );
      }
    },
    [isOrganizer, loadData]
  );

  const logout = useCallback(() => {
    auth.logout();
    navigate('/login');
  }, [navigate]);

  const zones: Zone[] = ws.zones.length > 0 ? ws.zones : [];

  const pending = useMemo(
    () => actions.filter((a) => a.status === 'pending'),
    [actions]
  );
  const sorted = useMemo(
    () =>
      [...pending].sort(
        (a, b) => PRIORITY_ORDER[a.priority] - PRIORITY_ORDER[b.priority]
      ),
    [pending]
  );

  return (
    <div className="ops-app">
      <header className="ops-header">
        <div>
          <p className="eyebrow">FIFA World Cup 2026 · Control Room</p>
          <h1>
            Ops <span className="text-accent">Dashboard</span>
          </h1>
        </div>
        <div className="ops-header-meta">
          {user && (
            <span
              className="role-badge"
              aria-label={`Signed in as ${user.role}`}
            >
              {user.username} · {user.role}
            </span>
          )}
          {!ws.isConnected && (
            <span className="offline-pill" aria-live="polite">
              <WifiOff size={14} /> Live feed offline
            </span>
          )}
          <nav className="ops-tabs" aria-label="Dashboard sections">
            {(
              [
                'overview',
                'actions',
                'sustainability',
                'efficiency',
                'audit',
              ] as const
            )
              .filter(
                (t) => !(isVolunteer && (t === 'audit' || t === 'efficiency'))
              )
              .map((t) => (
                <button
                  key={t}
                  className={tab === t ? 'active' : ''}
                  onClick={() => setTab(t)}
                  aria-current={tab === t ? 'page' : undefined}
                >
                  {t === 'overview' && <Activity size={16} />}
                  {t === 'actions' && <AlertTriangle size={16} />}
                  {t === 'sustainability' && <Leaf size={16} />}
                  {t === 'efficiency' && <Zap size={16} />}
                  {t === 'audit' && <FileText size={16} />}
                  {t.charAt(0).toUpperCase() + t.slice(1)}
                </button>
              ))}
          </nav>
          <button className="btn-ghost" onClick={logout}>
            <LogOut size={16} /> Exit
          </button>
        </div>
      </header>

      {error && (
        <div
          className="bg-red-900 text-white p-3 text-center"
          role="alert"
          aria-live="assertive"
        >
          {error}
        </div>
      )}

      <main className="ops-main" id="main-content">
        {isVolunteer && tab === 'overview' && sorted.length > 0 && (
          <section
            className="panel volunteer-banner"
            aria-labelledby="volunteer-title"
          >
            <div className="panel-head">
              <div>
                <p className="eyebrow">Your Assignment</p>
                <h2 id="volunteer-title">Steward Instructions</h2>
              </div>
              <span className="metric">
                <Megaphone size={16} /> Plain language
              </span>
            </div>
            <article className={`action ${sorted[0].priority}`}>
              <h3>{sorted[0].title}</h3>
              <p className="volunteer-instruction">{sorted[0].description}</p>
              <p className="reason">{sorted[0].reasoning}</p>
            </article>
          </section>
        )}

        {tab === 'overview' && (
          <>
            <section
              className="panel heatmap-panel"
              aria-labelledby="heatmap-title"
            >
              <div className="panel-head">
                <div>
                  <p className="eyebrow">Live Crowd Graph</p>
                  <h2 id="heatmap-title">Stadium Heatmap</h2>
                </div>
                <span className="metric" aria-live="polite">
                  <ShieldCheck size={16} /> Auto-alerting
                </span>
              </div>
              <div
                className="stadium-map"
                role="img"
                aria-label="Stadium zone density map"
              >
                {zones.length === 0 && (
                  <p className="muted center">Loading live zone data...</p>
                )}
                {zones.map((z, i) => (
                  <button
                    key={z.name}
                    className={`zone zone-${i + 1} ${getDensityClass(z.density)}`}
                    aria-label={`${z.name} density ${Math.round(z.density * 100)} percent`}
                  >
                    <strong>{z.name.replace('_', ' ')}</strong>
                    <span>{z.label || 'Zone'}</span>
                    <b>{Math.round(z.density * 100)}%</b>
                  </button>
                ))}
                <div className="pitch">MATCH BOWL</div>
              </div>
            </section>

            <section className="panel" aria-labelledby="actions-title">
              <div className="panel-head">
                <div>
                  <p className="eyebrow">OpsCommander</p>
                  <h2 id="actions-title">Top Priority Actions</h2>
                </div>
                <span className="metric" aria-live="polite">
                  <AlertTriangle size={16} /> {sorted.length} pending
                </span>
              </div>
              <div className="action-list compact">
                {sorted.slice(0, 3).map((action) => (
                  <article
                    key={action.id}
                    className={`action ${action.priority}`}
                  >
                    <span className="priority">{action.priority}</span>
                    <h3>{action.title}</h3>
                    <p>{action.description}</p>
                    <p className="reason">{action.reasoning}</p>
                    <div className="action-meta">
                      <span>
                        <Users size={14} />{' '}
                        {action.affected_population.toLocaleString()} fans
                      </span>
                      <span>
                        <Clock size={14} /> {action.time_to_impact_min ?? 'N/A'}{' '}
                        min
                      </span>
                    </div>
                  </article>
                ))}
                {sorted.length === 0 && (
                  <p className="muted">No pending actions.</p>
                )}
              </div>
            </section>

            <section
              className="panel heatmap-panel"
              aria-labelledby="live-map-title"
              style={{ gridColumn: '1 / -1' }}
            >
              <div className="panel-head">
                <div>
                  <p className="eyebrow">Geographic Data</p>
                  <h2 id="live-map-title">Live Geographic Map</h2>
                </div>
              </div>
              <div
                className="stadium-map-container"
                role="img"
                aria-label="Geographic zone density map"
                style={{ padding: '1rem' }}
              >
                {zones.length === 0 && (
                  <p className="muted center">Loading live zone data...</p>
                )}
                {zones.length > 0 && <LiveStadiumMap zones={zones} />}
              </div>
            </section>

            <div style={{ gridColumn: '1 / -1' }}>
              <DashboardCharts zones={zones} />
            </div>
          </>
        )}

        {tab === 'actions' && (
          <section
            className="panel"
            aria-labelledby="all-actions-title"
            style={{ gridColumn: '1 / -1' }}
          >
            <div className="panel-head">
              <div>
                <p className="eyebrow">Human-in-the-loop</p>
                <h2 id="all-actions-title">Action Queue</h2>
              </div>
            </div>
            <div className="action-list">
              {sorted.map((action) => (
                <article
                  key={action.id}
                  className={`action ${action.priority}`}
                >
                  <div className="action-header">
                    <span className={`priority-badge ${action.priority}`}>
                      {action.priority}
                    </span>
                    <h3>{action.title}</h3>
                  </div>
                  <p>{action.description}</p>
                  <div className="reason-box">
                    <strong>Reasoning:</strong> {action.reasoning}
                  </div>
                  <div className="action-meta">
                    <span>
                      <Users size={14} />{' '}
                      {action.affected_population.toLocaleString()} fans
                    </span>
                    <span>
                      <Clock size={14} /> {action.time_to_impact_min ?? 'N/A'}{' '}
                      min impact
                    </span>
                    <span>By {action.recommended_by}</span>
                  </div>
                  <div className="action-buttons">
                    {isOrganizer ? (
                      <>
                        <button
                          className="btn-success"
                          onClick={() => approve(action.id)}
                        >
                          <Check size={16} /> Approve
                        </button>
                        <button
                          className="btn-danger"
                          onClick={() => reject(action.id)}
                        >
                          <X size={16} /> Reject
                        </button>
                      </>
                    ) : (
                      <p className="muted">
                        Volunteer view — read-only. Contact organizer to
                        approve.
                      </p>
                    )}
                  </div>
                </article>
              ))}
              {sorted.length === 0 && (
                <p className="muted">All clear — no pending actions.</p>
              )}
            </div>
          </section>
        )}

        {tab === 'sustainability' && sustain && (
          <section
            className="panel"
            aria-labelledby="sustain-title"
            style={{ gridColumn: '1 / -1' }}
          >
            <div className="panel-head">
              <div>
                <p className="eyebrow">Green Operations</p>
                <h2 id="sustain-title">Sustainability</h2>
              </div>
              <span className="metric">
                <Leaf size={16} /> Score {sustain.sustainability_score}/100
              </span>
            </div>
            <div className="sustain-grid">
              <div className="sustain-card">
                <h4>Transit Split</h4>
                {Object.entries(sustain.transit_split).map(([mode, pct]) => (
                  <div key={mode} className="transit-bar">
                    <span>{mode}</span>
                    <div className="bar-track">
                      <div
                        className="bar-fill"
                        style={{ width: `${Math.round(pct * 100)}%` }}
                      />
                    </div>
                    <span>{Math.round(pct * 100)}%</span>
                  </div>
                ))}
              </div>
              <div className="sustain-card">
                <h4>Eco Tips</h4>
                {sustain.eco_tips.map((tip, i) => (
                  <p key={i} className="eco-tip">
                    <Leaf size={14} /> {tip}
                  </p>
                ))}
              </div>
              <div className="sustain-card">
                <h4>CO₂ Estimate</h4>
                <p className="big-number">
                  {sustain.estimated_co2_kg_per_1000_fans ??
                    sustain.estimated_co2_kg ??
                    '--'}{' '}
                  kg
                </p>
                <p className="muted">per 1,000 fans</p>
              </div>
            </div>
          </section>
        )}

        {tab === 'efficiency' && efficiency && (
          <section
            className="panel"
            aria-labelledby="eff-title"
            style={{ gridColumn: '1 / -1' }}
          >
            <div className="panel-head">
              <div>
                <p className="eyebrow">Responsible AI</p>
                <h2 id="eff-title">LLM Efficiency</h2>
              </div>
              <span className="metric">
                <Zap size={16} /> {efficiency.cache_hit_rate_pct}% cache hit
              </span>
            </div>
            <div className="efficiency-grid">
              <div className="sustain-card">
                <h4>Model Routing</h4>
                <p>{efficiency.routing_strategy}</p>
              </div>
              <div className="sustain-card">
                <h4>Cache Performance</h4>
                <p className="big-number">{efficiency.cache_hit_rate_pct}%</p>
                <p className="muted">
                  {efficiency.cache_hits} hits · {efficiency.cache_misses}{' '}
                  misses
                </p>
              </div>
              <div className="sustain-card">
                <h4>Calls</h4>
                <p>Flash: {efficiency.flash_calls}</p>
                <p>Pro: {efficiency.pro_calls}</p>
              </div>
              <div className="sustain-card">
                <h4>Est. Cost</h4>
                <p className="big-number">${efficiency.estimated_cost_usd}</p>
                <p className="muted">
                  {efficiency.estimated_tokens_saved} tokens saved via cache
                </p>
              </div>
            </div>
          </section>
        )}

        {tab === 'audit' && (
          <section
            className="panel"
            aria-labelledby="audit-title"
            style={{ gridColumn: '1 / -1' }}
          >
            <div className="panel-head">
              <div>
                <p className="eyebrow">Accountability</p>
                <h2 id="audit-title">Audit Log</h2>
              </div>
            </div>
            <table className="audit-table">
              <thead>
                <tr>
                  <th>Time</th>
                  <th>User</th>
                  <th>Action</th>
                  <th>Target</th>
                  <th>Details</th>
                </tr>
              </thead>
              <tbody>
                {auditLogs.length === 0 && (
                  <tr>
                    <td colSpan={5} className="muted center">
                      No audit entries yet. Approve or reject an action to
                      populate the log.
                    </td>
                  </tr>
                )}
                {auditLogs.map((log) => (
                  <tr key={log.id}>
                    <td>{new Date(log.timestamp).toLocaleString()}</td>
                    <td>{log.username || 'system'}</td>
                    <td>{log.action_type}</td>
                    <td>{log.target_id || '—'}</td>
                    <td>{JSON.stringify(log.details)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </section>
        )}
      </main>
    </div>
  );
}
