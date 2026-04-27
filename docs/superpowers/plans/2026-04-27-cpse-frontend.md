# CPSE Frontend Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Next.js 14 frontend that authenticates via session cookie, submits crowd analysis jobs, polls for results, and renders the full CPSE dashboard (StateBanner, RiskBar, MetricsGrid, Charts, InterventionPanel) plus a History page.

**Architecture:** Next.js 14 App Router with all interactive components as client components (`'use client'`). The dashboard page owns polling state (POST /analyze → poll GET /result/{task_id} every 2 s). Components are pure — they receive props and render. Auth is session-cookie-based; `credentials: 'include'` on every fetch. Charts use recharts (no Plotly).

**Tech Stack:** Next.js 14, TypeScript, Tailwind CSS, recharts 2.x, Jest + @testing-library/react

---

## Scope Note

This plan is **frontend only**. The backend (Django + Celery) is already complete on `feat/django-restructure`. Run the backend before smoke-testing the frontend.

---

## File Map

**Created:**
```
frontend/
├── package.json
├── tsconfig.json
├── tailwind.config.ts
├── jest.config.ts
├── jest.setup.ts
├── .env.local                         ← NEXT_PUBLIC_API_URL=http://localhost:8000
├── app/
│   ├── layout.tsx                     ← root layout, Inter font, global CSS
│   ├── page.tsx                       ← redirect → /login
│   ├── globals.css                    ← Tailwind base + custom CSS vars
│   ├── login/
│   │   └── page.tsx                   ← login form → POST /auth/login → redirect /dashboard
│   ├── dashboard/
│   │   └── page.tsx                   ← analyze form + polling loop + full dashboard
│   └── history/
│       └── page.tsx                   ← history filter + KPI row + trend chart + table
├── components/
│   ├── NavBar.tsx                     ← top nav with logout
│   ├── StateBanner.tsx                ← state label + confidence badge
│   ├── RiskBar.tsx                    ← animated progress bar with score
│   ├── MetricsGrid.tsx                ← 4 metric cards (congestion/gradient/velocity/anomaly)
│   ├── Charts.tsx                     ← ComposedChart (signal history) + PieChart + gauge
│   └── InterventionPanel.tsx          ← response level badge + action cards
└── lib/
    ├── types.ts                       ← AnalysisResult, HistoryRecord, Intervention
    ├── api.ts                         ← login, logout, analyze, pollResult, getHistory, getLatest
    └── __tests__/
        ├── api.test.ts
        ├── StateBanner.test.tsx
        ├── RiskBar.test.tsx
        ├── MetricsGrid.test.tsx
        └── InterventionPanel.test.tsx
```

---

## Task 1: Scaffold + API client + shared types

**Files:**
- Create: `frontend/` (full scaffold via `create-next-app`)
- Create: `frontend/lib/types.ts`
- Create: `frontend/lib/api.ts`
- Create: `frontend/lib/__tests__/api.test.ts`
- Create: `frontend/.env.local`
- Create: `frontend/jest.config.ts`
- Create: `frontend/jest.setup.ts`

- [ ] **Step 1: Scaffold Next.js app**

```bash
npx create-next-app@latest frontend \
  --typescript \
  --tailwind \
  --app \
  --no-src-dir \
  --import-alias '@/*' \
  --no-eslint
cd frontend
npm install recharts
npm install -D jest jest-environment-jsdom @testing-library/react \
  @testing-library/jest-dom @types/jest ts-jest
```

- [ ] **Step 2: Create `.env.local`**

`frontend/.env.local`:
```
NEXT_PUBLIC_API_URL=http://localhost:8000
```

- [ ] **Step 3: Create jest.config.ts**

`frontend/jest.config.ts`:
```typescript
import type { Config } from 'jest'

const config: Config = {
  testEnvironment: 'jsdom',
  setupFilesAfterFramework: ['<rootDir>/jest.setup.ts'],
  transform: {
    '^.+\\.(ts|tsx)$': ['ts-jest', { tsconfig: { jsx: 'react-jsx' } }],
  },
  moduleNameMapper: {
    '^@/(.*)$': '<rootDir>/$1',
    '\\.(css|scss)$': '<rootDir>/__mocks__/fileMock.js',
  },
  testPathPattern: 'lib/__tests__',
}

export default config
```

