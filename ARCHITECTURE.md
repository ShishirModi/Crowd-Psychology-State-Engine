# ARCHITECTURE.md
## Crowd Psychology State Engine — System Architecture

---

## System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        BROWSER (Next.js)                        │
│  Login → Dashboard → POST /analyze → poll /result/{task_id}     │
└────────────────────────────┬────────────────────────────────────┘
                             │ HTTP + session cookie
┌────────────────────────────▼────────────────────────────────────┐
│                      DJANGO + DRF                               │
│  auth_app/   api/   → enqueues Celery task, serves results      │
└──────────┬───────────────────────────────────┬──────────────────┘
           │ task dispatch                     │ Redis reads
┌──────────▼──────────┐             ┌──────────▼──────────────────┐
│    CELERY WORKER    │             │           REDIS              │
│  analyze_crowd()    │────writes──▶│  result:{id}  state:{loc}   │
│  full pipeline      │             │  last:{loc}   weather:{...} │
└──────────┬──────────┘             └─────────────────────────────┘
           │ ORM write
┌──────────▼──────────────────────────────────────────────────────┐
│                  SUPABASE (PostgreSQL)                          │
│          crowd_telemetry        analysis_task                   │
└─────────────────────────────────────────────────────────────────┘
```

---

## Request Lifecycle

```
Client                Django              Redis           Celery Worker         Supabase
  │                     │                   │                  │                    │
  │── POST /analyze ───▶│                   │                  │                    │
  │                     │── enqueue task ──▶│                  │                    │
  │◀─ { task_id } ──────│                   │                  │                    │
  │                     │                   │◀── pick up ──────│                    │
  │── GET /result/{id} ▶│                   │                  │                    │
  │◀─ { status: pending}│                   │   load state ───▶│                    │
  │   (poll every 2s)   │                   │◀─ state blob ────│                    │
  │                     │                   │                  │── run pipeline ──▶ │
  │                     │                   │                  │◀─ (ok) ───────────│
  │                     │                   │◀─ write result ──│                    │
  │                     │                   │◀─ write state ───│                    │
  │── GET /result/{id} ▶│                   │                  │                    │
  │                     │── read result ───▶│                  │                    │
  │◀─ { status: done,   │◀─ result JSON ────│                  │                    │
  │    payload: {...} } │                   │                  │                    │
```

---

## Backend — Component Map

### `backend/core/`
Django project package. Contains `settings/`, `urls.py`, `wsgi.py`, `celery.py`.
Settings split into `base.py` (shared), `dev.py` (DEBUG=True, SQLite allowed),
`prod.py` (Gunicorn, ALLOWED_HOSTS, secure cookies).

---

### `backend/api/`
DRF views and serializers. No business logic — thin adapter between HTTP and services/tasks.

| Endpoint | Method | Handler | Notes |
|---|---|---|---|
| `/auth/login` | POST | `AuthView.login` | Django `authenticate()` + `login()` |
| `/auth/logout` | POST | `AuthView.logout` | `logout()` + session flush |
| `/analyze` | POST | `AnalyzeView.post` | Validates payload, calls `analyze_crowd.delay()`, returns `task_id` |
| `/result/{task_id}` | GET | `ResultView.get` | Reads `cpse:result:{task_id}` from Redis; 404 if absent |
| `/history` | GET | `HistoryView.get` | Paginated query on `CrowdTelemetry` ORM |
| `/latest` | GET | `LatestView.get` | Reads `cpse:last:{location}` from Redis |

**Analyze request payload:**
```json
{
  "lat": 28.6139,
  "lon": 77.2090,
  "location_name": "Delhi City Center",
  "env_weather_risk": 0.0,
  "env_width_factor": 1.0,
  "env_event_active": false
}
```

**Result response payload (on completion):**
```json
{
  "status": "done",
  "task_id": "abc-123",
  "location": "Delhi City Center",
  "timestamp": "2026-04-27T10:00:00Z",
  "state": "Compressing",
  "confidence": 0.82,
  "risk_score": 38.4,
  "congestion": 0.612,
  "gradient": 0.491,
  "velocity_var": 0.18,
  "anomaly_score": 1.2,
  "breakdown": { ... },
  "interventions": { ... }
}
```

---

### `backend/tasks/analysis.py` — `analyze_crowd`

The single Celery task. Orchestrates the full pipeline.

```
analyze_crowd(lat, lon, location_name, env_params, task_id)
    │
    ├─ 1. load_state(location_name)          ← Redis: cpse:state:{location}
    │       returns CrowdMetrics + AnomalyDetector (or fresh instances)
    │
    ├─ 2. TomTomSignal.fetch_telemetry()     ← TomTom API or simulation
    │       → { congestion, current_speed, is_simulated }
    │
    ├─ 3. CrowdMetrics.update(congestion, speed)
    │
    ├─ 4. CrowdMetrics.compute_compression_gradient()
    │       → (gradient, fit_quality, gradient_details)
    │
    ├─ 5. CrowdMetrics.compute_velocity_variance()
    │       → (velocity_var, vv_details)
    │
    ├─ 6. CrowdStateVectorizer.create_state_vector(congestion, velocity_var, gradient)
    │       → np.array([density, turbulence, pressure, time_factor])
    │
    ├─ 7. AnomalyDetector.update_and_detect(vector)
    │       → (is_anomaly, anomaly_score, anomaly_details)
    │
    ├─ 8. CrowdClassifier.classify(gradient, velocity_var, anomaly_score, **env_params)
    │       → (state, confidence, breakdown)
    │
    ├─ 9. InterventionRecommender.get_recommendations(state)
    │       → { level, actions[] }
    │
    ├─ 10. save_state(location_name, metrics, detector)  ← Redis: cpse:state:{location}
    │
    ├─ 11. CrowdTelemetry.objects.create(...)            ← Supabase write
    │
    └─ 12. store_result(task_id, location_name, payload) ← Redis: cpse:result:{task_id}
                                                                    cpse:last:{location}
