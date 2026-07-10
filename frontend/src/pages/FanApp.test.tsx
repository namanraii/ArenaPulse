import { render, screen } from '@testing-library/react'
import { FanApp } from './FanApp'
import { BrowserRouter } from 'react-router-dom'

describe('FanApp', () => {
  it('renders correctly', () => {
    render(
      <BrowserRouter>
        <FanApp />
      </BrowserRouter>
    )
    expect(screen.getByText('ArenaPulse')).toBeInTheDocument()
    expect(screen.getByText('Find Your Way')).toBeInTheDocument()
    expect(screen.getByText('Zone Densities')).toBeInTheDocument()
  })
})
