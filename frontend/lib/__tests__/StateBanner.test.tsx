import { render, screen } from '@testing-library/react'
import StateBanner from '@/components/StateBanner'

const props = {
  state: 'Stable',
  confidence: 0.87,
  summary: 'Normal crowd flow.',
}

describe('StateBanner', () => {
  it('renders state name uppercased', () => {
    render(<StateBanner {...props} />)
    expect(screen.getByText('STABLE')).toBeInTheDocument()
  })

  it('renders confidence as percentage', () => {
    render(<StateBanner {...props} />)
    expect(screen.getByText('87%')).toBeInTheDocument()
  })

  it('renders summary text', () => {
    render(<StateBanner {...props} />)
    expect(screen.getByText('Normal crowd flow.')).toBeInTheDocument()
  })
})