`frontend/jest.setup.ts`:
```typescript
import '@testing-library/jest-dom'
```

`frontend/__mocks__/fileMock.js`:
```javascript
module.exports = {}
```

- [ ] **Step 4: Write failing API tests**

Create `frontend/lib/__tests__/api.test.ts`:
```typescript
const API = 'http://localhost:8000'

beforeEach(() => {
  global.fetch = jest.fn()
})

afterEach(() => {
  jest.resetAllMocks()
})

function mockFetch(body: unknown, status = 200) {
  ;(global.fetch as jest.Mock).mockResolvedValueOnce({
    ok: status < 400,
    status,
    json: async () => body,
  })
}

describe('login', () => {
  it('posts credentials and returns user', async () => {
    mockFetch({ username: 'admin', is_admin: true })
    const { login } = await import('../api')
    const result = await login('admin', 'pass')
    expect(result).toEqual({ username: 'admin', is_admin: true })
    expect(global.fetch).toHaveBeenCalledWith(
      `${API}/auth/login`,
      expect.objectContaining({ method: 'POST', credentials: 'include' })
    )
  })

  it('throws on 401', async () => {
    mockFetch({ error: 'Invalid credentials' }, 401)
    const { login } = await import('../api')
    await expect(login('bad', 'bad')).rejects.toThrow('Invalid credentials')
  })
})

describe('analyze', () => {
  it('returns task_id', async () => {
    mockFetch({ task_id: 'abc-123' }, 202)
    const { analyze } = await import('../api')
    const result = await analyze({
      lat: 28.6, lon: 77.2, location_name: 'Delhi',
      env_weather_risk: 0, env_width_factor: 1, env_event_active: false,
    })
    expect(result.task_id).toBe('abc-123')
  })
})

describe('pollResult', () => {
  it('returns pending when not ready', async () => {
    mockFetch({ status: 'pending', task_id: 'xyz' })
    const { pollResult } = await import('../api')
    const result = await pollResult('xyz')
    expect(result.status).toBe('pending')
  })
})

describe('getHistory', () => {
  it('returns array', async () => {
    mockFetch([{ id: 1, state: 'Stable' }])
    const { getHistory } = await import('../api')
    const result = await getHistory()
    expect(Array.isArray(result)).toBe(true)
  })
})
```

- [ ] **Step 5: Run tests to verify they fail**

```bash
cd frontend && npx jest lib/__tests__/api.test.ts
```

Expected: FAIL — `Cannot find module '../api'`

- [ ] **Step 6: Write lib/types.ts**

`frontend/lib/types.ts`:
```typescript
export interface Breakdown {
  state_info?: { summary: string; label: string; severity: number; color: string }
  risk_score?: {
    value: number
    verdict: string
    formula: string
    rating: 'safe' | 'watch' | 'warning' | 'critical'
  }
  compression_gradient?: { rating: string; verdict: string }
  velocity_variance?: { rating: string; verdict: string }
  anomaly_score?: { rating: string; verdict: string }
  confidence?: { penalties: string[]; bonuses: string[]; verdict: string }
  environment?: { verdict: string }
}

export interface InterventionAction {
  priority: string
  action: string
  owner: string
  outcome: string
}

export interface Interventions {
  level: string
  pastel_bg: string
  text_color: string
  border_color: string
  actions: InterventionAction[]
}

export interface AnalysisResult {
  status: 'done' | 'pending'
  task_id: string
  location: string
  timestamp: string
  state: string
  confidence: number
  risk_score: number
  congestion: number
  gradient: number
  velocity_var: number
  anomaly_score: number
  is_simulated: boolean
  breakdown: Breakdown
  interventions: Interventions
}

export interface HistoryRecord {
  id: number
  created_at: string
  location_name: string
  latitude: number
  longitude: number
  congestion: number
  speed: number | null
  gradient: number | null
  velocity_var: number | null
  anomaly_score: number | null
  risk_score: number | null
  state: string
  session_id: string | null
}

export interface AnalyzeParams {
  lat: number
  lon: number
  location_name: string
  env_weather_risk: number
  env_width_factor: number
  env_event_active: boolean
}
```

