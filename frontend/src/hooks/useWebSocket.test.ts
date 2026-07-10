import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';

// Mock api.zones
vi.mock('../services/api', () => ({
  api: {
    zones: vi
      .fn()
      .mockResolvedValue([
        { name: 'Zone_1', density: 0.4, label: 'North', capacity: 10000 },
      ]),
  },
}));

// We need to intercept WebSocket constructor calls
const mockClose = vi.fn();

interface MockWS {
  onopen: (() => void) | null;
  onmessage: ((e: { data: string }) => void) | null;
  onclose: (() => void) | null;
  onerror: (() => void) | null;
  close: () => void;
}

let lastWs: MockWS | null = null;

class MockWebSocket implements MockWS {
  onopen: (() => void) | null = null;
  onmessage: ((e: { data: string }) => void) | null = null;
  onclose: (() => void) | null = null;
  onerror: (() => void) | null = null;
  close = mockClose;

  constructor(_url: string) {
    lastWs = this;
  }
}

vi.stubGlobal('WebSocket', MockWebSocket);

import { useWebSocket } from './useWebSocket';

describe('useWebSocket', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    lastWs = null;
  });

  it('starts with zones array defined', () => {
    const { result } = renderHook(() => useWebSocket('ws://localhost/test'));
    expect(Array.isArray(result.current.zones)).toBe(true);
  });

  it('sets isConnected to true when WebSocket opens', () => {
    const { result } = renderHook(() => useWebSocket('ws://localhost/test'));
    act(() => {
      lastWs?.onopen?.();
    });
    expect(result.current.isConnected).toBe(true);
    expect(result.current.error).toBeNull();
  });

  it('updates zones when crowd_update message is received', () => {
    const { result } = renderHook(() => useWebSocket('ws://localhost/test'));
    act(() => {
      lastWs?.onopen?.();
    });
    const payload = {
      type: 'crowd_update',
      zones: [{ name: 'Zone_2', density: 0.8, label: 'South', capacity: 8000 }],
    };
    act(() => {
      lastWs?.onmessage?.({ data: JSON.stringify(payload) });
    });
    expect(result.current.zones[0].name).toBe('Zone_2');
    expect(result.current.zones[0].density).toBe(0.8);
  });

  it('sets isConnected to false on close', () => {
    const { result } = renderHook(() => useWebSocket('ws://localhost/test'));
    act(() => {
      lastWs?.onopen?.();
    });
    act(() => {
      lastWs?.onclose?.();
    });
    expect(result.current.isConnected).toBe(false);
  });

  it('sets error on WebSocket error', () => {
    const { result } = renderHook(() => useWebSocket('ws://localhost/test'));
    act(() => {
      lastWs?.onerror?.();
    });
    expect(result.current.error).toBe('WebSocket error');
  });

  it('ignores malformed JSON messages without throwing', () => {
    const { result } = renderHook(() => useWebSocket('ws://localhost/test'));
    act(() => {
      lastWs?.onopen?.();
    });
    // Should not throw
    expect(() => {
      act(() => {
        lastWs?.onmessage?.({ data: 'not-valid-json' });
      });
    }).not.toThrow();
    expect(result.current.isConnected).toBe(true);
  });
});
