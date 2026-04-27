interface Props {
  state: string
  confidence: number
  summary?: string
}

const STATE_STYLES: Record<string, { bg: string; border: string; leftBorder: string; text: string }> = {
  stable:      { bg: '#f0fdf4', border: '#bbf7d0', leftBorder: '#86efac', text: '#15803d' },
  compressing: { bg: '#fffbeb', border: '#fde68a', leftBorder: '#fde68a', text: '#b45309' },
  volatile:    { bg: '#fef2f2', border: '#fecaca', leftBorder: '#fca5a5', text: '#b91c1c' },
  agitated:    { bg: '#faf5ff', border: '#ddd6fe', leftBorder: '#c4b5fd', text: '#6d28d9' },
  fragmenting: { bg: '#f0f9ff', border: '#bae6fd', leftBorder: '#bae6fd', text: '#0369a1' },
}

export default function StateBanner({ state, confidence, summary }: Props) {
  const baseState = state.split(' (')[0].toLowerCase()
  const s = STATE_STYLES[baseState] ?? STATE_STYLES.stable

  return (
    <div
      style={{
        background: s.bg,
        border: `1px solid ${s.border}`,
        borderLeft: `5px solid ${s.leftBorder}`,
        color: s.text,
      }}
      className="rounded-lg px-7 py-5 flex justify-between items-center mb-5"
    >
      <div>
        <p className="text-xs font-bold uppercase tracking-widest opacity-75 mb-1">
          Current Crowd State
        </p>
        <p className="text-2xl font-extrabold tracking-wide">{state.toUpperCase()}</p>
        {summary && (
          <p className="text-xs opacity-70 mt-1 font-normal">{summary}</p>
        )}
      </div>
      <div className="text-right">
        <p className="text-xs uppercase tracking-widest opacity-65 mb-0.5">Confidence</p>
        <p className="text-4xl font-extrabold">{Math.round(confidence * 100)}%</p>
      </div>
    </div>
  )
}
