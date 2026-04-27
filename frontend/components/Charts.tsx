'use client'

import {
  ComposedChart, Area, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, ReferenceLine, PieChart, Pie, Cell,
  RadialBarChart, RadialBar,
} from 'recharts'
import type { AnalysisResult } from '@/lib/types'

export interface HistoryPoint {
  time: string
  congestion: number
  gradient: number
  velocity_var: number
  anomaly_score: number
  state: string
}

interface Props {
  history: HistoryPoint[]
  riskScore: number
}

const STATE_COLORS: Record<string, string> = {
  Stable:      '#86efac',
  Compressing: '#fde68a',
  Volatile:    '#fca5a5',
  Agitated:    '#c4b5fd',
  Fragmenting: '#bae6fd',
}

function riskColor(score: number): string {
  if (score > 75) return '#f87171'
  if (score > 50) return '#fb923c'
  if (score > 25) return '#fbbf24'
  return '#4ade80'
}

function tickFormatter(t: string) {
  try {
    return new Date(t).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })
  } catch {
    return t
  }
}

export default function Charts({ history, riskScore }: Props) {
  const stateCounts = history.reduce<Record<string, number>>((acc, p) => {
    const base = p.state.split(' (')[0]
    acc[base] = (acc[base] ?? 0) + 1
    return acc
  }, {})
  const pieData = Object.entries(stateCounts).map(([name, value]) => ({ name, value }))
  const gaugeData = [{ name: 'Risk', value: riskScore, fill: riskColor(riskScore) }]

  if (history.length < 2) {
    return (
      <p className="text-sm text-slate-400 italic py-4">
        Collecting initial data points — charts appear after 2+ samples.
      </p>
    )
  }

  return (
    <div>
      <p className="text-xs font-bold uppercase tracking-widest text-slate-400 mb-3 pb-2 border-b border-slate-200">
        Signal Telemetry &amp; Analysis
      </p>
      <div className="grid grid-cols-1 lg:grid-cols-5 gap-4">
        {/* Left: signal charts stacked */}
        <div className="lg:col-span-3 space-y-3">
          {/* Density + Compression pane */}
          <div className="bg-white border border-slate-200 rounded-lg p-3">
            <p className="text-xs text-slate-400 mb-2">Crowd Density &amp; Compression</p>
            <ResponsiveContainer width="100%" height={200}>
              <ComposedChart data={history} margin={{ top: 5, right: 10, left: -20, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(226,232,240,0.8)" />
                <XAxis dataKey="time" tickFormatter={tickFormatter} tick={{ fontSize: 10, fill: '#94a3b8' }} />
                <YAxis domain={[0, 1.15]} tick={{ fontSize: 10, fill: '#94a3b8' }} />
                <Tooltip contentStyle={{ fontSize: 11, borderColor: '#e2e8f0' }} />
                <Area
                  type="monotone" dataKey="congestion" name="Congestion"
                  stroke="#7eb8da" fill="rgba(126,184,218,0.12)" strokeWidth={2} dot={false}
                />
                <Line
                  type="monotone" dataKey="gradient" name="Gradient"
                  stroke="#c4a35a" strokeWidth={1.8} strokeDasharray="4 2" dot={false}
                />
              </ComposedChart>
            </ResponsiveContainer>
          </div>

          {/* Turbulence + Anomaly pane */}
          <div className="bg-white border border-slate-200 rounded-lg p-3">
            <p className="text-xs text-slate-400 mb-2">Turbulence &amp; Anomaly</p>
            <ResponsiveContainer width="100%" height={180}>
              <ComposedChart data={history} margin={{ top: 5, right: 10, left: -20, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(226,232,240,0.8)" />
                <XAxis dataKey="time" tickFormatter={tickFormatter} tick={{ fontSize: 10, fill: '#94a3b8' }} />
                <YAxis tick={{ fontSize: 10, fill: '#94a3b8' }} />
                <Tooltip contentStyle={{ fontSize: 11, borderColor: '#e2e8f0' }} />
                <ReferenceLine
                  y={2.5}
                  stroke="rgba(212,122,122,0.5)"
                  strokeDasharray="3 3"
                  label={{ value: 'Z=2.5', fill: '#d47a7a', fontSize: 10 }}
                />
                <Area
                  type="monotone" dataKey="velocity_var" name="Velocity CV"
                  stroke="#a89ad4" fill="rgba(168,154,212,0.10)" strokeWidth={1.8} dot={false}
                />
                <Line
                  type="monotone" dataKey="anomaly_score" name="Anomaly Z"
                  stroke="#d47a7a" strokeWidth={1.5} strokeDasharray="5 2" dot={false}
                />
              </ComposedChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Right: gauge + pie */}
        <div className="lg:col-span-2 space-y-3">
          {/* Risk gauge */}
          <div className="bg-white border border-slate-200 rounded-lg p-3">
            <p className="text-xs text-slate-400 mb-1">Risk Score</p>
            <ResponsiveContainer width="100%" height={160}>
              <RadialBarChart
                innerRadius="55%" outerRadius="80%"
                data={gaugeData} startAngle={180} endAngle={0}
              >
                <RadialBar dataKey="value" cornerRadius={6} background={{ fill: '#f1f5f9' }} />
                <text x="50%" y="75%" textAnchor="middle" fill="#1e293b" fontSize={28} fontWeight={700}>
                  {riskScore}
                </text>
                <text x="50%" y="88%" textAnchor="middle" fill="#94a3b8" fontSize={11}>
                  out of 100
                </text>
              </RadialBarChart>
            </ResponsiveContainer>
          </div>

          {/* State distribution pie */}
          {pieData.length > 0 && (
            <div className="bg-white border border-slate-200 rounded-lg p-3">
              <p className="text-xs text-slate-400 mb-1">State Distribution</p>
              <ResponsiveContainer width="100%" height={160}>
                <PieChart>
                  <Pie
                    data={pieData} dataKey="value" nameKey="name"
                    cx="50%" cy="50%" innerRadius="40%" outerRadius="65%"
                    label={({ name, percent }: { name?: string; percent?: number }) =>
                      `${name ?? ''} ${((percent ?? 0) * 100).toFixed(0)}%`
                    }
                    labelLine={false}
                  >
                    {pieData.map(entry => (
                      <Cell
                        key={entry.name}
                        fill={STATE_COLORS[entry.name] ?? '#94a3b8'}
                        stroke="#fff"
                        strokeWidth={2}
                      />
                    ))}
                  </Pie>
                </PieChart>
              </ResponsiveContainer>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
