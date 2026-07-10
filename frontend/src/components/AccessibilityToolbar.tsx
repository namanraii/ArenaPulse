import React from 'react'
import {
  Accessibility,
  Contrast,
  Type,
  Volume2,
  WifiOff,
} from 'lucide-react'

interface AccessibilityToolbarProps {
  settings: {
    highContrast: boolean
    largeText: boolean
    reducedMotion: boolean
    voiceEnabled: boolean
  }
  onToggle: (key: string) => void
  offline?: boolean
}

export function AccessibilityToolbar({ settings, onToggle, offline }: AccessibilityToolbarProps) {
  return (
    <aside className="a11y-bar" aria-label="Accessibility settings">
      {offline && (
        <span className="offline-badge" aria-live="polite">
          <WifiOff size={14} /> Offline mode
        </span>
      )}
      <button
        className={settings.highContrast ? 'active' : ''}
        onClick={() => onToggle('highContrast')}
        aria-pressed={settings.highContrast}
        aria-label="Toggle high contrast"
        title="High contrast"
      >
        <Contrast size={18} />
      </button>
      <button
        className={settings.largeText ? 'active' : ''}
        onClick={() => onToggle('largeText')}
        aria-pressed={settings.largeText}
        aria-label="Toggle large text"
        title="Large text"
      >
        <Type size={18} />
      </button>
      <button
        className={settings.voiceEnabled ? 'active' : ''}
        onClick={() => onToggle('voiceEnabled')}
        aria-pressed={settings.voiceEnabled}
        aria-label="Toggle voice assistance"
        title="Voice assistance"
      >
        <Volume2 size={18} />
      </button>
      <button
        className={settings.reducedMotion ? 'active' : ''}
        onClick={() => onToggle('reducedMotion')}
        aria-pressed={settings.reducedMotion}
        aria-label="Toggle reduced motion"
        title="Reduced motion"
      >
        <Accessibility size={18} />
      </button>
      <span className="a11y-label">
        <Accessibility size={16} /> Accessibility
      </span>
    </aside>
  )
}
