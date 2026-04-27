import type { Interventions } from '@/lib/types'

interface Props {
  plan: Interventions
}

const PRIORITY_COLOR: Record<string, string> = {
  critical: '#fca5a5',
  high:     '#fdba74',
  medium:   '#fde68a',
  low:      '#86efac',
}

export default function InterventionPanel({ plan }: Props) {
  return (
    <div>
      <p className="text-xs font-bold uppercase tracking-widest text-slate-400 mb-3 pb-2 border-b border-slate-200">
        Intervention Plan
      </p>
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        {/* Level badge */}
        <div
          className="rounded-lg px-4 py-5 text-center border flex flex-col justify-center"
          style={{
            background: plan.pastel_bg,
            borderColor: plan.border_color,
            borderLeftWidth: 4,
            color: plan.text_color,
          }}
        >
          <p className="text-base font-extrabold tracking-wide">{plan.level}</p>
          <p className="text-xs text-slate-400 mt-1 uppercase tracking-wide">Response Level</p>
        </div>

        {/* Action cards */}
        <div className="md:col-span-3 space-y-2.5">
          {plan.actions.map((action, i) => {
            const priorityKey = action.priority.toLowerCase()
            const leftColor = PRIORITY_COLOR[priorityKey] ?? '#cbd5e1'
            return (
              <div
                key={i}
                className="bg-white border border-slate-200 rounded-lg px-4 py-3"
                style={{ borderLeft: `4px solid ${leftColor}` }}
              >
                <p className="text-sm font-medium text-slate-800 mb-1">{action.action}</p>
                <p className="text-xs text-slate-400">
                  <span className="mr-3">Priority: <strong>{action.priority}</strong></span>
                  <span className="mr-3">Owner: <strong>{action.owner}</strong></span>
                  <span>Outcome: {action.outcome}</span>
                </p>
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}
