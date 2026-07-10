import { describe, it, expect } from 'vitest';
import { render } from '@testing-library/react';
import { AccessibilityToolbar } from '../AccessibilityToolbar';

describe('AccessibilityToolbar', () => {
  it('renders accessibility buttons', () => {
    const settings = {
      highContrast: false,
      largeText: false,
      reducedMotion: false,
      voiceEnabled: false,
    };
    const { getByLabelText } = render(<AccessibilityToolbar settings={settings} onToggle={() => {}} offline={false} />);
    expect(getByLabelText(/High Contrast/i)).toBeInTheDocument();
  });
});
