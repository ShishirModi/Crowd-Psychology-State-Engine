import { render, screen } from '@testing-library/react'
import RiskBar from '@/components/RiskBar'

describe('RiskBar', () => {
  it('renders score', () => {
    render(<RiskBar score={42} verdict="Moderate risk." formula="0.4G+0.3V" />)
    expect(screen.getByText('42/100')).toBeInTheDocument()
  })

  it('renders verdict', () => {
    render(<RiskBar score={42} verdict="Moderate risk." formula="0.4G+0.3V" />)
    expect(screen.getByText('Moderate risk.')).toBeInTheDocument()
  })
})
