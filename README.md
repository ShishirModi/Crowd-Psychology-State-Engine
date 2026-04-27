# Crowd Psychology State Engine (CPSE)

Real-time crowd dynamics classification and risk analysis. CPSE ingests aggregate telemetry — traffic flows, congestion indices, and weather — to compute crowd state, anomaly scores, composite risk, and structured intervention plans. No PII, no cameras.

---

## Architecture

```
Browser (Next.js)
    │  POST /analyze  →  GET /result/{task_id}  (polling)
    │  session cookie
Django + DRF
    │  enqueue
Celery Worker  ──writes──▶  Redis (results, state, weather cache)
    │  ORM
Supabase (PostgreSQL)   crowd_telemetry · analysis_task
```

Full diagram: [`ARCHITECTURE.md`](ARCHITECTURE.md)

---

## Stack

| Layer | Technology |
|---|---|
| Frontend | Next.js 16, TypeScript, Tailwind CSS, recharts |
| Backend | Django 4.2, Django REST Framework |
| Async | Celery 5, Redis |
| Database | Supabase (PostgreSQL via `psycopg2`) |
| Auth | Django session auth, seeded from `APP_PASSWORD` |
| Deployment | Gunicorn + Celery systemd units, Cloudflare Tunnel |

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
# fill in SUPABASE_DB_URL, REDIS_URL, DJANGO_SECRET_KEY, API keys
```

### 2. Backend

```bash
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_users   # creates users from APP_PASSWORD
python manage.py runserver    # http://localhost:8000
```

### 3. Celery worker (separate terminal)

```bash
cd backend
source venv/bin/activate
celery -A core worker --loglevel=info
```

### 4. Frontend

```bash
cd frontend
npm install
# create frontend/.env.local with: NEXT_PUBLIC_API_URL=http://localhost:8000
npm run dev   # http://localhost:3000
```

Open `http://localhost:3000` → log in → run an analysis.

---

## API

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
backend/
├── core/           Django project (settings, urls, wsgi, celery)
├── api/            DRF views, serializers, auth
├── auth_app/       login/logout + seed_users command
├── tasks/          analyze_crowd Celery task
├── cache/          Redis key helpers, state serialization
├── models/         CrowdTelemetry (unmanaged), AnalysisTask ORM
└── services/
    ├── signals/    tomtom.py · weather.py · geocoder.py
    ├── metrics/    compression.py
    ├── engine/     classifier.py · anomaly.py
    ├── interventions/  recommender.py
    └── data_layer/ vectorizer.py · database.py

frontend/
├── app/            login/ · dashboard/ · history/
├── components/     NavBar · StateBanner · RiskBar · MetricsGrid
│                   Charts · InterventionPanel
└── lib/            types.ts · api.ts
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

`config.yaml` at project root controls API endpoints, simulation parameters, and metric thresholds. The backend loads it at startup via `backend/utils/config_loader.py`.

---

## Deployment

Production: Gunicorn serves Django; Celery runs as a systemd service; Cloudflare Tunnel (`cloudflared tunnel run cpse`) exposes both without opening firewall ports.

See `ARCHITECTURE.md` for the full deployment section.