```

---

### `backend/cache/result_store.py`

Owns all Redis key patterns and state serialization.

**Key schema:**

| Key | TTL | Value |
|---|---|---|
| `cpse:result:{task_id}` | 1h | Full result JSON (string) |
| `cpse:last:{location}` | 24h | Latest result JSON for location |
| `cpse:state:{location}` | 24h | Pickled `CrowdMetrics` + `AnomalyDetector` state |
| `cpse:weather:{lat}:{lon}` | 10m | Cached OpenWeatherMap response |

**State serialization:** `CrowdMetrics` exposes `congestion_history` and `speed_history`
as `deque` objects. `AnomalyDetector` exposes `history` as `deque` and `_cycle` as int.
State is serialized to JSON (lists of floats) — not pickle — for forward compatibility.

**Concurrency guard:** Before writing state back, the task acquires
`cpse:lock:{location}` (Redis `SET NX EX 30`). If the lock is held, the task
retries after 1s (max 3 retries). This prevents two concurrent tasks for the same
location from racing on state writes.

---

### `backend/services/` — Service Classes

All service classes are ported from the existing codebase with **no logic changes**
during migration. They are plain Python — no Django or Celery imports.

#### `signals/tomtom.py` — `TomTomSignal`
Fetches traffic flow data from TomTom Flow Segment API.
Falls back to `_simulate_telemetry()` when API key absent or request fails.

| Config key | Value |
|---|---|
| Base URL | `https://api.tomtom.com/traffic/services/4/flowSegmentData` |
| Zoom level | 10 (city level) |
| Units | KMPH |
| Timeout | 5s |
| Congestion formula | `1 − (currentSpeed / freeFlowSpeed)` clamped to [0, 1] |

#### `signals/weather.py` — `OpenWeatherMapSignal`
Fetches current weather and maps OWM condition code to a risk float [0.0, 1.0].
Cache moves from `@st.cache_data` (Streamlit) to Redis key `cpse:weather:{lat}:{lon}` (TTL 10m).

| OWM Group | Risk |
|---|---|
| 2xx Thunderstorm | 1.0 |
| 3xx Drizzle | 0.3 |
| 500–501 Light/Mod Rain | 0.5 |
| 502+ Heavy Rain | 0.8 |
| 6xx Snow | 0.7 |
| 7xx Fog/Mist | 0.4 |
| 771 Squall | 0.9 |
| 781 Tornado | 1.0 |
| 800 Clear | 0.0 |
| 80x Clouds | 0.1 |

#### `signals/geocoder.py` — `TomTomGeocoder`
Wraps TomTom Search API. Used by the frontend location search only. Reuses the
same `TOMTOM_API_KEY`. Returns `[{ name, lat, lon }]`.

