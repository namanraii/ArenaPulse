import { useState, useEffect, useRef, useCallback } from 'react';
import type { Zone } from '../types';
import { api } from '../services/api';

interface WsState {
  zones: Zone[];
  isConnected: boolean;
  error: string | null;
}

const defaultWsUrl = import.meta.env.VITE_WS_URL
  ? `${import.meta.env.VITE_WS_URL}/api/v1/ws/crowd-feed`
  : `${window.location.protocol === 'https:' ? 'wss' : 'ws'}://${window.location.hostname}:8000/api/v1/ws/crowd-feed`;

export function useWebSocket(url: string = defaultWsUrl) {
  const [state, setState] = useState<WsState>({
    zones: [],
    isConnected: false,
    error: null,
  });
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(
    null
  );
  const pollIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const reconnectAttempts = useRef(0);
  const maxReconnect = 10;
  const connectRef = useRef<() => void>();

  const loadFallbackZones = useCallback(async () => {
    const zones = await api.zones();
    if (zones.length) {
      setState((s) => ({ ...s, zones }));
    }
  }, []);

  const connect = useCallback(() => {
    try {
      const ws = new WebSocket(url);
      wsRef.current = ws;

      ws.onopen = () => {
        reconnectAttempts.current = 0;
        if (pollIntervalRef.current) {
          clearInterval(pollIntervalRef.current);
          pollIntervalRef.current = null;
        }
        setState((s) => ({ ...s, isConnected: true, error: null }));
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.type === 'crowd_update' && Array.isArray(data.zones)) {
            setState((s) => ({ ...s, zones: data.zones }));
          }
        } catch {
          // ignore malformed messages
        }
      };

      ws.onclose = () => {
        setState((s) => ({ ...s, isConnected: false }));
        wsRef.current = null;
        loadFallbackZones();
        if (!pollIntervalRef.current) {
          pollIntervalRef.current = setInterval(loadFallbackZones, 5000);
        }
        if (reconnectAttempts.current < maxReconnect) {
          const delay = Math.min(1000 * 2 ** reconnectAttempts.current, 30000);
          reconnectTimeoutRef.current = setTimeout(() => {
            reconnectAttempts.current += 1;
            connectRef.current?.();
          }, delay);
        }
      };

      ws.onerror = () => {
        setState((s) => ({ ...s, error: 'WebSocket error' }));
      };
    } catch {
      setState((s) => ({ ...s, error: 'Failed to connect' }));
      loadFallbackZones();
    }
  }, [url, loadFallbackZones]);

  // Sync the ref on every render inside an effect so the close handler always has the latest connect callback
  useEffect(() => {
    connectRef.current = connect;
  }, [connect]);

  useEffect(() => {
    loadFallbackZones();
    connect();
    return () => {
      if (reconnectTimeoutRef.current)
        clearTimeout(reconnectTimeoutRef.current);
      if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);
      wsRef.current?.close();
    };
  }, [connect, loadFallbackZones]);

  return state;
}
