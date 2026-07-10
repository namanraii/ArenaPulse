import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { vi } from 'vitest';
import { MemoryRouter } from 'react-router-dom';
import { auth } from '../services/api';

// Mock modules before component import
vi.mock('../services/api', () => ({
  api: {
    actions: vi.fn().mockResolvedValue([]),
    sustainability: vi.fn().mockResolvedValue({
      transit_split: { metro: 0.4, bus: 0.3, rideshare: 0.3 },
      sustainability_score: 72,
      eco_tips: ['Use public transit'],
    }),
    efficiency: vi.fn().mockResolvedValue({
      cache_hits: 10,
      cache_misses: 2,
      flash_calls: 8,
      pro_calls: 4,
      cache_hit_rate_pct: 83,
      estimated_cost_usd: 0.05,
      estimated_tokens_saved: 1200,
      routing_strategy: 'Flash for fan chat; Pro for ops',
    }),
    auditLogs: vi.fn().mockResolvedValue([]),
    alerts: vi.fn().mockResolvedValue([]),
  },
  auth: {
    isLoggedIn: vi.fn().mockReturnValue(true),
    getUser: vi.fn().mockReturnValue({
      id: 1,
      username: 'organizer1',
      email: 'org@test.com',
      role: 'organizer',
    }),
    logout: vi.fn(),
  },
}));

vi.mock('../hooks/useWebSocket', () => ({
  useWebSocket: () => ({ zones: [], isConnected: false, error: null }),
}));

import { OpsDashboard } from './OpsDashboard';

const renderWithRouter = (ui: React.ReactElement) =>
  render(<MemoryRouter>{ui}</MemoryRouter>);

describe('OpsDashboard — Organizer', () => {
  beforeEach(() => {
    vi.mocked(auth.getUser).mockReturnValue({
      id: 1,
      username: 'organizer1',
      email: 'org@test.com',
      role: 'organizer',
    });
  });

  it('renders the dashboard heading', () => {
    renderWithRouter(<OpsDashboard />);
    expect(screen.getByRole('heading', { level: 1 })).toBeInTheDocument();
  });

  it('shows username in role badge', () => {
    renderWithRouter(<OpsDashboard />);
    expect(screen.getByText(/organizer1/i)).toBeInTheDocument();
  });

  it('shows audit and efficiency tabs for organizer', () => {
    renderWithRouter(<OpsDashboard />);
    expect(screen.getByRole('button', { name: /audit/i })).toBeInTheDocument();
    expect(
      screen.getByRole('button', { name: /efficiency/i })
    ).toBeInTheDocument();
  });

  it('shows no pending actions when queue is empty', async () => {
    renderWithRouter(<OpsDashboard />);
    fireEvent.click(screen.getByRole('button', { name: /actions/i }));
    await waitFor(() => {
      expect(screen.getByText(/all clear/i)).toBeInTheDocument();
    });
  });
});

describe('OpsDashboard — Volunteer', () => {
  beforeEach(() => {
    vi.mocked(auth.getUser).mockReturnValue({
      id: 2,
      username: 'volunteer1',
      email: 'vol@test.com',
      role: 'volunteer',
    });
  });

  it('hides audit tab for volunteer', () => {
    renderWithRouter(<OpsDashboard />);
    expect(
      screen.queryByRole('button', { name: /audit/i })
    ).not.toBeInTheDocument();
  });

  it('hides efficiency tab for volunteer', () => {
    renderWithRouter(<OpsDashboard />);
    expect(
      screen.queryByRole('button', { name: /efficiency/i })
    ).not.toBeInTheDocument();
  });

  it('shows volunteer username in badge', () => {
    renderWithRouter(<OpsDashboard />);
    expect(screen.getByText(/volunteer1/i)).toBeInTheDocument();
  });
});