#### `metrics/compression.py` — `CrowdMetrics`
Maintains a 12-sample rolling window (≈60s at 5s intervals).

**Compression Gradient:**
- ≥5 samples: linear regression (`np.polyfit`), slope × 5 + current level
- <5 samples: finite difference (last − second-last)
- Formula: `0.6 × current_level + 0.4 × slope × 5`, clamped to [0, 1]
- Exposes R² fit quality for confidence penalty in classifier

**Velocity Variance:**
- CV = σ(speed) / μ(speed)
- Falls back to raw σ when μ < 1.0 km/h (near standstill)
- Thresholds: Negligible <0.10 | Mild <0.25 | Moderate <0.40 | Severe ≥0.40

#### `engine/classifier.py` — `CrowdClassifier`
Rule-based multi-factor classifier. Reads thresholds from `config.yaml`.

**State assignment (in priority order):**

| Rule | Condition | Outcome |
|---|---|---|
| Fragmentation | prev_gradient > 0.5 and Δgradient < −0.3 | Fragmenting |
| Primary (gradient) | gradient < 0.1 | Stable |
| Primary (gradient) | 0.1 ≤ gradient < 0.5 | Stable (transition) |
| Primary (gradient) | 0.5 ≤ gradient < 0.8 | Compressing |
| Primary (gradient) | 0.8 ≤ gradient < 0.95 | Volatile |
| Primary (gradient) | gradient ≥ 0.95 | Agitated |
| VV override | CV > 0.25 + state=Compressing | → Volatile |
| VV override | CV > 0.25 + state=Volatile | → Agitated |
| Anomaly override | Z > 2.5 + state=Stable/Compressing | append "(Anomaly Detected)" |
| Env override | env_penalty ≥ 0.10 + state=Compressing | → Volatile |

**Risk score formula:**
`0.35 × gradient + 0.25 × velocity_var + 0.20 × anomaly + 0.20 × environment` → 0–100

**Confidence penalties:**
- Simulated data: −20%
- History < 5 samples: −30%
- History 5–9 samples: −10%
- R² < 0.5: −20%
- R² 0.5–0.8: −10%
- R² > 0.95: +5%

#### `engine/anomaly.py` — `AnomalyDetector`
Rolling Z-score detector. History window: 100 samples. Calibration minimum: 20 samples.

- Vector structure: `[density, turbulence, pressure, time_factor]`
- Score: `max(|Xᵢ − μᵢ| / σᵢ)` across all features
- Threshold: Z > 2.5 = anomaly, Z > 4.0 = extreme outlier
- Inactive during calibration (returns score=0.0, is_anomaly=False)

#### `interventions/recommender.py` — `InterventionRecommender`
Maps state → response level + prioritised action list.

| State | Level | Highest Priority |
|---|---|---|
| Stable | ROUTINE | Low |
| Compressing | ADVISORY | Medium |
| Volatile | URGENT | Critical |
| Agitated | EMERGENCY | Critical |
| Fragmenting | CAUTION | High |

#### `data_layer/vectorizer.py` — `CrowdStateVectorizer`
Transforms raw telemetry into normalised numpy vectors for the anomaly detector.

| Feature | Source | Normalisation |
|---|---|---|
| density | congestion | clip [0, 1] |
| turbulence | velocity_var | ÷ 5.0, clip [0, 1] |
| pressure | gradient | clip [−1, 1] |
| time_factor | wall clock | seconds_in_day ÷ 86400 |

#### `data_layer/database.py` — Supabase client
Wraps `psycopg2` direct connection to Supabase PostgreSQL.
Django app server uses `SUPABASE_DB_URL` (direct connection, `CONN_MAX_AGE=60`).
Celery workers use the pooler URL (Transaction mode) to avoid exhausting connections.

---

### `backend/models/`

#### `CrowdTelemetry`
Maps to existing `crowd_telemetry` table. Django ORM with `managed=False` to avoid
re-creating the table (schema already exists in Supabase).

| Column | Type | Notes |
|---|---|---|
| id | SERIAL PK | auto |
| created_at | TIMESTAMPTZ | DEFAULT NOW() |
| location_name | TEXT | indexed |
| latitude | DOUBLE PRECISION | |
| longitude | DOUBLE PRECISION | |
| congestion | DOUBLE PRECISION | |
| speed | DOUBLE PRECISION | |
| gradient | DOUBLE PRECISION | |
| velocity_var | DOUBLE PRECISION | |
| anomaly_score | DOUBLE PRECISION | |
| risk_score | DOUBLE PRECISION | |
| state | TEXT | |
| session_id | TEXT | nullable |

