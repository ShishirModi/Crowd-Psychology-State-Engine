interface Props {
  score: number
  verdict?: string
  formula?: string
}

function barColor(score: number): string {
  if (score > 75) return '#f87171'
  if (score > 50) return '#fb923c'
  if (score > 25) return '#fbbf24'
  return '#4ade80'
}

export default function RiskBar({ score, verdict, formula }: Props) {
  const color = barColor(score)
  return (
    <div className="bg-white border border-slate-200 rounded-lg px-5 py-4 mb-5">
      <div className="flex justify-between items-baseline mb-2">
        <span className="text-xs font-bold uppercase tracking-widest text-slate-400">
          Composite Risk Score
        </span>
        <span className="text-xl font-bold" style={{ color }}>
          {score}/100
        </span>
      </div>
      <div className="bg-slate-100 rounded-full h-3 overflow-hidden">
        <div
          className="h-full rounded-full transition-all duration-500"
          style={{ width: `${Math.min(score, 100)}%`, background: color }}
        />
      </div>
      {verdict && (
        <p className="text-xs text-slate-400 mt-1.5">{verdict}</p>
      )}
      {formula && (
        <p className="text-xs text-slate-300 mt-0.5">Formula: {formula}</p>
      )}
    </div>
  )
}
