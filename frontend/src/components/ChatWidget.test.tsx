import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { vi } from 'vitest';
import { ChatWidget } from './ChatWidget';

// Mock api.chat so tests don't make real network calls
vi.mock('../services/api', () => ({
  api: {
    chat: vi.fn().mockResolvedValue({
      response: 'Hello! How can I help you?',
      sources: [],
      detected_intent: 'general',
      language: 'en',
    }),
  },
}));

describe('ChatWidget', () => {
  it('renders chat FAB button initially', () => {
    render(<ChatWidget language="en" />);
    expect(
      screen.getByRole('button', { name: /open chat/i })
    ).toBeInTheDocument();
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });

  it('opens chat panel when FAB is clicked', () => {
    render(<ChatWidget language="en" />);
    fireEvent.click(screen.getByRole('button', { name: /open chat/i }));
    expect(screen.getByRole('dialog')).toBeInTheDocument();
    expect(screen.getByText('ArenaPulse Concierge')).toBeInTheDocument();
  });

  it('closes chat panel when close button is clicked', () => {
    render(<ChatWidget language="en" />);
    fireEvent.click(screen.getByRole('button', { name: /open chat/i }));
    expect(screen.getByRole('dialog')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: /close chat/i }));
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });

  it('shows empty state when no messages', () => {
    render(<ChatWidget language="en" />);
    fireEvent.click(screen.getByRole('button', { name: /open chat/i }));
    expect(screen.getByText(/ask about routes/i)).toBeInTheDocument();
  });

  it('sends a message and shows assistant response', async () => {
    render(<ChatWidget language="en" />);
    fireEvent.click(screen.getByRole('button', { name: /open chat/i }));

    const textarea = screen.getByRole('textbox', { name: /message/i });
    fireEvent.change(textarea, { target: { value: 'Where is the restroom?' } });
    fireEvent.click(screen.getByRole('button', { name: /send message/i }));

    await waitFor(() => {
      expect(screen.getByText('Where is the restroom?')).toBeInTheDocument();
    });
    await waitFor(() => {
      expect(
        screen.getByText('Hello! How can I help you?')
      ).toBeInTheDocument();
    });
  });

  it('voice output button toggles state when clicked', () => {
    render(<ChatWidget language="en" voiceEnabled={false} />);
    fireEvent.click(screen.getByRole('button', { name: /open chat/i }));
    const voiceBtn = screen.getByRole('button', {
      name: /enable voice output/i,
    });
    expect(voiceBtn).toBeInTheDocument();
    fireEvent.click(voiceBtn);
    expect(
      screen.getByRole('button', { name: /disable voice output/i })
    ).toBeInTheDocument();
  });

  it('voiceEnabled prop initialises voice output on', () => {
    render(<ChatWidget language="en" voiceEnabled={true} />);
    fireEvent.click(screen.getByRole('button', { name: /open chat/i }));
    expect(
      screen.getByRole('button', { name: /disable voice output/i })
    ).toBeInTheDocument();
  });

  it('Escape key closes the dialog', () => {
    render(<ChatWidget language="en" />);
    fireEvent.click(screen.getByRole('button', { name: /open chat/i }));
    expect(screen.getByRole('dialog')).toBeInTheDocument();
    fireEvent.keyDown(screen.getByRole('textbox', { name: /message/i }), {
      key: 'Escape',
      code: 'Escape',
    });
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });
});