- [ ] **Step 7: Write lib/api.ts**

`frontend/lib/api.ts`:
```typescript
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
```

- [ ] **Step 8: Run tests**

```bash
cd frontend && npx jest lib/__tests__/api.test.ts
```

Expected: 5 tests pass.

- [ ] **Step 9: Commit**

```bash
cd frontend && git add . && cd .. && git add frontend/ && \
git commit -m "feat: Next.js scaffold, shared types, and typed API client"
```

---

## Task 2: Login page

**Files:**
- Modify: `frontend/app/layout.tsx`
- Modify: `frontend/app/globals.css`
- Modify: `frontend/app/page.tsx`
- Create: `frontend/app/login/page.tsx`

- [ ] **Step 1: Write failing test**

Create `frontend/lib/__tests__/LoginPage.test.tsx`:
```typescript
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import LoginPage from '@/app/login/page'

jest.mock('@/lib/api', () => ({
  login: jest.fn(),
}))

// mock next/navigation
const mockPush = jest.fn()
jest.mock('next/navigation', () => ({
  useRouter: () => ({ push: mockPush }),
}))

describe('LoginPage', () => {
  it('renders username and password fields', () => {
    render(<LoginPage />)
    expect(screen.getByPlaceholderText('Username')).toBeInTheDocument()
    expect(screen.getByPlaceholderText('Password')).toBeInTheDocument()
  })

  it('redirects to /dashboard on success', async () => {
    const { login } = await import('@/lib/api')
    ;(login as jest.Mock).mockResolvedValueOnce({ username: 'admin', is_admin: true })
    render(<LoginPage />)
    fireEvent.change(screen.getByPlaceholderText('Username'), { target: { value: 'admin' } })
    fireEvent.change(screen.getByPlaceholderText('Password'), { target: { value: 'cpseisawesome' } })
    fireEvent.click(screen.getByRole('button', { name: /sign in/i }))
    await waitFor(() => expect(mockPush).toHaveBeenCalledWith('/dashboard'))
  })

  it('shows error on 401', async () => {
    const { login } = await import('@/lib/api')
    ;(login as jest.Mock).mockRejectedValueOnce(new Error('Invalid credentials'))
    render(<LoginPage />)
    fireEvent.change(screen.getByPlaceholderText('Username'), { target: { value: 'bad' } })
    fireEvent.change(screen.getByPlaceholderText('Password'), { target: { value: 'bad' } })
    fireEvent.click(screen.getByRole('button', { name: /sign in/i }))
    await waitFor(() => expect(screen.getByText('Invalid credentials')).toBeInTheDocument())
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd frontend && npx jest lib/__tests__/LoginPage.test.tsx
```

Expected: FAIL — `Cannot find module '@/app/login/page'`

- [ ] **Step 3: Update app/layout.tsx**

`frontend/app/layout.tsx`:
```typescript
import type { Metadata } from 'next'
import { Inter } from 'next/font/google'
import './globals.css'

const inter = Inter({ subsets: ['latin'] })

export const metadata: Metadata = {
  title: 'CPSE | Crowd Psychology State Engine',
  description: 'Real-time crowd dynamics classification and risk analysis',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className={`${inter.className} bg-slate-50 text-slate-800`}>
        {children}
      </body>
    </html>
  )
}
```

- [ ] **Step 4: Update app/page.tsx (root redirect)**

`frontend/app/page.tsx`:
```typescript
import { redirect } from 'next/navigation'

export default function Home() {
  redirect('/login')
}
```

- [ ] **Step 5: Create app/login/page.tsx**

