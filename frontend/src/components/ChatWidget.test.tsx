import { render, screen, fireEvent } from '@testing-library/react'
import { ChatWidget } from './ChatWidget'

describe('ChatWidget', () => {
  it('renders chat FAB button initially', () => {
    render(<ChatWidget language="en-US" />)
    expect(screen.getByRole('button', { name: /open chat/i })).toBeInTheDocument()
  })

  it('opens chat panel when FAB is clicked', () => {
    render(<ChatWidget language="en-US" />)
    const fab = screen.getByRole('button', { name: /open chat/i })
    fireEvent.click(fab)
    expect(screen.getByRole('dialog', { name: /concierge chat/i })).toBeInTheDocument()
    expect(screen.getByText('ArenaPulse Concierge')).toBeInTheDocument()
  })
})
