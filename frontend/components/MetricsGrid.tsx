import type { AnalysisResult } from '@/lib/types'

interface Props {
  result: AnalysisResult
}

const RATING_COLOR: Record<string, string> = {
  safe:     '#86efac',
  watch:    '#fde68a',
  warning:  '#fdba74',
  critical: '#fca5a5',
}

interface MetricCardProps {
  label: string
  value: string
  rows: Record<string, string>
  verdict?: string
  rating?: string
  anomalyFlag?: boolean
}

function MetricCard({ label, value, rows, verdict, rating = 'safe', anomalyFlag }: MetricCardProps) {
  const borderColor = RATING_COLOR[rating] ?? RATING_COLOR.safe
  return (
    <div className="bg-white border border-slate-200 rounded-lg p-4">
      <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-0.5">{label}</p>
      <p className="text-2xl font-bold text-slate-800 mb-2">
        {value}
        {anomalyFlag !== undefined && (
          <span
            className={`ml-2 text-xs font-semibold px-1.5 py-0.5 rounded ${
              anomalyFlag ? 'bg-red-100 text-red-600' : 'bg-green-100 text-green-600'
            }`}
          >
            {anomalyFlag ? 'ANOMALY' : 'Normal'}
          </span>
        )}
      </p>
      <div
        className="rounded text-xs p-3"
        style={{
          background: '#f8fafc',
          borderLeft: `3px solid ${borderColor}`,
        }}
      >
        {Object.entries(rows).map(([k, v]) => (
          <div key={k} className="flex justify-between py-0.5 border-b border-slate-100 last:border-0">
            <span className="text-slate-400 font-medium">{k}</span>
            <span className="text-slate-700 font-semibold font-mono">{v}</span>
          </div>
        ))}
        {verdict && (
          <p className="mt-2 text-slate-400 italic text-xs">{verdict}</p>
        )}
      </div>
    </div>
  )
}

export default function MetricsGrid({ result }: Props) {
  const bd = result.breakdown

  return (
    <div>
      <p className="text-xs font-bold uppercase tracking-widest text-slate-400 mb-3 pb-2 border-b border-slate-200">
        Crowd Dynamics Metrics
      </p>
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        <MetricCard
          label="Congestion Level"
          value={result.congestion.toFixed(3)}
          rating={bd.compression_gradient?.rating}
          rows={{
            Formula: '1 − (Speed / FreeFlow)',
            Range: '0.0 free → 1.0 gridlock',
          }}
        />
        <MetricCard
          label="Compression Gradient"
          value={result.gradient.toFixed(4)}
          rating={bd.compression_gradient?.rating}
          verdict={bd.compression_gradient?.verdict}
          rows={{
            Formula: '0.6×Level + 0.4×Slope×5',
            Thresholds: 'S<0.1 | C<0.5 | V<0.8',
          }}
        />
        <MetricCard
          label="Velocity Variance (CV)"
          value={result.velocity_var.toFixed(4)}
          rating={bd.velocity_variance?.rating}
          verdict={bd.velocity_variance?.verdict}
          rows={{
            Formula: 'σ(Speed) / μ(Speed)',
            Thresholds: '>0.10 mild | >0.25 ↑ | >0.40 severe',
          }}
        />
        <MetricCard
          label="Anomaly Score (Z)"
          value={result.anomaly_score.toFixed(3)}
          rating={bd.anomaly_score?.rating}
          verdict={bd.anomaly_score?.verdict}
          anomalyFlag={result.anomaly_score > 2.5}
          rows={{
            Formula: 'max(|Xᵢ − μᵢ| / σᵢ)',
            Threshold: 'Z > 2.5',
          }}
        />
      </div>
    </div>
  )
}
