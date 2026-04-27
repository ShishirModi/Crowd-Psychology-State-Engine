# Crowd Psychology State Engine (CPSE)

Real-time crowd dynamics classification and risk analysis. CPSE ingests aggregate telemetry — traffic flows, congestion indices, and weather — to compute crowd state, anomaly scores, composite risk, and structured intervention plans. No PII, no cameras.

---

## Architecture

```
Browser / Cloudflare Tunnel
        │  HTTPS → :3000
  Next.js (public)
        │  server-side rewrites for API paths
        │  /auth/*  /analyze  /result/*  /history  /latest
  Django :8000 (localhost only, never exposed)
        │  enqueue
  Celery Worker ──writes──▶ Redis (results · state · weather cache)
        │  ORM
  Supabase (PostgreSQL)   crowd_telemetry · analysis_task
```

`app.py` at the project root manages both Django and Next.js as subprocesses.
Cloudflare Tunnel points to port 3000 only.

Full diagram: [`ARCHITECTURE.md`](ARCHITECTURE.md)

---

## Stack

| Layer | Technology |
|---|---|
| Entry point | `app.py` — subprocess manager (Django + Next.js) |
| Frontend | Next.js 16, TypeScript, Tailwind CSS, recharts |
| Backend | Django 4.2, Django REST Framework |
| Async | Celery 5, Redis |
| Database | Supabase (PostgreSQL via `psycopg2`) |
| Auth | Django session auth, seeded from `APP_PASSWORD` |
| Deployment | `app.py` (dev) · Gunicorn + `next start` systemd units (prod), Cloudflare Tunnel → :3000 |

---

## Crowd States

| State | Description |
|---|---|
| **Stable** | Normal flow, low density gradient, calm |
| **Compressing** | Density rising, compression gradient climbing |
| **Volatile** | High velocity variance — stop-and-go shockwaves |
| **Agitated** | Multi-factor alert; anomaly + compression + turbulence |
| **Fragmenting** | Dispersal pattern — crowd splitting into streams |

---

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 20+
- Redis
- Supabase project (or any PostgreSQL DB)

### 1. Environment

```bash
cp .env.example .env
# fill in SUPABASE_DB_URL, REDIS_URL, DJANGO_SECRET_KEY, APP_PASSWORD, API keys
```

### 2. Install dependencies

```bash
# Backend
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_users   # creates users from APP_PASSWORD

# Frontend
cd ../frontend
npm install
```

### 3. Start everything

```bash
# From project root (development)
python app.py
```

This starts Django on `:8000` (internal) and Next.js on `:3000` (public).
Open `http://localhost:3000` → log in → run an analysis.

### 4. Celery worker (separate terminal)

```bash
cd backend && source venv/bin/activate
celery -A core worker --loglevel=info
```

### Running components separately

If you prefer to run without `app.py`:

```bash
# Django
cd backend && python manage.py runserver

# Next.js (in another terminal)
cd frontend && npm run dev
```

When running separately, add `DJANGO_INTERNAL_URL=http://localhost:8000` to
`frontend/.env.local` so Next.js rewrites can reach Django.

---

## API

All paths below are served through Next.js rewrites — the browser never connects directly to Django.

| Method | Path | Description |
|---|---|---|
| `POST` | `/auth/login` | Session login (`{username, password}`) |
| `POST` | `/auth/logout` | Clear session |
| `POST` | `/analyze` | Queue analysis → `{task_id}` |
| `GET` | `/result/{task_id}` | Poll result from Redis |
| `GET` | `/history` | Paginated telemetry (`?limit=&location=&anomaly_only=`) |
| `GET` | `/latest` | Latest result per location (`?location=`) |

---

## Project Structure

```
app.py                  ← single entry point: starts Django + Next.js
backend/
├── core/               Django project (settings/, urls.py, wsgi.py, celery.py)
├── api/                DRF views, serializers, auth
├── auth_app/           login/logout + seed_users management command
├── tasks/              analyze_crowd Celery task
├── cache/              Redis key helpers, state serialization
├── models/             CrowdTelemetry (unmanaged), AnalysisTask ORM
└── services/
    ├── signals/        tomtom.py · weather.py · geocoder.py
    ├── metrics/        compression.py
    ├── engine/         classifier.py · anomaly.py
    ├── interventions/  recommender.py
    └── data_layer/     vectorizer.py · database.py

frontend/
├── next.config.ts      API rewrites → Django internal URL
├── app/                login/ · dashboard/ · history/
├── components/         NavBar · StateBanner · RiskBar · MetricsGrid
│                       Charts · InterventionPanel
└── lib/                types.ts · api.ts (relative-URL fetch client)
```

---

## Redis Key Schema

| Key | TTL | Contents |
|---|---|---|
| `cpse:result:{task_id}` | 1 h | Full analysis result JSON |
| `cpse:last:{location}` | 24 h | Latest result per location |
| `cpse:state:{location}` | 24 h | Serialized CrowdMetrics + AnomalyDetector state |
| `cpse:weather:{lat}:{lon}` | 10 min | Cached weather API response |
| `cpse:lock:{location}` | 30 s | Per-location concurrency lock |

---

## Configuration

`config.yaml` at project root controls API endpoints, simulation parameters, and metric
thresholds. The backend loads it at startup via `backend/utils/config_loader.py`.

---

## Deployment

```bash
# Production mode — Gunicorn + next start
APP_ENV=prod python app.py
```

Or as separate systemd units (Gunicorn, Celery, Next.js), with Cloudflare Tunnel
pointing to `http://localhost:3000`.

```bash
cloudflared tunnel run cpse
```

See `ARCHITECTURE.md` for the full deployment section.
