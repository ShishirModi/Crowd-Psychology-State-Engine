import type { AnalysisResult, AnalyzeParams, HistoryRecord } from './types'

const BASE = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    credentials: 'include',
    headers: { 'Content-Type': 'application/json' },
    ...init,
  })
  const data = await res.json()
  if (!res.ok) throw new Error(data.error ?? data.detail ?? 'Request failed')
  return data as T
}

export async function login(
  username: string,
  password: string
): Promise<{ username: string; is_admin: boolean }> {
  return request('/auth/login', {
    method: 'POST',
    body: JSON.stringify({ username, password }),
  })
}

export async function logout(): Promise<void> {
  await request('/auth/logout', { method: 'POST' })
}

export async function analyze(params: AnalyzeParams): Promise<{ task_id: string }> {
  return request('/analyze', { method: 'POST', body: JSON.stringify(params) })
}

export async function pollResult(taskId: string): Promise<AnalysisResult> {
  return request(`/result/${taskId}`)
}

export async function getHistory(params?: {
  limit?: number
  location?: string
  anomaly_only?: boolean
}): Promise<HistoryRecord[]> {
  const qs = new URLSearchParams()
  if (params?.limit) qs.set('limit', String(params.limit))
  if (params?.location) qs.set('location', params.location)
  if (params?.anomaly_only) qs.set('anomaly_only', 'true')
  return request(`/history?${qs}`)
}

export async function getLatest(location: string): Promise<AnalysisResult | null> {
  return request(`/latest?location=${encodeURIComponent(location)}`)
}