`frontend/app/login/page.tsx`:
```typescript
'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { login } from '@/lib/api'

export default function LoginPage() {
  const router = useRouter()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      await login(username, password)
      localStorage.setItem('cpse_user', username)
      router.push('/dashboard')
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Login failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center">
      <div className="w-full max-w-sm">
        <div className="text-center mb-8">
          <h1 className="text-2xl font-bold text-slate-800">CPSE</h1>
          <p className="text-sm text-slate-500 mt-1">Crowd Psychology State Engine</p>
        </div>

        <form onSubmit={handleSubmit} className="bg-white rounded-lg border border-slate-200 p-6 shadow-sm space-y-4">
          <div>
            <label className="block text-xs font-semibold text-slate-500 uppercase tracking-wider mb-1">
              Username
            </label>
            <input
              type="text"
              placeholder="Username"
              value={username}
              onChange={e => setUsername(e.target.value)}
              className="w-full border border-slate-200 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-slate-300"
              required
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-500 uppercase tracking-wider mb-1">
              Password
            </label>
            <input
              type="password"
              placeholder="Password"
              value={password}
              onChange={e => setPassword(e.target.value)}
              className="w-full border border-slate-200 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-slate-300"
              required
            />
          </div>

          {error && (
            <p className="text-sm text-red-600 bg-red-50 border border-red-200 rounded px-3 py-2">
              {error}
            </p>
          )}

          <button
            type="submit"
            disabled={loading}
            className="w-full bg-slate-800 text-white rounded-md py-2 text-sm font-semibold hover:bg-slate-700 disabled:opacity-50 transition-colors"
          >
            {loading ? 'Signing in…' : 'Sign In'}
          </button>
        </form>

        <p className="text-center text-xs text-slate-400 mt-4">
          Contact your administrator for access credentials.
        </p>
      </div>
    </div>
  )
}
```

- [ ] **Step 6: Run tests**

```bash
cd frontend && npx jest lib/__tests__/LoginPage.test.tsx
```

Expected: 3 passed.

- [ ] **Step 7: Verify login page renders in browser**

```bash
cd frontend && npm run dev
```

Open `http://localhost:3000` — should redirect to `/login` and show the login form.
Stop server with Ctrl+C.

- [ ] **Step 8: Commit**

```bash
cd .. && git add frontend/ && git commit -m "feat: login page with session cookie auth"
```

---

## Task 3: Dashboard shell + polling loop

**Files:**
- Create: `frontend/components/NavBar.tsx`
- Create: `frontend/app/dashboard/page.tsx`

- [ ] **Step 1: Create NavBar.tsx**

`frontend/components/NavBar.tsx`:
```typescript
'use client'

import { useRouter } from 'next/navigation'
import { logout } from '@/lib/api'
import Link from 'next/link'

export default function NavBar() {
  const router = useRouter()

  async function handleLogout() {
    try { await logout() } catch {}
    localStorage.removeItem('cpse_user')
    router.push('/login')
  }

  return (
    <nav className="bg-white border-b border-slate-200 px-6 py-3 flex items-center justify-between">
      <div className="flex items-center gap-6">
        <span className="font-bold text-slate-800 text-sm tracking-wide">CPSE</span>
        <Link href="/dashboard" className="text-sm text-slate-600 hover:text-slate-800">
          Dashboard
        </Link>
        <Link href="/history" className="text-sm text-slate-600 hover:text-slate-800">
          History
        </Link>
      </div>
      <button
        onClick={handleLogout}
        className="text-xs text-slate-500 hover:text-slate-800 transition-colors"
      >
        Sign out
      </button>
    </nav>
  )
}
```

- [ ] **Step 2: Create dashboard/page.tsx (polling shell)**

`frontend/app/dashboard/page.tsx`:
```typescript
'use client'

import { useState, useEffect, useRef } from 'react'
import { useRouter } from 'next/navigation'
import NavBar from '@/components/NavBar'
import { analyze, pollResult } from '@/lib/api'
import type { AnalysisResult, AnalyzeParams } from '@/lib/types'

const POLL_INTERVAL = 2000 // 2 s

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
  const [result, setResult] = useState<AnalysisResult | null>(null)
  const [taskId, setTaskId] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null)

  // Auth guard: redirect if no session
  useEffect(() => {
    if (!localStorage.getItem('cpse_user')) router.push('/login')
  }, [router])

  // Polling loop
  useEffect(() => {
    if (!taskId) return
    pollRef.current = setInterval(async () => {
      try {
        const r = await pollResult(taskId)
        if (r.status === 'done') {
          setResult(r)
          setLoading(false)
          clearInterval(pollRef.current!)
          setTaskId(null)
        }
      } catch {
        clearInterval(pollRef.current!)
        setError('Polling failed — result may not be available')
        setLoading(false)
      }
    }, POLL_INTERVAL)
    return () => clearInterval(pollRef.current!)
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

  return (
    <div className="min-h-screen bg-slate-50">
      <NavBar />
      <main className="max-w-7xl mx-auto px-6 py-6">
        <div className="flex items-start justify-between mb-6">
          <div>
            <h1 className="text-xl font-bold text-slate-800">Crowd Psychology State Engine</h1>
            <p className="text-sm text-slate-500">Real-time crowd dynamics classification & risk analysis</p>
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

        {/* Result area — raw JSON for now, replaced by components in Tasks 4–7 */}
        {loading && (
          <div className="text-sm text-slate-500 animate-pulse">Running analysis…</div>
        )}
        {result && (
          <pre className="text-xs bg-white border border-slate-200 rounded p-4 overflow-auto max-h-96">
            {JSON.stringify(result, null, 2)}
          </pre>
        )}
      </main>
    </div>
  )
}
```

