import { render, screen } from '@testing-library/react'
import InterventionPanel from '@/components/InterventionPanel'
import type { Interventions } from '@/lib/types'

const mockPlan: Interventions = {
  level: 'ELEVATED',
  pastel_bg: '#fffbeb',
  text_color: '#b45309',
  border_color: '#fde68a',
  actions: [
    {
      priority: 'High',
      action: 'Deploy crowd marshals to main entry.',
      owner: 'Security',
      outcome: 'Reduce entry bottleneck.',
    },
    {
      priority: 'Medium',
      action: 'Open secondary exits.',
      owner: 'Operations',
      outcome: 'Improve flow distribution.',
    },
  ],
}

describe('InterventionPanel', () => {
  it('renders response level', () => {
    render(<InterventionPanel plan={mockPlan} />)
    expect(screen.getByText('ELEVATED')).toBeInTheDocument()
  })

  it('renders all actions', () => {
    render(<InterventionPanel plan={mockPlan} />)
    expect(screen.getByText('Deploy crowd marshals to main entry.')).toBeInTheDocument()
    expect(screen.getByText('Open secondary exits.')).toBeInTheDocument()
  })

  it('renders owner for each action', () => {
    render(<InterventionPanel plan={mockPlan} />)
    expect(screen.getByText(/Security/)).toBeInTheDocument()
    expect(screen.getByText(/Operations/)).toBeInTheDocument()
  })
})
