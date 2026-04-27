import { render, screen } from '@testing-library/react'
import MetricsGrid from '@/components/MetricsGrid'
import type { AnalysisResult } from '@/lib/types'

const mockResult: Partial<AnalysisResult> = {
  congestion: 0.452,
  gradient: 0.3,
  velocity_var: 0.12,
  anomaly_score: 1.2,
  breakdown: {
    compression_gradient: { rating: 'watch', verdict: 'Rising density.' },
    velocity_variance: { rating: 'safe', verdict: 'Mild turbulence.' },
    anomaly_score: { rating: 'safe', verdict: 'Normal.' },
  },
}

describe('MetricsGrid', () => {
  it('renders all four metric labels', () => {
    render(<MetricsGrid result={mockResult as AnalysisResult} />)
    expect(screen.getByText('Congestion Level')).toBeInTheDocument()
    expect(screen.getByText('Compression Gradient')).toBeInTheDocument()
    expect(screen.getByText('Velocity Variance (CV)')).toBeInTheDocument()
    expect(screen.getByText('Anomaly Score (Z)')).toBeInTheDocument()
  })

  it('renders congestion value', () => {
    render(<MetricsGrid result={mockResult as AnalysisResult} />)
    expect(screen.getByText('0.452')).toBeInTheDocument()
  })

  it('renders verdict text', () => {
    render(<MetricsGrid result={mockResult as AnalysisResult} />)
    expect(screen.getByText('Rising density.')).toBeInTheDocument()
  })
})