- [ ] **Step 3: Verify dashboard loads**

```bash
cd frontend && npm run dev
```

1. Log in at `http://localhost:3000/login`
2. Should redirect to `/dashboard`
3. Fill in the form and click "Run Analysis"
4. The raw JSON result should appear in ~3 s (requires backend + Celery + Redis running)

Stop server with Ctrl+C.

- [ ] **Step 4: Commit**

```bash
cd .. && git add frontend/ && git commit -m "feat: dashboard shell with POST/poll loop, NavBar"
```

---

## Task 4: StateBanner + RiskBar

**Files:**
- Create: `frontend/components/StateBanner.tsx`
- Create: `frontend/components/RiskBar.tsx`
- Create: `frontend/lib/__tests__/StateBanner.test.tsx`
- Create: `frontend/lib/__tests__/RiskBar.test.tsx`
- Modify: `frontend/app/dashboard/page.tsx`

**State color map** (from app.py CSS):
```
Stable      → bg:#f0fdf4  border:#86efac  text:#15803d
Compressing → bg:#fffbeb  border:#fde68a  text:#b45309
Volatile    → bg:#fef2f2  border:#fecaca  text:#b91c1c
Agitated    → bg:#faf5ff  border:#ddd6fe  text:#6d28d9
Fragmenting → bg:#f0f9ff  border:#bae6fd  text:#0369a1
```

- [ ] **Step 1: Write failing tests**

`frontend/lib/__tests__/StateBanner.test.tsx`:
```typescript
import { render, screen } from '@testing-library/react'
import StateBanner from '@/components/StateBanner'

const props = {
  state: 'Stable',
  confidence: 0.87,
  summary: 'Normal crowd flow.',
}

describe('StateBanner', () => {
  it('renders state name uppercased', () => {
    render(<StateBanner {...props} />)
    expect(screen.getByText('STABLE')).toBeInTheDocument()
  })

  it('renders confidence as percentage', () => {
    render(<StateBanner {...props} />)
    expect(screen.getByText('87%')).toBeInTheDocument()
  })

  it('renders summary text', () => {
    render(<StateBanner {...props} />)
    expect(screen.getByText('Normal crowd flow.')).toBeInTheDocument()
  })
})
```

`frontend/lib/__tests__/RiskBar.test.tsx`:
```typescript
import { render, screen } from '@testing-library/react'
import RiskBar from '@/components/RiskBar'

describe('RiskBar', () => {
  it('renders score', () => {
    render(<RiskBar score={42} verdict="Moderate risk." formula="0.4G+0.3V" />)
    expect(screen.getByText('42/100')).toBeInTheDocument()
  })

  it('renders verdict', () => {
    render(<RiskBar score={42} verdict="Moderate risk." formula="0.4G+0.3V" />)
    expect(screen.getByText('Moderate risk.')).toBeInTheDocument()
  })
})
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd frontend && npx jest lib/__tests__/StateBanner.test.tsx lib/__tests__/RiskBar.test.tsx
```

Expected: FAIL — `Cannot find module '@/components/StateBanner'`

- [ ] **Step 3: Create StateBanner.tsx**

`frontend/components/StateBanner.tsx`:
```typescript
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
```

