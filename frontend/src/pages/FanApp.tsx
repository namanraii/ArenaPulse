import React, { useState, useEffect, useCallback } from 'react';
import {
  MapPin,
  Navigation,
  Route,
  Users,
  Leaf,
  AlertTriangle,
  ShieldCheck,
  Globe,
  ChevronRight,
  Footprints,
} from 'lucide-react';
import { AccessibilityToolbar } from '../components/AccessibilityToolbar';
import { ChatWidget } from '../components/ChatWidget';
import { useWebSocket } from '../hooks/useWebSocket';
import { api } from '../services/api';
import { LANGUAGES, getDensityClass } from '../utils/constants';
import type { NavigationResult, SustainabilityData, Zone } from '../types';

export function FanApp() {
  const [lang, setLang] = useState('es');
  const [a11y, setA11y] = useState({
    highContrast: false,
    largeText: false,
    reducedMotion: false,
    voiceEnabled: false,
  });
  const [startLoc, setStartLoc] = useState('Section_214');
  const [intent, setIntent] = useState('nearest_restroom');
  const [stepFree, setStepFree] = useState(true);
  const [route, setRoute] = useState<NavigationResult | null>(null);
  const [loadingRoute, setLoadingRoute] = useState(false);
  const [sustain, setSustain] = useState<SustainabilityData | null>(null);
  const [error, setError] = useState<string | null>(null);

  const ws = useWebSocket();

  useEffect(() => {
    document.title = 'Fan Guide | ArenaPulse';
    api.sustainability().then(setSustain);
  }, []);

  const toggleA11y = useCallback((key: string) => {
    setA11y((prev) => ({ ...prev, [key]: !prev[key as keyof typeof prev] }));
  }, []);

  const askRoute = useCallback(async () => {
    setLoadingRoute(true);
    setError(null);
    try {
      const result = await api.navigate(startLoc, intent, stepFree, lang);
      setRoute(result);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to generate route');
    } finally {
      setLoadingRoute(false);
    }
  }, [startLoc, intent, stepFree, lang]);

  const zones: Zone[] = ws.zones.length > 0 ? ws.zones : [];

  return (
    <div
      className={`fan-app ${a11y.largeText ? 'large-text' : ''} ${
        a11y.highContrast ? 'contrast' : ''
      } ${a11y.reducedMotion ? 'reduced-motion' : ''}`}
    >
      <header className="fan-header">
        <div>
          <p className="eyebrow">FIFA World Cup 2026 · AT&T Stadium</p>
          <h1>
            ArenaPulse <span className="text-accent">Fan Guide</span>
          </h1>
        </div>
        <div className="fan-header-actions">
          <select
            value={lang}
            onChange={(e) => setLang(e.target.value)}
            aria-label="Language"
          >
            {Object.entries(LANGUAGES).map(([code, name]) => (
              <option key={code} value={code}>
                {name}
              </option>
            ))}
          </select>
          {!ws.isConnected && (
            <span className="offline-pill" aria-live="polite">
              Offline cached data
            </span>
          )}
        </div>
      </header>

      <AccessibilityToolbar
        settings={a11y}
        onToggle={toggleA11y}
        offline={!ws.isConnected}
      />

      <main className="fan-main" id="main-content">
        <section className="panel" aria-labelledby="nav-title">
          <div className="panel-head">
            <div>
              <p className="eyebrow">Safe Navigation</p>
              <h2 id="nav-title">Find Your Way</h2>
            </div>
            <span className="metric">
              <Navigation size={18} /> Step-free
            </span>
          </div>
          <div className="fan-form">
            <label>
              <span>Your location</span>
              <select
                value={startLoc}
                onChange={(e) => setStartLoc(e.target.value)}
              >
                <option>Section_214</option>
                <option>Section_215</option>
                <option>Gate_A</option>
                <option>Gate_B</option>
                <option>Zone_1</option>
                <option>Zone_4</option>
              </select>
            </label>
            <label>
              <span>Destination</span>
              <select
                value={intent}
                onChange={(e) => setIntent(e.target.value)}
              >
                <option value="nearest_restroom">Nearest restroom</option>
                <option value="nearest_exit">Nearest exit</option>
                <option value="transit">Transit / Metro</option>
                <option value="medical">Medical point</option>
                <option value="Gate_D">Gate D</option>
              </select>
            </label>
            <label className="checkbox">
              <input
                type="checkbox"
                checked={stepFree}
                onChange={(e) => setStepFree(e.target.checked)}
              />
              Step-free route
            </label>
            <button onClick={askRoute} disabled={loadingRoute}>
              <Route size={18} />{' '}
              {loadingRoute ? 'Generating...' : 'Generate Route'}
            </button>
          </div>
          {loadingRoute && (
            <div className="route-result" aria-live="polite">
              <p className="muted center">Generating accessible route...</p>
            </div>
          )}
          {error && (
            <div className="route-result" aria-live="polite">
              <p className="text-red-500 center">{error}</p>
            </div>
          )}
          {route && !loadingRoute && !error && (
            <div className="route-result" aria-live="polite">
              <h4>
                <Footprints size={16} /> {route.total_distance_m}m ·{' '}
                {Math.ceil(route.total_time_s / 60)} min
              </h4>
              <p>{route.explanation}</p>
              {route.avoid_reason && (
                <span className="avoid-chip">
                  <AlertTriangle size={12} /> {route.avoid_reason}
                </span>
              )}
              <div className="path-list">
                {route.path.map((node, i) => (
                  <span key={i} className="path-node">
                    {node.name.replace('_', ' ')}
                    {i < route.path.length - 1 && <ChevronRight size={14} />}
                  </span>
                ))}
              </div>
            </div>
          )}
        </section>

        <section className="panel" aria-labelledby="crowd-title">
          <div className="panel-head">
            <div>
              <p className="eyebrow">Live Crowd Status</p>
              <h2 id="crowd-title">Zone Densities</h2>
            </div>
            <span className="metric">
              <Users size={18} /> Live
            </span>
          </div>
          <div className="zone-list">
            {zones.length === 0 && (
              <p className="muted">Connecting to live feed...</p>
            )}
            {zones.map((z) => (
              <div
                key={z.name}
                className={`zone-row ${getDensityClass(z.density)}`}
              >
                <strong>{z.name.replace('_', ' ')}</strong>
                <span>{Math.round(z.density * 100)}% full</span>
                {z.density > 0.85 && (
                  <span
                    className="alert-badge"
                    aria-label="High density warning"
                  >
                    <AlertTriangle size={12} /> Congested
                  </span>
                )}
              </div>
            ))}
          </div>
        </section>

        <section className="panel" aria-labelledby="eco-title">
          <div className="panel-head">
            <div>
              <p className="eyebrow">Sustainability</p>
              <h2 id="eco-title">Eco Impact</h2>
            </div>
            <span className="metric">
              <Leaf size={18} /> Score: {sustain?.sustainability_score ?? '--'}
            </span>
          </div>
          {sustain && (
            <div className="eco-content">
              <div className="eco-tips">
                {sustain.eco_tips.map((tip, i) => (
                  <p key={i} className="eco-tip">
                    <Leaf size={14} /> {tip}
                  </p>
                ))}
              </div>
              <div className="transit-bars">
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
            </div>
          )}
        </section>
      </main>

      <ChatWidget language={lang} voiceEnabled={a11y.voiceEnabled} />

      <footer className="fan-footer">
        <p>
          <ShieldCheck size={14} /> ArenaPulse uses deterministic routing and
          retrieval-grounded AI. <a href="/ops">Staff Login</a>
        </p>
      </footer>
    </div>
  );
}