#### `AnalysisTask`
New table. Tracks task lifecycle and optionally snapshots the result.

| Column | Type | Notes |
|---|---|---|
| task_id | UUID PK | Celery task id |
| created_at | TIMESTAMPTZ | |
| status | TEXT | pending / running / done / failed |
| location_name | TEXT | |
| result_json | JSONB | nullable — fallback if Redis flushes |

---

## Frontend — Component Map

```
app/
├── login/page.tsx
│     POST /auth/login → set session cookie → redirect /
│
├── page.tsx (Dashboard)
│     ├── useAnalysis() hook
│     │     POST /analyze → task_id
│     │     poll GET /result/{task_id} every 2s until status=done
│     │
│     ├── <StateBanner state confidence summary />
│     ├── <RiskBar score />
│     ├── <MetricsGrid congestion gradient velocityVar anomalyScore />
│     ├── <EnvironmentPanel weather width event />
│     ├── <Charts history />         ← recharts LineChart / AreaChart
│     ├── <InterventionPanel plan />
│     └── <LocationMap lat lon />    ← react-leaflet or next/image static map
│
└── history/page.tsx
      GET /history?location=&limit=&anomaly_only=
      ├── <FilterBar />
      ├── <KPIRow totalRecords avgCongestion anomalies dominantState />
      ├── <TrendChart />             ← only for single-location filter
      └── <DataTable />
```

**API client (`lib/api.ts`):**
Typed wrapper around `fetch`. Sends credentials (session cookie) on all requests.
Throws on non-2xx. Exposes: `login`, `logout`, `analyze`, `pollResult`, `getHistory`, `getLatest`.

---

## Configuration

**`config.yaml`** — service-level config (thresholds, API URLs, simulation flag).
Read by `utils/config_loader.py` (`get_config()` is `@lru_cache`). Both Django and
Celery workers resolve this from the project root.

**`.env`** — secrets and infrastructure URLs. Never committed.

```
DJANGO_SECRET_KEY=
SUPABASE_DB_URL=             # direct connection, used by Django ORM
SUPABASE_POOLER_URL=         # transaction pooler, used by Celery workers
REDIS_URL=
TOMTOM_API_KEY=
OPENWEATHERMAP_API_KEY=
APP_PASSWORD=                # first entry = admin, rest = viewer
```

---

## Crowd State Model

```
Severity →  0          1             2            2            3
           Stable → Compressing → Volatile ← Fragmenting ← Agitated
                         ↑              ↑
                    VV override    env override
                    (CV > 0.25)   (penalty ≥ 0.10)

Fragmentation: detected when gradient drops > 0.3 from a previously elevated state.
Escalation overrides are one-way — they never de-escalate state.
```

---

## Dependency Graph (backend)

```
analyze_crowd (Celery task)
    ├── TomTomSignal          ← requests, config.yaml
    ├── CrowdMetrics          ← numpy, deque  [stateful — Redis]
    ├── CrowdStateVectorizer  ← numpy
    ├── AnomalyDetector       ← numpy, deque  [stateful — Redis]
    ├── CrowdClassifier       ← config.yaml
    ├── InterventionRecommender
    ├── result_store          ← redis-py
    └── CrowdTelemetry ORM   ← psycopg2 → Supabase
```

---

## Python Packages

| Package | Role |
|---|---|
| `django>=4.2` | web framework |
| `djangorestframework` | API layer |
| `celery[redis]` | async task queue |
| `redis` | Redis client |
| `django-cors-headers` | CORS for Next.js dev origin |
| `psycopg2-binary` | PostgreSQL driver (Supabase) |
| `requests` | TomTom + OWM HTTP calls |
| `numpy` | metrics and anomaly math |
| `pyyaml` | config.yaml parsing |
| `python-dotenv` | .env loading |
| `timezonefinder`, `pytz` | local time for telemetry timestamps |

**Removed:** `streamlit`, `plotly`, `pandas` (moved to frontend)

## Node Packages (frontend)

| Package | Role |
|---|---|
| `next` | React framework + routing |
| `react`, `react-dom` | UI |
| `recharts` | charts (replaces Plotly) |
| `react-leaflet` | location map |
| `tailwindcss` | styling |