- [ ] **Step 4: Create RiskBar.tsx**

`frontend/components/RiskBar.tsx`:
```typescript
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
```

- [ ] **Step 5: Run tests**

```bash
cd frontend && npx jest lib/__tests__/StateBanner.test.tsx lib/__tests__/RiskBar.test.tsx
```

Expected: 5 passed.

- [ ] **Step 6: Wire components into dashboard/page.tsx**

Replace the raw JSON `<pre>` block in `frontend/app/dashboard/page.tsx` with:

```typescript
// Add these imports at the top of the file:
import StateBanner from '@/components/StateBanner'
import RiskBar from '@/components/RiskBar'

// Replace the result display section:
        {result && result.status === 'done' && (
          <div>
            <StateBanner
              state={result.state}
              confidence={result.confidence}
              summary={result.breakdown.state_info?.summary}
            />
            <RiskBar
              score={result.risk_score}
              verdict={result.breakdown.risk_score?.verdict}
              formula={result.breakdown.risk_score?.formula}
            />
          </div>
        )}
```

- [ ] **Step 7: Verify in browser**

```bash
cd frontend && npm run dev
```

Run an analysis — the state banner and risk bar should appear.
Stop server with Ctrl+C.

- [ ] **Step 8: Commit**

```bash
cd .. && git add frontend/ && git commit -m "feat: StateBanner and RiskBar components"
```

---

## Task 5: MetricsGrid

**Files:**
- Create: `frontend/components/MetricsGrid.tsx`
- Create: `frontend/lib/__tests__/MetricsGrid.test.tsx`
- Modify: `frontend/app/dashboard/page.tsx`

Each metric card shows:
- Label + value
- Criteria panel (key-value rows) with a colour-coded left border
- Verdict text

Rating → left-border colour:
- `safe`     → `#86efac`
- `watch`    → `#fde68a`
- `warning`  → `#fdba74`
- `critical` → `#fca5a5`

- [ ] **Step 1: Write failing test**

`frontend/lib/__tests__/MetricsGrid.test.tsx`:
```typescript
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
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd frontend && npx jest lib/__tests__/MetricsGrid.test.tsx
```

Expected: FAIL — `Cannot find module '@/components/MetricsGrid'`

- [ ] **Step 3: Create MetricsGrid.tsx**

`frontend/components/MetricsGrid.tsx`:
```typescript
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
          verdict={bd.compression_gradient?.verdict}
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
```

- [ ] **Step 4: Run tests**

```bash
cd frontend && npx jest lib/__tests__/MetricsGrid.test.tsx
```

Expected: 3 passed.

- [ ] **Step 5: Wire into dashboard/page.tsx**

Add import and wire below `<RiskBar>`:
```typescript
import MetricsGrid from '@/components/MetricsGrid'

// Add inside the result block, after RiskBar:
            <MetricsGrid result={result} />
```

- [ ] **Step 6: Commit**

```bash
cd .. && git add frontend/ && git commit -m "feat: MetricsGrid component with criteria panels"
```

---

## Task 6: Charts

**Files:**
- Create: `frontend/components/Charts.tsx`
- Modify: `frontend/app/dashboard/page.tsx`

**Charts to port from app.py:**
1. **Signal chart** (left column, 60% height): stacked area/line — congestion (area), gradient (dotted line) on top pane; velocity_var (area), anomaly_score (dashed line) + Z=2.5 threshold line on bottom pane → Use recharts `ComposedChart` with two separate charts stacked vertically
2. **Risk gauge** (right column, top): recharts `RadialBarChart` showing risk_score 0–100
3. **State distribution pie** (right column, bottom): recharts `PieChart` of state history counts

Charts receive the rolling history as a prop (array of past results kept in dashboard state).

Colors (from app.py):
```
congestion  → #7eb8da  (steel blue)
gradient    → #c4a35a  (warm gold)
velocity    → #a89ad4  (soft purple)
anomaly     → #d47a7a  (muted rose)
```

State palette:
```
Stable      → #86efac
Compressing → #fde68a
Volatile    → #fca5a5
Agitated    → #c4b5fd
Fragmenting → #bae6fd
```

- [ ] **Step 1: Create Charts.tsx**

