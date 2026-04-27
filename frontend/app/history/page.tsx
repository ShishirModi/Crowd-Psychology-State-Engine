'use client'

import { useState, useEffect, useCallback } from 'react'
import { useRouter } from 'next/navigation'
import NavBar from '@/components/NavBar'
import { getHistory } from '@/lib/api'
import type { HistoryRecord } from '@/lib/types'
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, ReferenceLine,
} from 'recharts'

export default function HistoryPage() {
  const router = useRouter()
  const [records, setRecords] = useState<HistoryRecord[]>([])
  const [loading, setLoading] = useState(false)
  const [location, setLocation] = useState('')
  const [limit, setLimit] = useState(100)
  const [anomalyOnly, setAnomalyOnly] = useState(false)
  const [error, setError] = useState('')
  const [authChecked, setAuthChecked] = useState(false)

  useEffect(() => {
    if (!localStorage.getItem('cpse_user')) {
      router.push('/login')
    } else {
      setAuthChecked(true)
    }
  }, [router])

  const fetchRecords = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const data = await getHistory({
        limit,
        location: location || undefined,
        anomaly_only: anomalyOnly,
      })
      setRecords(data)
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to load history')
    } finally {
      setLoading(false)
    }
  }, [limit, location, anomalyOnly])

  useEffect(() => {
    if (authChecked) fetchRecords()
  }, [authChecked, fetchRecords])

  if (!authChecked) return null

  // KPI calculations
  const totalRecords = records.length
  const avgCongestion =
    records.length > 0
      ? (records.reduce((s, r) => s + (r.congestion ?? 0), 0) / records.length).toFixed(3)
      : '—'
  const anomalyCount = records.filter(r => (r.anomaly_score ?? 0) > 2.5).length
  const stateCounts = records.reduce<Record<string, number>>((acc, r) => {
    const s = r.state?.split(' (')[0] ?? 'Unknown'
    acc[s] = (acc[s] ?? 0) + 1
    return acc
  }, {})
  const dominantState =
    Object.entries(stateCounts).sort(([, a], [, b]) => b - a)[0]?.[0] ?? '—'

  // Chart data (sorted ascending for trend)
  const chartData = [...records]
    .sort((a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime())
    .map(r => ({
      time: new Date(r.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      congestion: r.congestion ?? 0,
      anomaly: r.anomaly_score ?? 0,
    }))

  // CSV export
  function downloadCSV() {
    const headers = [
      'id', 'created_at', 'location_name', 'congestion', 'speed',
      'gradient', 'velocity_var', 'anomaly_score', 'risk_score', 'state',
    ]
    const rows = records.map(r =>
      headers.map(h => String(r[h as keyof HistoryRecord] ?? '')).join(',')
    )
    const csv = [headers.join(','), ...rows].join('\n')
    const blob = new Blob([csv], { type: 'text/csv' })
    const a = document.createElement('a')
    a.href = URL.createObjectURL(blob)
    a.download = 'cpse_telemetry.csv'
    a.click()
  }

  return (
    <div className="min-h-screen bg-slate-50">
      <NavBar />
      <main className="max-w-7xl mx-auto px-6 py-6">
        <div className="mb-6">
          <h1 className="text-xl font-bold text-slate-800">Historical Telemetry</h1>
          <p className="text-sm text-slate-500">Query and analyse persisted crowd telemetry.</p>
        </div>

        {/* Filters */}
        <div className="bg-white border border-slate-200 rounded-lg p-4 mb-6">
          <p className="text-xs font-bold uppercase tracking-widest text-slate-400 mb-3">Query Filters</p>
          <div className="flex flex-wrap gap-3 items-end">
            <div>
              <label className="text-xs text-slate-500 block mb-1">Location</label>
              <input
                type="text"
                value={location}
                onChange={e => setLocation(e.target.value)}
                placeholder="All locations"
                className="border border-slate-200 rounded px-2 py-1.5 text-sm w-44"
              />
            </div>
            <div>
              <label className="text-xs text-slate-500 block mb-1">Limit: {limit}</label>
              <input
                type="range" min={10} max={500} step={10}
                value={limit}
                onChange={e => setLimit(parseInt(e.target.value))}
                className="w-32"
              />
            </div>
            <div className="flex items-center gap-2">
              <input
                type="checkbox"
                id="anom"
                checked={anomalyOnly}
                onChange={e => setAnomalyOnly(e.target.checked)}
              />
              <label htmlFor="anom" className="text-xs text-slate-500">Anomalies Only</label>
            </div>
            <button
              onClick={fetchRecords}
              className="bg-slate-800 text-white rounded px-3 py-1.5 text-xs font-semibold hover:bg-slate-700 transition-colors"
            >
              {loading ? 'Loading…' : 'Refresh'}
            </button>
          </div>
          {error && <p className="text-sm text-red-600 mt-2">{error}</p>}
        </div>

        {/* KPI cards */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
          {[
            { label: 'Total Records', value: totalRecords.toLocaleString() },
            { label: 'Avg Congestion', value: avgCongestion },
            { label: 'Anomalies Detected', value: anomalyCount.toLocaleString() },
            { label: 'Dominant State', value: dominantState },
          ].map(kpi => (
            <div key={kpi.label} className="bg-white border border-slate-200 rounded-lg p-4">
              <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1">
                {kpi.label}
              </p>
              <p className="text-2xl font-bold text-slate-800">{kpi.value}</p>
            </div>
          ))}
        </div>

        {/* Trend chart (only when location is specified and has data) */}
        {location && chartData.length > 1 && (
          <div className="bg-white border border-slate-200 rounded-lg p-4 mb-6">
            <p className="text-xs font-bold uppercase tracking-widest text-slate-400 mb-3">
              Congestion Trend — {location.toUpperCase()}
            </p>
            <ResponsiveContainer width="100%" height={280}>
              <LineChart data={chartData} margin={{ top: 5, right: 10, left: -20, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(226,232,240,0.8)" />
                <XAxis dataKey="time" tick={{ fontSize: 10, fill: '#94a3b8' }} />
                <YAxis tick={{ fontSize: 10, fill: '#94a3b8' }} />
                <Tooltip contentStyle={{ fontSize: 11, borderColor: '#e2e8f0' }} />
                <Line
                  type="monotone" dataKey="congestion" name="Congestion"
                  stroke="#7eb8da" strokeWidth={2} dot={false}
                />
                <Line
                  type="monotone" dataKey="anomaly" name="Anomaly Z"
                  stroke="#d47a7a" strokeWidth={1.5} strokeDasharray="5 2" dot={false}
                />
                <ReferenceLine
                  y={2.5} stroke="rgba(212,122,122,0.5)" strokeDasharray="3 3"
                  label={{ value: 'Z=2.5', fill: '#d47a7a', fontSize: 10 }}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        )}

        {/* Table */}
        {records.length > 0 ? (
          <div className="bg-white border border-slate-200 rounded-lg overflow-hidden">
            <div className="flex items-center justify-between px-4 py-3 border-b border-slate-100">
              <p className="text-xs font-bold uppercase tracking-widest text-slate-400">
                Detailed Logs ({records.length})
              </p>
              <button
                onClick={downloadCSV}
                className="text-xs text-slate-500 hover:text-slate-800 border border-slate-200 rounded px-2 py-1 transition-colors"
              >
                Download CSV
              </button>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-xs">
                <thead>
                  <tr className="bg-slate-50 text-left">
                    {['Timestamp', 'Location', 'Congestion', 'Speed', 'Gradient', 'Anomaly Z', 'Risk', 'State'].map(h => (
                      <th key={h} className="px-4 py-2 text-xs font-semibold text-slate-400 uppercase tracking-wider">
                        {h}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {records.map(r => (
                    <tr key={r.id} className="border-t border-slate-100 hover:bg-slate-50">
                      <td className="px-4 py-2 text-slate-500 whitespace-nowrap">
                        {new Date(r.created_at).toLocaleString()}
                      </td>
                      <td className="px-4 py-2 text-slate-700 font-medium">{r.location_name}</td>
                      <td className="px-4 py-2">
                        <div className="flex items-center gap-2">
                          <div className="w-16 bg-slate-100 rounded-full h-1.5 overflow-hidden">
                            <div
                              className="h-full bg-sky-400 rounded-full"
                              style={{ width: `${(r.congestion ?? 0) * 100}%` }}
                            />
                          </div>
                          <span>{(r.congestion ?? 0).toFixed(3)}</span>
                        </div>
                      </td>
                      <td className="px-4 py-2 text-slate-600">{r.speed?.toFixed(1) ?? '—'}</td>
                      <td className="px-4 py-2 text-slate-600">{r.gradient?.toFixed(4) ?? '—'}</td>
                      <td className="px-4 py-2 font-mono">
                        <span className={`${(r.anomaly_score ?? 0) > 2.5 ? 'text-red-500 font-bold' : 'text-slate-600'}`}>
                          {r.anomaly_score?.toFixed(2) ?? '—'}
                        </span>
                      </td>
                      <td className="px-4 py-2 text-slate-600">{r.risk_score?.toFixed(0) ?? '—'}</td>
                      <td className="px-4 py-2">
                        <span className="text-slate-700 font-medium">{r.state}</span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        ) : (
          !loading && (
            <div className="bg-white border border-slate-200 rounded-lg p-8 text-center text-slate-400 text-sm">
              No records found. Run an analysis session first.
            </div>
          )
        )}
      </main>
    </div>
  )
}
