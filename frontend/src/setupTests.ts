import '@testing-library/jest-dom';

// Mock matchMedia
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: (query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: () => {},
    removeListener: () => {},
    addEventListener: () => {},
    removeEventListener: () => {},
    dispatchEvent: () => false,
  }),
});

// Mock ResizeObserver
class ResizeObserver {
  observe() {}
  unobserve() {}
  disconnect() {}
}
window.ResizeObserver = ResizeObserver;

// Mock window.speechSynthesis
window.speechSynthesis = {
  cancel: () => {},
  speak: () => {},
  pause: () => {},
  resume: () => {},
  getVoices: () => [],
  pending: false,
  speaking: false,
  paused: false,
  onvoiceschanged: null,
} as any;

// Mock global fetch
globalThis.fetch = (() => Promise.resolve({
  ok: true,
  json: () => Promise.resolve({}),
})) as any;
