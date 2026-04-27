'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import NavBar from '@/components/NavBar'
import { analyze, pollResult } from '@/lib/api'
import type { AnalyzeParams, PollResponse, AnalysisResult } from '@/lib/types'

const POLL_INTERVAL = 2000

function isDone(r: PollResponse): r is AnalysisResult {
  return r.status === 'done'
}

export default function DashboardPage() {
  const router = useRouter()
  const [params, setParams] = useState<AnalyzeParams>({
    lat: 28.6139,
    lon: 77.2090,
    location_name: 'Delhi',
    env_weather_risk: 0,
    env_width_factor: 1,
    env_event_active: false,
  })
  const [result, setResult] = useState<PollResponse | null>(null)
  const [taskId, setTaskId] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [authChecked, setAuthChecked] = useState(false)

  useEffect(() => {
    if (!localStorage.getItem('cpse_user')) {
      router.push('/login')
    } else {
      setAuthChecked(true)
    }
  }, [router])

  useEffect(() => {
    if (!taskId) return
    let cancelled = false
    const id = setInterval(async () => {
      try {
        const r = await pollResult(taskId)
        if (cancelled) return
        if (r.status === 'done') {
          setResult(r)
          setLoading(false)
          clearInterval(id)
          setTaskId(null)
        }
      } catch {
        if (cancelled) return
        clearInterval(id)
        setError('Polling failed — result may not be available')
        setLoading(false)
      }
    }, POLL_INTERVAL)
    return () => {
      cancelled = true
      clearInterval(id)
    }
  }, [taskId])

  async function handleAnalyze() {
    setError('')
    setLoading(true)
    try {
      const { task_id } = await analyze(params)
      setTaskId(task_id)
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to start analysis')
      setLoading(false)
    }
  }

  const doneResult = result && isDone(result) ? result : null

  if (!authChecked) return null

  return (
    <div className="min-h-screen bg-slate-50">
      <NavBar />
      <main className="max-w-7xl mx-auto px-6 py-6">
        <div className="flex items-start justify-between mb-6">
          <div>
            <h1 className="text-xl font-bold text-slate-800">Crowd Psychology State Engine</h1>
            <p className="text-sm text-slate-500">Real-time crowd dynamics classification &amp; risk analysis</p>
          </div>
        </div>

        {/* Analysis form */}
        <div className="bg-white border border-slate-200 rounded-lg p-4 mb-6">
          <p className="text-xs font-bold uppercase tracking-widest text-slate-400 mb-3">Analysis Parameters</p>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-3">
            <div>
              <label className="text-xs text-slate-500 mb-1 block">Location Name</label>
              <input
                type="text"
                value={params.location_name}
                onChange={e => setParams(p => ({ ...p, location_name: e.target.value }))}
                className="w-full border border-slate-200 rounded px-2 py-1.5 text-sm"
              />
            </div>
            <div>
              <label className="text-xs text-slate-500 mb-1 block">Latitude</label>
              <input
                type="number"
                step="0.0001"
                value={params.lat}
                onChange={e => setParams(p => ({ ...p, lat: parseFloat(e.target.value) }))}
                className="w-full border border-slate-200 rounded px-2 py-1.5 text-sm"
              />
            </div>
            <div>
              <label className="text-xs text-slate-500 mb-1 block">Longitude</label>
              <input
                type="number"
                step="0.0001"
                value={params.lon}
                onChange={e => setParams(p => ({ ...p, lon: parseFloat(e.target.value) }))}
                className="w-full border border-slate-200 rounded px-2 py-1.5 text-sm"
              />
            </div>
            <div>
              <label className="text-xs text-slate-500 mb-1 block">
                Weather Risk: {params.env_weather_risk.toFixed(2)}
              </label>
              <input
                type="range"
                min="0" max="1" step="0.05"
                value={params.env_weather_risk}
                onChange={e => setParams(p => ({ ...p, env_weather_risk: parseFloat(e.target.value) }))}
                className="w-full mt-1"
              />
            </div>
            <div>
              <label className="text-xs text-slate-500 mb-1 block">
                Width Factor: {params.env_width_factor.toFixed(1)}×
              </label>
              <input
                type="range"
                min="0.1" max="2" step="0.1"
                value={params.env_width_factor}
                onChange={e => setParams(p => ({ ...p, env_width_factor: parseFloat(e.target.value) }))}
                className="w-full mt-1"
              />
            </div>
            <div className="flex items-center gap-2 pt-4">
              <input
                type="checkbox"
                id="event"
                checked={params.env_event_active}
                onChange={e => setParams(p => ({ ...p, env_event_active: e.target.checked }))}
              />
              <label htmlFor="event" className="text-xs text-slate-500">Active Event</label>
            </div>
          </div>

          <button
            onClick={handleAnalyze}
            disabled={loading}
            className="bg-slate-800 text-white rounded px-4 py-2 text-sm font-semibold hover:bg-slate-700 disabled:opacity-50 transition-colors"
          >
            {loading ? 'Analysing…' : 'Run Analysis'}
          </button>

          {error && (
            <p className="text-sm text-red-600 mt-2">{error}</p>
          )}
        </div>

        {loading && (
          <div className="text-sm text-slate-500 animate-pulse">Running analysis…</div>
        )}

        {/* Result area — raw JSON for now, replaced in Tasks 4–7 */}
        {doneResult && (
          <pre className="text-xs bg-white border border-slate-200 rounded p-4 overflow-auto max-h-96">
            {JSON.stringify(doneResult, null, 2)}
          </pre>
        )}
      </main>
    </div>
  )
}