`frontend/components/Charts.tsx`:
```typescript
'use client'

import {
  ComposedChart, Area, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, ReferenceLine, PieChart, Pie, Cell,
  RadialBarChart, RadialBar, Legend,
} from 'recharts'
import type { AnalysisResult } from '@/lib/types'

interface HistoryPoint {
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

  const tickFormatter = (t: string) => {
    try { return new Date(t).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }) }
    catch { return t }
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
                <ReferenceLine y={2.5} stroke="rgba(212,122,122,0.5)" strokeDasharray="3 3" label={{ value: 'Z=2.5', fill: '#d47a7a', fontSize: 10 }} />
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
                    label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
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
```

- [ ] **Step 2: Wire into dashboard/page.tsx**

Add to imports and state in `frontend/app/dashboard/page.tsx`:

```typescript
import Charts from '@/components/Charts'

// In the component, add history state (after result state):
  const [history, setHistory] = useState<Array<{
    time: string
    congestion: number
    gradient: number
    velocity_var: number
    anomaly_score: number
    state: string
  }>>([])

// In the polling useEffect, when result arrives (after setResult(r)):
          setHistory(prev => {
            const point = {
              time: r.timestamp,
              congestion: r.congestion,
              gradient: r.gradient,
              velocity_var: r.velocity_var,
              anomaly_score: r.anomaly_score,
              state: r.state,
            }
            return [...prev.slice(-59), point]  // keep last 60 points
          })

// Add inside the result block, after MetricsGrid:
            <Charts history={history} riskScore={result.risk_score} />
```

- [ ] **Step 3: Verify charts render**

```bash
cd frontend && npm run dev
```

Run 2+ analyses — charts should appear.
Stop server with Ctrl+C.

- [ ] **Step 4: Commit**

```bash
cd .. && git add frontend/ && git commit -m "feat: Charts component (signal history, risk gauge, state pie)"
```

---

## Task 7: InterventionPanel

**Files:**
- Create: `frontend/components/InterventionPanel.tsx`
- Create: `frontend/lib/__tests__/InterventionPanel.test.tsx`
- Modify: `frontend/app/dashboard/page.tsx`

- [ ] **Step 1: Write failing test**

`frontend/lib/__tests__/InterventionPanel.test.tsx`:
```typescript
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
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd frontend && npx jest lib/__tests__/InterventionPanel.test.tsx
```

Expected: FAIL — `Cannot find module '@/components/InterventionPanel'`

- [ ] **Step 3: Create InterventionPanel.tsx**

`frontend/components/InterventionPanel.tsx`:
```typescript
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
```

- [ ] **Step 4: Run tests**

```bash
cd frontend && npx jest lib/__tests__/InterventionPanel.test.tsx
```

Expected: 3 passed.

- [ ] **Step 5: Wire into dashboard/page.tsx**

Add import and wire below Charts:
```typescript
import InterventionPanel from '@/components/InterventionPanel'

// Add inside result block, after Charts:
            <div className="mt-6">
              <InterventionPanel plan={result.interventions} />
            </div>
```

- [ ] **Step 6: Run full test suite**

```bash
cd frontend && npx jest
```

Expected: all tests pass.

- [ ] **Step 7: Commit**

```bash
cd .. && git add frontend/ && git commit -m "feat: InterventionPanel component with action cards"
```

---

## Task 8: History page

**Files:**
- Create: `frontend/app/history/page.tsx`

The history page:
- Calls `GET /history?limit=N&location=L&anomaly_only=true/false`
- Shows 4 KPI cards: total records, avg congestion, anomaly count, dominant state
- Shows a recharts `LineChart` of congestion over time (when single location selected)
- Shows a sortable table of all records
- Has a CSV download button

- [ ] **Step 1: Create history/page.tsx**

`frontend/app/history/page.tsx`:
```typescript
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

  useEffect(() => {
    if (!localStorage.getItem('cpse_user')) router.push('/login')
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

  useEffect(() => { fetchRecords() }, [fetchRecords])

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

  // Chart data (sorted ascending)
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
```

- [ ] **Step 2: Verify in browser**

```bash
cd frontend && npm run dev
```

1. Log in → Dashboard → History (via NavBar link)
2. Should load records from the backend (requires at least one analysis having been run)

