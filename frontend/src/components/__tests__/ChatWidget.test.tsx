import { describe, it, expect } from 'vitest';
import { render } from '@testing-library/react';
import { ChatWidget } from '../ChatWidget';

describe('ChatWidget', () => {
  it('renders chat button', () => {
    const { getByRole } = render(<ChatWidget language="en" />);
    expect(getByRole('button', { name: /open chat/i })).toBeInTheDocument();
  });
});