Stop server with Ctrl+C.

- [ ] **Step 3: Commit**

```bash
cd .. && git add frontend/ && git commit -m "feat: history page with KPI cards, trend chart, and table"
```

---

## Task 9: End-to-end smoke test

Prerequisites: backend running at `http://localhost:8000` with Redis + Celery worker active. Use the curl commands from Task 11 of the backend plan (or the Django dev server).

- [ ] **Step 1: Start backend services**

```bash
# Terminal 1
redis-server --daemonize yes

# Terminal 2
cd backend && source venv/bin/activate && celery -A core worker --loglevel=info

# Terminal 3
cd backend && source venv/bin/activate && python manage.py runserver
```

- [ ] **Step 2: Start frontend dev server**

```bash
# Terminal 4
cd frontend && npm run dev
```

- [ ] **Step 3: Login flow**

1. Open `http://localhost:3000`
2. Should redirect to `/login`
3. Enter `admin` / `cpseisawesome`
4. Should redirect to `/dashboard`

Expected: redirected to dashboard, no console errors.

- [ ] **Step 4: Analysis flow**

1. On dashboard, verify default location (Delhi, 28.6139, 77.2090)
2. Click "Run Analysis"
3. Button shows "Analysing…" while polling
4. Within ~5 s: StateBanner appears with a state (e.g. "STABLE"), confidence percentage, and RiskBar
5. MetricsGrid shows all 4 metrics with criteria panels
6. After 2+ analyses: Charts appear (signal history, risk gauge, state distribution pie)
7. InterventionPanel shows action cards

Expected: no console errors, no "polling failed" message.

- [ ] **Step 5: History flow**

1. Click "History" in NavBar
2. Records table should show entries from the analyses run in Step 4
3. Type "Delhi" in Location filter and click Refresh
4. Trend chart should appear
5. Click "Download CSV" — file downloads

Expected: records present, chart visible, CSV downloads.

- [ ] **Step 6: Logout flow**

1. Click "Sign out" in NavBar
2. Should redirect to `/login`
3. Navigating directly to `/dashboard` should redirect back to `/login`

Expected: session cleared, auth guard works.

- [ ] **Step 7: Run full test suite**

```bash
cd frontend && npx jest
```

Expected: all tests pass.

- [ ] **Step 8: Build check**

```bash
cd frontend && npm run build
```

Expected: no TypeScript errors, build completes.

- [ ] **Step 9: Final commit**

```bash
cd .. && git add frontend/ && git commit -m "chore: frontend smoke test verified — login, dashboard, history, logout all pass"
git push origin feat/django-restructure
```

---

## Self-Review

### Spec coverage

| CLAUDE.md requirement | Task |
|---|---|
| `app/login/page.tsx` — login page | Task 2 |
| `app/page.tsx` — redirect | Task 2 |
| `app/history/page.tsx` — history page | Task 8 |
| `app/dashboard/page.tsx` — POST → poll → render | Task 3 |
| `components/StateBanner` | Task 4 |
| `components/RiskBar` | Task 4 |
| `components/MetricsGrid` | Task 5 |
| `components/Charts` (recharts, no Plotly) | Task 6 |
| `components/InterventionPanel` | Task 7 |
| `lib/api.ts` typed API client | Task 1 |
| Auth via session cookie (`credentials: 'include'`) | Task 1 |
| Poll `/result/{task_id}` every 2 s | Task 3 |
| History page: filter + KPI + trend chart + table | Task 8 |
| NavBar with logout | Task 3 |

### Gaps (acceptable for this plan)

- **Location geocoder** (TomTom search → select): not included. Users enter lat/lon manually. Can be added as a follow-up task.
- **Live weather fetch on frontend**: weather risk is set via slider. The backend `env_weather_risk` param handles it.
- **`AnalysisTask` write** in pipeline: backend plan note already flags this. Doesn't affect frontend.
- **CORS `SESSION_COOKIE_SAMESITE`**: `Lax` means same-site requests work; cross-site (different port in dev) requires `None` + HTTPS or `CORS_ALLOW_ALL_ORIGINS = True` in dev. This is already configured in `core/settings/dev.py`.
