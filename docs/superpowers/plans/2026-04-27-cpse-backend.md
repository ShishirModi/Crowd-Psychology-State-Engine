# CPSE Backend Restructure Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Migrate CPSE from a Streamlit monolith to a Django + DRF + Celery backend that exposes a REST API consumed by a Next.js frontend.

**Architecture:** Django handles HTTP (auth, API endpoints). Celery workers run the full analysis pipeline asynchronously. Per-location rolling state (`CrowdMetrics`, `AnomalyDetector`) is serialized to/from Redis between task invocations. Results go to Redis (`cpse:result:{task_id}`) and Supabase PostgreSQL. The existing service layer is moved into `backend/services/` with minimal changes — only two files require modification (remove Streamlit, update DB connection).

**Tech Stack:** Django 4.2, djangorestframework, celery[redis] 5.3, redis-py, psycopg2-binary, dj-database-url, pytest-django

---

## Scope Note

This plan is **backend only**. Frontend (Next.js) is a separate plan: `2026-04-27-cpse-frontend.md`.

---

## File Map

**Created:**
```
backend/
├── manage.py
├── requirements.txt
├── pytest.ini
├── core/
│   ├── __init__.py           ← exports celery_app
│   ├── celery.py             ← Celery app definition
│   ├── settings/
│   │   ├── __init__.py
│   │   ├── base.py           ← all shared settings
│   │   └── dev.py            ← DEBUG=True, CORS open
│   ├── urls.py               ← root URL dispatch
│   └── wsgi.py
├── api/
│   ├── __init__.py
│   ├── apps.py
│   ├── models.py             ← CrowdTelemetry (managed=False) + AnalysisTask
│   ├── serializers.py        ← DRF serializers
│   ├── views.py              ← HistoryView, LatestView, AnalyzeView, ResultView
│   ├── urls.py
│   └── migrations/
│       └── 0001_initial.py   ← auto-generated, only creates analysis_task
├── auth_app/
│   ├── __init__.py
│   ├── apps.py
│   ├── views.py              ← LoginView, LogoutView
│   ├── urls.py
│   └── management/commands/
│       └── seed_users.py     ← seeds users from APP_PASSWORD env var
├── tasks/
│   ├── __init__.py
│   └── analysis.py           ← analyze_crowd Celery task + _run_pipeline()
├── cache/
│   ├── __init__.py
│   └── result_store.py       ← Redis key helpers + state serialization
├── services/                 ← ported from project root (see below)
│   ├── signals/tomtom.py
│   ├── signals/weather.py    ← modified: remove @st.cache_data
│   ├── signals/geocoder.py
│   ├── metrics/compression.py
│   ├── engine/classifier.py
│   ├── engine/anomaly.py
│   ├── interventions/recommender.py
│   └── data_layer/
│       ├── vectorizer.py
│       └── database.py       ← modified: SUPABASE_DB_URL, remove Neon/Streamlit
└── utils/
    ├── config_loader.py      ← modified: absolute path to config.yaml
    ├── time_helper.py
    └── security.py
```

**Modified (project root):** none — original files preserved until migration verified.

---

## Task 1: Create backend directory and requirements

**Files:**
- Create: `backend/requirements.txt`
- Create: `backend/pytest.ini`

- [ ] **Step 1: Create backend/ and requirements.txt**

```bash
mkdir -p backend
```

`backend/requirements.txt`:
```
django>=4.2,<5.0
djangorestframework>=3.14
celery[redis]>=5.3
redis>=5.0
django-cors-headers>=4.0
psycopg2-binary>=2.9
dj-database-url>=2.0
requests>=2.28
numpy>=1.23
pyyaml>=6.0
python-dotenv>=1.0
timezonefinder>=6.0
pytz>=2023.3
pytest>=7.4
pytest-django>=4.7
```

- [ ] **Step 2: Install**

```bash
cd backend && pip install -r requirements.txt
```

Expected: all packages install without errors.

- [ ] **Step 3: Create pytest.ini**

`backend/pytest.ini`:
```ini
[pytest]
DJANGO_SETTINGS_MODULE = core.settings.dev
python_files = test_*.py
python_classes = Test*
python_functions = test_*
```

- [ ] **Step 4: Commit**

```bash
git add backend/requirements.txt backend/pytest.ini
git commit -m "chore: add backend requirements and pytest config"
```

---

## Task 2: Django project skeleton

**Files:**
- Create: `backend/manage.py`
- Create: `backend/core/__init__.py`
- Create: `backend/core/celery.py`
- Create: `backend/core/settings/__init__.py`
- Create: `backend/core/settings/base.py`
- Create: `backend/core/settings/dev.py`
- Create: `backend/core/urls.py`
- Create: `backend/core/wsgi.py`
- Create: `backend/api/__init__.py`, `backend/api/apps.py`, `backend/api/models.py`, `backend/api/views.py`, `backend/api/urls.py`
- Create: `backend/auth_app/__init__.py`, `backend/auth_app/apps.py`, `backend/auth_app/views.py`, `backend/auth_app/urls.py`

- [ ] **Step 1: Write manage.py**

`backend/manage.py`:
```python
#!/usr/bin/env python
import os
import sys

def main():
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings.dev')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError("Couldn't import Django.") from exc
    execute_from_command_line(sys.argv)

if __name__ == '__main__':
    main()
```

- [ ] **Step 2: Write core/settings/base.py**

`backend/core/settings/base.py`:
```python
from pathlib import Path
import os
import dj_database_url
from dotenv import load_dotenv

# Load .env from project root (one level above backend/)
load_dotenv(Path(__file__).resolve().parent.parent.parent.parent / '.env')

BASE_DIR = Path(__file__).resolve().parent.parent.parent  # backend/
ROOT_DIR = BASE_DIR.parent                                 # project root

SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', 'dev-insecure-key-change-in-prod')
DEBUG = False
ALLOWED_HOSTS: list[str] = []

INSTALLED_APPS = [
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'rest_framework',
    'corsheaders',
    'api',
    'auth_app',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
]

ROOT_URLCONF = 'core.urls'
WSGI_APPLICATION = 'core.wsgi.application'

_db_url = os.environ.get('SUPABASE_DB_URL', '')
if _db_url:
    DATABASES = {'default': dj_database_url.parse(_db_url)}
    DATABASES['default']['CONN_MAX_AGE'] = 60
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

CELERY_BROKER_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
CELERY_RESULT_BACKEND = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_ACCEPT_CONTENT = ['json']

SESSION_ENGINE = 'django.contrib.sessions.backends.db'
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
}

CORS_ALLOW_CREDENTIALS = True
CORS_ALLOWED_ORIGINS: list[str] = []
REDIS_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
```

- [ ] **Step 3: Write core/settings/dev.py**

`backend/core/settings/dev.py`:
```python
from .base import *  # noqa: F401, F403

DEBUG = True
ALLOWED_HOSTS = ['*']
CORS_ALLOWED_ORIGINS = ['http://localhost:3000']
CORS_ALLOW_ALL_ORIGINS = True
```

- [ ] **Step 4: Write core/urls.py**

`backend/core/urls.py`:
```python
from django.urls import path, include

urlpatterns = [
    path('auth/', include('auth_app.urls')),
    path('', include('api.urls')),
]
```

- [ ] **Step 5: Write core/wsgi.py**

`backend/core/wsgi.py`:
```python
import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings.prod')
application = get_wsgi_application()
```

- [ ] **Step 6: Write core/celery.py and core/__init__.py**

`backend/core/celery.py`:
```python
import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings.dev')
app = Celery('cpse')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()
```

`backend/core/__init__.py`:
```python
from .celery import app as celery_app

__all__ = ['celery_app']
```

`backend/core/settings/__init__.py` (empty):
```python
```

- [ ] **Step 7: Create stub app files**

`backend/api/__init__.py` (empty)

`backend/api/apps.py`:
```python
from django.apps import AppConfig

class ApiConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'api'
```

`backend/api/models.py` (empty stub — filled in Task 4):
```python
```

`backend/api/views.py` (empty stub — filled in Tasks 6 and 10):
```python
```

`backend/api/urls.py`:
```python
from django.urls import path

urlpatterns = []
```

`backend/auth_app/__init__.py` (empty)

`backend/auth_app/apps.py`:
```python
from django.apps import AppConfig

class AuthAppConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'auth_app'
```

`backend/auth_app/views.py` (empty stub — filled in Task 5):
```python
```

`backend/auth_app/urls.py`:
```python
from django.urls import path

urlpatterns = []
```

- [ ] **Step 8: Verify Django starts**

```bash
cd backend && python manage.py check
```

Expected:
```
System check identified no issues (0 silenced).
```

- [ ] **Step 9: Commit**

```bash
git add backend/manage.py backend/core/ backend/api/ backend/auth_app/
git commit -m "feat: Django project skeleton (core settings, stub apps)"
```

---

## Task 3: Move service layer into backend/services/

**Files:**
- Create: `backend/services/` tree (copy from project root)
- Create: `backend/utils/` tree (copy from project root)
- Modify: `backend/utils/config_loader.py`
- Modify: `backend/services/signals/weather.py`
- Modify: `backend/services/data_layer/database.py`
- Create: `backend/tests/` (copy existing tests, update imports)

- [ ] **Step 1: Create directories and copy files**

Run from project root:

```bash
mkdir -p backend/services/signals
mkdir -p backend/services/metrics
mkdir -p backend/services/engine/models
mkdir -p backend/services/interventions
mkdir -p backend/services/data_layer
mkdir -p backend/utils
mkdir -p backend/tests

# Copy services as-is
cp signals/geocoder.py       backend/services/signals/
cp signals/tomtom.py         backend/services/signals/
cp metrics/compression.py    backend/services/metrics/
cp engine/classifier.py      backend/services/engine/
cp engine/anomaly.py         backend/services/engine/
cp engine/models/gnn_stub.py backend/services/engine/models/
cp interventions/recommender.py backend/services/interventions/
cp data_layer/vectorizer.py  backend/services/data_layer/

# Copy for modification
cp signals/weather.py        backend/services/signals/
cp data_layer/database.py    backend/services/data_layer/

# Copy utils
cp utils/config_loader.py    backend/utils/
cp utils/time_helper.py      backend/utils/
cp utils/security.py         backend/utils/

# Create __init__.py files
touch backend/services/__init__.py
touch backend/services/signals/__init__.py
touch backend/services/metrics/__init__.py
touch backend/services/engine/__init__.py
touch backend/services/engine/models/__init__.py
touch backend/services/interventions/__init__.py
touch backend/services/data_layer/__init__.py
touch backend/utils/__init__.py
touch backend/tests/__init__.py
```

- [ ] **Step 2: Rewrite utils/config_loader.py with absolute path**

`backend/utils/config_loader.py`:
```python
import yaml
import os
from pathlib import Path

# config.yaml lives at project root, two levels above backend/utils/
_CONFIG_PATH = Path(__file__).resolve().parent.parent.parent / 'config.yaml'
_config = None


def load_config(path: str | None = None) -> dict:
    global _config
    resolved = Path(path) if path else _CONFIG_PATH
    if not resolved.exists():
        print(f"Config file not found at {resolved}, using defaults.")
        return {}
    with open(resolved, 'r') as f:
        _config = yaml.safe_load(f)
    return _config


def get_config() -> dict:
    global _config
    if _config is None:
        return load_config()
    return _config
```

- [ ] **Step 3: Rewrite signals/weather.py — remove Streamlit**

`backend/services/signals/weather.py`:
```python
import requests
import os
import time
from utils.config_loader import get_config


def _fetch_weather_risk_live(lat: float, lon: float, api_key: str, base_url: str):
    params = {'lat': lat, 'lon': lon, 'appid': api_key, 'units': 'metric'}
    try:
        response = requests.get(base_url, params=params, timeout=5)
        response.raise_for_status()
        data = response.json()
        weather_id = data['weather'][0]['id']
        description = data['weather'][0]['main']
        risk = 0.0
        if 200 <= weather_id < 300:
            risk = 1.0
        elif 300 <= weather_id < 400:
            risk = 0.3
        elif 500 <= weather_id < 600:
            risk = 0.5 if weather_id in (500, 501) else 0.8
        elif 600 <= weather_id < 700:
            risk = 0.7
        elif 700 <= weather_id < 800:
            risk = 1.0 if weather_id == 781 else (0.9 if weather_id == 771 else 0.4)
        elif weather_id == 800:
            risk = 0.0
        elif 800 < weather_id < 900:
            risk = 0.1
        return risk, description, data
    except Exception as e:
        print(f"Weather API Error: {e}")
        return None, "Error", {}


class OpenWeatherMapSignal:
    # Class-level in-memory cache: {key: {'ts': float, 'result': tuple}}
    _cache: dict = {}
    _cache_ttl = 600  # 10 minutes — mirrors old @st.cache_data(ttl=600)

    def __init__(self):
        config = get_config()
        weather_config = config.get('api', {}).get('openweathermap', {})
        env_var = weather_config.get('env_key_name', 'OPENWEATHERMAP_API_KEY')
        self.api_key = os.getenv(env_var)
        self.base_url = weather_config.get(
            'base_url', 'https://api.openweathermap.org/data/2.5/weather'
        )

    def fetch_weather_risk(self, lat: float, lon: float):
        if not self.api_key:
            return None, "No API Key", {}
        key = f"{lat:.4f},{lon:.4f}"
        entry = OpenWeatherMapSignal._cache.get(key)
        if entry and time.monotonic() - entry['ts'] < self._cache_ttl:
            return entry['result']
        result = _fetch_weather_risk_live(lat, lon, self.api_key, self.base_url)
        OpenWeatherMapSignal._cache[key] = {'ts': time.monotonic(), 'result': result}
        return result
```

- [ ] **Step 4: Rewrite data_layer/database.py — use SUPABASE_DB_URL**

`backend/services/data_layer/database.py`:
```python
"""
data_layer/database.py
PostgreSQL persistence via Supabase. Reads SUPABASE_DB_URL from environment.
"""
import os
import logging
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Optional

import psycopg2
from psycopg2.extras import RealDictCursor

log = logging.getLogger(__name__)

_TABLE = "crowd_telemetry"

_SCHEMA_COLUMNS: dict[str, str] = {
    "speed":         "DOUBLE PRECISION",
    "gradient":      "DOUBLE PRECISION",
    "velocity_var":  "DOUBLE PRECISION",
    "anomaly_score": "DOUBLE PRECISION",
    "risk_score":    "DOUBLE PRECISION",
    "session_id":    "TEXT",
}


class SupabaseDatabaseManager:
    def __init__(self):
        self._dsn: Optional[str] = None
        self._connected: bool = False
        self._status: str = "Not initialised"

        dsn = os.getenv("SUPABASE_DB_URL") or os.getenv("SUPABASE_POOLER_URL")
        if not dsn:
            self._status = "SUPABASE_DB_URL not set — persistence disabled"
            log.warning(self._status)
            return

        self._dsn = dsn
        try:
            self._bootstrap_schema()
            self._connected = True
            self._status = "Connected — Supabase PostgreSQL"
        except Exception as exc:
            self._connected = False
            self._status = f"Connection failed: {exc}"
            log.error(f"Supabase bootstrap error: {exc}")

    @property
    def connected(self) -> bool:
        return self._connected

    @property
    def status_label(self) -> str:
        return self._status

    @contextmanager
    def _cursor(self, dict_cursor: bool = False):
        factory = RealDictCursor if dict_cursor else None
        conn = psycopg2.connect(self._dsn)
        try:
            cur = conn.cursor(cursor_factory=factory) if factory else conn.cursor()
            yield cur
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _bootstrap_schema(self):
        with self._cursor() as cur:
            cur.execute(f"""
                CREATE TABLE IF NOT EXISTS {_TABLE} (
                    id            SERIAL           PRIMARY KEY,
                    created_at    TIMESTAMPTZ      NOT NULL DEFAULT NOW(),
                    location_name TEXT             NOT NULL,
                    latitude      DOUBLE PRECISION NOT NULL DEFAULT 0,
                    longitude     DOUBLE PRECISION NOT NULL DEFAULT 0,
                    congestion    DOUBLE PRECISION NOT NULL DEFAULT 0,
                    speed         DOUBLE PRECISION,
                    gradient      DOUBLE PRECISION,
                    velocity_var  DOUBLE PRECISION,
                    anomaly_score DOUBLE PRECISION,
                    risk_score    DOUBLE PRECISION,
                    state         TEXT             NOT NULL DEFAULT 'Unknown',
                    session_id    TEXT
                )
            """)
            cur.execute("""
                SELECT column_name FROM information_schema.columns
                WHERE table_schema = 'public' AND table_name = %s
            """, (_TABLE,))
            existing = {row[0] for row in cur.fetchall()}
            for col, typ in _SCHEMA_COLUMNS.items():
                if col not in existing:
                    cur.execute(
                        f"ALTER TABLE {_TABLE} ADD COLUMN IF NOT EXISTS {col} {typ}"
                    )
            cur.execute(
                f"CREATE INDEX IF NOT EXISTS idx_{_TABLE}_location "
                f"ON {_TABLE} (location_name)"
            )
            cur.execute(
                f"CREATE INDEX IF NOT EXISTS idx_{_TABLE}_created_at "
                f"ON {_TABLE} (created_at DESC)"
            )

    def insert_telemetry(self, data: dict):
        if not self._connected:
            return
        try:
            with self._cursor() as cur:
                cur.execute(
                    f"""INSERT INTO {_TABLE}
                        (location_name, latitude, longitude, congestion, speed,
                         gradient, velocity_var, anomaly_score, risk_score,
                         state, created_at)
                        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                    (
                        data.get("location_name", "Unknown"),
                        data.get("lat", 0.0),
                        data.get("lon", 0.0),
                        data.get("congestion", 0.0),
                        data.get("speed", 0.0),
                        data.get("gradient", 0.0),
                        data.get("velocity_var", 0.0),
                        data.get("anomaly_score", 0.0),
                        data.get("risk_score", 0.0),
                        data.get("state", "Unknown"),
                        datetime.now(timezone.utc),
                    ),
                )
        except Exception as exc:
            log.error(f"insert_telemetry failed: {exc}")
            self._connected = False
            self._status = f"Write error: {exc}"

    def fetch_filtered_logs(
        self,
        limit: int = 100,
        location: Optional[str] = None,
        anomaly_only: bool = False,
    ) -> list:
        if not self._connected:
            return []
        try:
            conditions, params = [], []
            if location and location != "All":
                conditions.append("location_name = %s")
                params.append(location)
            if anomaly_only:
                conditions.append("anomaly_score > 2.5")
            where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
            params.append(limit)
            with self._cursor(dict_cursor=True) as cur:
                cur.execute(
                    f"SELECT * FROM {_TABLE} {where} "
                    f"ORDER BY created_at DESC LIMIT %s",
                    params,
                )
                return [dict(r) for r in cur.fetchall()]
        except Exception as exc:
            log.error(f"fetch_filtered_logs failed: {exc}")
            return []

    def fetch_unique_locations(self) -> list:
        if not self._connected:
            return []
        try:
            with self._cursor() as cur:
                cur.execute(
                    f"SELECT DISTINCT location_name FROM {_TABLE} "
                    f"ORDER BY location_name"
                )
                return [row[0] for row in cur.fetchall()]
        except Exception as exc:
            log.error(f"fetch_unique_locations failed: {exc}")
            return []


# Backward-compat alias so any remaining references to NeonDatabaseManager still work
NeonDatabaseManager = SupabaseDatabaseManager


def get_db_client() -> SupabaseDatabaseManager:
    return SupabaseDatabaseManager()
```

- [ ] **Step 5: Copy existing tests and update imports**

```bash
cp tests/test_classifier.py backend/tests/
cp tests/test_metrics.py    backend/tests/
cp tests/test_vectorizer.py backend/tests/
```

In `backend/tests/test_classifier.py`, change line 2:
```python
# Before:
from engine.classifier import CrowdClassifier
# After:
from services.engine.classifier import CrowdClassifier
```

In `backend/tests/test_metrics.py`, change line 2:
```python
# Before:
from metrics.compression import CrowdMetrics
# After:
from services.metrics.compression import CrowdMetrics
```

In `backend/tests/test_vectorizer.py`, change line 3:
```python
# Before:
from data_layer.vectorizer import CrowdStateVectorizer
# After:
from services.data_layer.vectorizer import CrowdStateVectorizer
```

- [ ] **Step 6: Run existing tests from backend/**

```bash
cd backend && python -m pytest tests/test_classifier.py tests/test_metrics.py tests/test_vectorizer.py -v
```

Expected: all 13 tests pass (8 classifier + 5 metrics + 2 vectorizer).

- [ ] **Step 7: Commit**

```bash
git add backend/services/ backend/utils/ backend/tests/
git commit -m "feat: move service layer into backend/services/, fix imports"
```

---

## Task 4: Django ORM models

**Files:**
- Modify: `backend/api/models.py`
- Auto-generate: `backend/api/migrations/0001_initial.py`
- Create: `backend/tests/test_models.py`

- [ ] **Step 1: Write failing test**

`backend/tests/test_models.py`:
```python
import uuid
from django.test import TestCase


class TestCrowdTelemetryModel(TestCase):
    def test_table_name_and_unmanaged(self):
        from api.models import CrowdTelemetry
        assert CrowdTelemetry._meta.db_table == 'crowd_telemetry'
        assert CrowdTelemetry._meta.managed is False


class TestAnalysisTaskModel(TestCase):
    def test_create_and_retrieve(self):
        from api.models import AnalysisTask
        tid = str(uuid.uuid4())
        task = AnalysisTask.objects.create(
            task_id=tid,
            status='pending',
            location_name='Test Location',
        )
        fetched = AnalysisTask.objects.get(task_id=tid)
        assert fetched.status == 'pending'
        assert fetched.result_json is None

    def test_result_json_stores_dict(self):
        from api.models import AnalysisTask
        task = AnalysisTask.objects.create(
            task_id=str(uuid.uuid4()),
            status='done',
            location_name='Delhi',
            result_json={'state': 'Stable', 'risk_score': 12.0},
        )
        fetched = AnalysisTask.objects.get(task_id=task.task_id)
        assert fetched.result_json['state'] == 'Stable'
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd backend && python -m pytest tests/test_models.py -v
```

Expected: FAIL — `ImportError: cannot import name 'CrowdTelemetry'`

- [ ] **Step 3: Write models**

`backend/api/models.py`:
```python
from django.db import models


class CrowdTelemetry(models.Model):
    created_at    = models.DateTimeField(auto_now_add=True)
    location_name = models.TextField()
    latitude      = models.FloatField(default=0)
    longitude     = models.FloatField(default=0)
    congestion    = models.FloatField(default=0)
    speed         = models.FloatField(null=True, blank=True)
    gradient      = models.FloatField(null=True, blank=True)
    velocity_var  = models.FloatField(null=True, blank=True)
    anomaly_score = models.FloatField(null=True, blank=True)
    risk_score    = models.FloatField(null=True, blank=True)
    state         = models.TextField(default='Unknown')
    session_id    = models.TextField(null=True, blank=True)

    class Meta:
        db_table = 'crowd_telemetry'
        managed  = False           # table already exists in Supabase
        ordering = ['-created_at']


class AnalysisTask(models.Model):
    task_id       = models.CharField(max_length=255, unique=True, db_index=True)
    created_at    = models.DateTimeField(auto_now_add=True)
    status        = models.CharField(max_length=20, default='pending')
    location_name = models.TextField()
    result_json   = models.JSONField(null=True, blank=True)

    class Meta:
        db_table = 'analysis_task'
        ordering = ['-created_at']
```

- [ ] **Step 4: Generate and run migration**

```bash
cd backend && python manage.py makemigrations api
python manage.py migrate
```

Expected: migration creates `analysis_task` table only; `crowd_telemetry` is skipped (`managed=False`).

- [ ] **Step 5: Run tests**

```bash
cd backend && python -m pytest tests/test_models.py -v
```

Expected: 3 passed.

- [ ] **Step 6: Commit**

```bash
git add backend/api/models.py backend/api/migrations/
git commit -m "feat: add CrowdTelemetry (unmanaged) and AnalysisTask ORM models"
```

---

## Task 5: Auth endpoints + seed_users

**Files:**
- Modify: `backend/auth_app/views.py`
- Modify: `backend/auth_app/urls.py`
- Create: `backend/auth_app/management/__init__.py`
- Create: `backend/auth_app/management/commands/__init__.py`
- Create: `backend/auth_app/management/commands/seed_users.py`
- Create: `backend/tests/test_auth.py`

- [ ] **Step 1: Write failing tests**

`backend/tests/test_auth.py`:
```python
import json
from django.test import TestCase, Client
from django.contrib.auth.models import User


class TestAuthEndpoints(TestCase):
    def setUp(self):
        self.client = Client(enforce_csrf_checks=False)
        User.objects.create_user(username='admin', password='testpass', is_staff=True)
        User.objects.create_user(username='viewer1', password='viewpass', is_staff=False)

    def _post(self, url, payload):
        return self.client.post(
            url,
            data=json.dumps(payload),
            content_type='application/json',
        )

    def test_login_admin_success(self):
        resp = self._post('/auth/login', {'username': 'admin', 'password': 'testpass'})
        assert resp.status_code == 200
        data = resp.json()
        assert data['username'] == 'admin'
        assert data['is_admin'] is True

    def test_login_viewer_not_admin(self):
        resp = self._post('/auth/login', {'username': 'viewer1', 'password': 'viewpass'})
        assert resp.status_code == 200
        assert resp.json()['is_admin'] is False

    def test_login_wrong_password_returns_401(self):
        resp = self._post('/auth/login', {'username': 'admin', 'password': 'wrong'})
        assert resp.status_code == 401

    def test_logout_returns_200(self):
        self.client.login(username='admin', password='testpass')
        resp = self.client.post('/auth/logout')
        assert resp.status_code == 200

    def test_history_without_login_returns_403(self):
        unauth = Client()
        resp = unauth.get('/history')
        assert resp.status_code in (401, 403)
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd backend && python -m pytest tests/test_auth.py -v
```

Expected: FAIL — 404 (endpoints not wired).

- [ ] **Step 3: Write auth views**

`backend/auth_app/views.py`:
```python
import json
from django.contrib.auth import authenticate, login, logout
from django.http import JsonResponse
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator


@method_decorator(csrf_exempt, name='dispatch')
class LoginView(View):
    def post(self, request):
        try:
            body = json.loads(request.body)
        except (json.JSONDecodeError, UnicodeDecodeError):
            return JsonResponse({'error': 'Invalid JSON'}, status=400)

        username = body.get('username', '').strip()
        password = body.get('password', '')
        user = authenticate(request, username=username, password=password)
        if user is None:
            return JsonResponse({'error': 'Invalid credentials'}, status=401)

        login(request, user)
        return JsonResponse({'username': user.username, 'is_admin': user.is_staff})


@method_decorator(csrf_exempt, name='dispatch')
class LogoutView(View):
    def post(self, request):
        logout(request)
        return JsonResponse({'status': 'logged out'})
```

- [ ] **Step 4: Wire auth URLs**

`backend/auth_app/urls.py`:
```python
from django.urls import path
from .views import LoginView, LogoutView

urlpatterns = [
    path('login', LoginView.as_view()),
    path('logout', LogoutView.as_view()),
]
```

- [ ] **Step 5: Run tests**

```bash
cd backend && python -m pytest tests/test_auth.py -v
```

Expected: 5 passed.

- [ ] **Step 6: Write seed_users management command**

```bash
mkdir -p backend/auth_app/management/commands
touch backend/auth_app/management/__init__.py
touch backend/auth_app/management/commands/__init__.py
```

`backend/auth_app/management/commands/seed_users.py`:
```python
import os
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User


class Command(BaseCommand):
    help = 'Seed users from APP_PASSWORD env var (comma-separated). First = admin.'

    def handle(self, *args, **options):
        raw = os.environ.get('APP_PASSWORD', 'cpseisawesome')
        passwords = [p.strip() for p in raw.split(',') if p.strip()]

        if not passwords:
            self.stderr.write("APP_PASSWORD is empty — no users created.")
            return

        for idx, password in enumerate(passwords):
            username = 'admin' if idx == 0 else f'viewer{idx}'
            is_staff = idx == 0

            if User.objects.filter(username=username).exists():
                self.stdout.write(f"User '{username}' already exists — skipping.")
                continue

            User.objects.create_user(
                username=username, password=password, is_staff=is_staff
            )
            role = 'admin' if is_staff else 'viewer'
            self.stdout.write(
                self.style.SUCCESS(f"Created {role} user: '{username}'")
            )
```

- [ ] **Step 7: Smoke-test seed_users**

```bash
cd backend && APP_PASSWORD="adminpass,viewerpass" python manage.py seed_users
```

Expected:
```
Created admin user: 'admin'
Created viewer user: 'viewer1'
```

Run again — should print "already exists" for both.

- [ ] **Step 8: Commit**

```bash
git add backend/auth_app/
git commit -m "feat: login/logout endpoints + seed_users management command"
```

---

## Task 6: /history and /latest DRF views

**Files:**
- Create: `backend/api/serializers.py`
- Modify: `backend/api/views.py`
- Modify: `backend/api/urls.py`
- Create: `backend/tests/test_api_static.py`

- [ ] **Step 1: Write failing tests**

`backend/tests/test_api_static.py`:
```python
import json
from django.test import TestCase, Client
from django.contrib.auth.models import User
from unittest.mock import patch


class TestHistoryView(TestCase):
    def setUp(self):
        self.client = Client(enforce_csrf_checks=False)
        User.objects.create_user(username='admin', password='pass', is_staff=True)
        self.client.login(username='admin', password='pass')

    def test_returns_list(self):
        resp = self.client.get('/history')
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_accepts_limit_param(self):
        resp = self.client.get('/history?limit=10&location=Delhi')
        assert resp.status_code == 200

    def test_requires_auth(self):
        unauth = Client()
        resp = unauth.get('/history')
        assert resp.status_code in (401, 403)


class TestLatestView(TestCase):
    def setUp(self):
        self.client = Client(enforce_csrf_checks=False)
        User.objects.create_user(username='admin', password='pass', is_staff=True)
        self.client.login(username='admin', password='pass')

    def test_returns_null_when_no_data(self):
        with patch('api.views._redis') as mock_redis_fn:
            mock_redis_fn.return_value.get.return_value = None
            resp = self.client.get('/latest?location=Delhi')
        assert resp.status_code == 200
        assert resp.json() is None

    def test_returns_cached_result(self):
        cached = json.dumps({'state': 'Stable', 'risk_score': 5.0})
        with patch('api.views._redis') as mock_redis_fn:
            mock_redis_fn.return_value.get.return_value = cached
            resp = self.client.get('/latest?location=Delhi')
        assert resp.status_code == 200
        assert resp.json()['state'] == 'Stable'
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd backend && python -m pytest tests/test_api_static.py -v
```

Expected: FAIL — 404.

- [ ] **Step 3: Write serializers**

`backend/api/serializers.py`:
```python
from rest_framework import serializers
from .models import CrowdTelemetry, AnalysisTask


class CrowdTelemetrySerializer(serializers.ModelSerializer):
    class Meta:
        model = CrowdTelemetry
        fields = '__all__'


class AnalysisTaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = AnalysisTask
        fields = ['task_id', 'created_at', 'status', 'location_name', 'result_json']
```

- [ ] **Step 4: Write views**

`backend/api/views.py`:
```python
import json
import redis as redis_lib
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from .models import CrowdTelemetry
from .serializers import CrowdTelemetrySerializer


def _redis() -> redis_lib.Redis:
    return redis_lib.from_url(settings.REDIS_URL, decode_responses=True)


class HistoryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        limit = int(request.query_params.get('limit', 100))
        location = request.query_params.get('location')
        anomaly_only = request.query_params.get('anomaly_only', 'false').lower() == 'true'

        qs = CrowdTelemetry.objects.all()
        if location and location != 'All':
            qs = qs.filter(location_name=location)
        if anomaly_only:
            qs = qs.filter(anomaly_score__gt=2.5)
        qs = qs[:limit]

        return Response(CrowdTelemetrySerializer(qs, many=True).data)


class LatestView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        location = request.query_params.get('location', '')
        if not location:
            return Response(None)
        try:
            raw = _redis().get(f'cpse:last:{location}')
            return Response(json.loads(raw) if raw else None)
        except Exception:
            return Response(None)
```

- [ ] **Step 5: Update api/urls.py**

`backend/api/urls.py`:
```python
from django.urls import path
from .views import HistoryView, LatestView

urlpatterns = [
    path('history', HistoryView.as_view()),
    path('latest', LatestView.as_view()),
]
```

- [ ] **Step 6: Run tests**

```bash
cd backend && python -m pytest tests/test_api_static.py -v
```

Expected: 5 passed.

- [ ] **Step 7: Commit**

```bash
git add backend/api/
git commit -m "feat: /history and /latest DRF endpoints"
```

---

## Task 7: Celery setup + trivial task verification

**Files:**
- Create: `backend/tasks/__init__.py`
- Create: `backend/tasks/analysis.py` (stub)
- Create: `backend/tests/test_celery_config.py`

- [ ] **Step 1: Write config tests**

`backend/tests/test_celery_config.py`:
```python
def test_celery_app_name():
    from core.celery import app
    assert app.main == 'cpse'


def test_celery_broker_is_redis():
    from django.conf import settings
    assert settings.CELERY_BROKER_URL.startswith('redis://')


def test_celery_result_backend_is_redis():
    from django.conf import settings
    assert settings.CELERY_RESULT_BACKEND.startswith('redis://')
```

- [ ] **Step 2: Run tests**

```bash
cd backend && python -m pytest tests/test_celery_config.py -v
```

Expected: 3 passed.

- [ ] **Step 3: Create tasks package with stub**

`backend/tasks/__init__.py`:
```python
from .analysis import analyze_crowd

__all__ = ['analyze_crowd']
```

`backend/tasks/analysis.py` (stub — full pipeline in Task 9):
```python
from celery import shared_task


@shared_task(bind=True, max_retries=3)
def analyze_crowd(self, lat: float, lon: float, location_name: str,
                  env_params: dict, task_id: str):
    """Full pipeline implemented in Task 9."""
    return {'status': 'stub', 'task_id': task_id}
```

- [ ] **Step 4: Manually verify Celery worker starts**

In a separate terminal (requires Redis running):
```bash
cd backend && celery -A core worker --loglevel=info
```

Expected output includes:
```
[tasks]
  . tasks.analysis.analyze_crowd
```

Stop with Ctrl+C after confirming.

- [ ] **Step 5: Commit**

```bash
git add backend/tasks/ backend/tests/test_celery_config.py
git commit -m "feat: Celery app config and task stub"
```

---

## Task 8: Redis result store + state serialization

**Files:**
- Create: `backend/cache/__init__.py`
- Create: `backend/cache/result_store.py`
- Create: `backend/tests/test_result_store.py`

- [ ] **Step 1: Write failing tests**

`backend/tests/test_result_store.py`:
```python
import json
import numpy as np
from unittest.mock import MagicMock, patch


class TestStateSerialisation:
    def test_roundtrip_crowd_metrics(self):
        from cache.result_store import serialize_metrics_state, deserialize_metrics_state
        from services.metrics.compression import CrowdMetrics

        m = CrowdMetrics()
        m.update(0.4, 28.0)
        m.update(0.55, 25.0)
        m.update(0.7, 20.0)

        blob = serialize_metrics_state(m)
        assert isinstance(blob, str)

        m2 = deserialize_metrics_state(blob)
        assert list(m2.congestion_history) == pytest_approx_list(m.congestion_history)
        assert list(m2.speed_history) == pytest_approx_list(m.speed_history)
        assert m2.history_size == m.history_size

    def test_roundtrip_anomaly_detector(self):
        from cache.result_store import serialize_anomaly_state, deserialize_anomaly_state
        from services.engine.anomaly import AnomalyDetector

        det = AnomalyDetector()
        vec = np.array([0.5, 0.1, 0.3, 0.4], dtype=np.float32)
        for _ in range(5):
            det.update_and_detect(vec)

        blob = serialize_anomaly_state(det)
        det2 = deserialize_anomaly_state(blob)

        assert len(det2.history) == len(det.history)
        assert det2._cycle == det._cycle
        assert det2.z_threshold == det.z_threshold

    def test_store_and_get_result(self):
        from cache.result_store import store_result, get_result

        mock_r = MagicMock()
        mock_r.get.return_value = json.dumps({'state': 'Stable', 'task_id': 'xyz'})

        with patch('cache.result_store._redis', return_value=mock_r):
            store_result('xyz', 'Delhi', {'state': 'Stable', 'task_id': 'xyz'})
            result = get_result('xyz')

        mock_r.setex.assert_called()
        assert result['state'] == 'Stable'

    def test_get_result_returns_none_on_miss(self):
        from cache.result_store import get_result

        mock_r = MagicMock()
        mock_r.get.return_value = None

        with patch('cache.result_store._redis', return_value=mock_r):
            assert get_result('nonexistent') is None


def pytest_approx_list(dq):
    return list(dq)
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd backend && python -m pytest tests/test_result_store.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'cache'`

- [ ] **Step 3: Write cache/result_store.py**

`backend/cache/__init__.py` (empty)

`backend/cache/result_store.py`:
```python
"""
Redis key schema:
  cpse:result:{task_id}   TTL 3600s  — full result JSON
  cpse:last:{location}    TTL 86400s — latest result per location
  cpse:state:{location}   TTL 86400s — serialized rolling state (JSON)
  cpse:lock:{location}    TTL 30s    — concurrency lock
"""
import json
import time
import logging
from collections import deque

import numpy as np
import redis as redis_lib
from django.conf import settings

log = logging.getLogger(__name__)

RESULT_TTL = 3600
LAST_TTL   = 86400
STATE_TTL  = 86400
LOCK_TTL   = 30


def _redis() -> redis_lib.Redis:
    return redis_lib.from_url(settings.REDIS_URL, decode_responses=True)


# ── Result helpers ────────────────────────────────────────────────────────────

def store_result(task_id: str, location_name: str, payload: dict) -> None:
    blob = json.dumps(payload, default=str)
    r = _redis()
    r.setex(f'cpse:result:{task_id}', RESULT_TTL, blob)
    r.setex(f'cpse:last:{location_name}', LAST_TTL, blob)


def get_result(task_id: str) -> dict | None:
    raw = _redis().get(f'cpse:result:{task_id}')
    return json.loads(raw) if raw else None


# ── State serialization ───────────────────────────────────────────────────────

def serialize_metrics_state(metrics) -> str:
    return json.dumps({
        'congestion_history': list(metrics.congestion_history),
        'speed_history':      list(metrics.speed_history),
        'history_size':       metrics.history_size,
    })


def deserialize_metrics_state(blob: str):
    from services.metrics.compression import CrowdMetrics
    d = json.loads(blob)
    m = CrowdMetrics(history_size=d['history_size'])
    m.congestion_history = deque(d['congestion_history'], maxlen=d['history_size'])
    m.speed_history      = deque(d['speed_history'],      maxlen=d['history_size'])
    return m


def serialize_anomaly_state(detector) -> str:
    return json.dumps({
        'history':      [v.tolist() for v in detector.history],
        'history_size': detector.history_size,
        'z_threshold':  detector.z_threshold,
        'min_samples':  detector.min_samples,
        'cycle':        detector._cycle,
    })


def deserialize_anomaly_state(blob: str):
    from services.engine.anomaly import AnomalyDetector
    d = json.loads(blob)
    det = AnomalyDetector(
        history_size=d['history_size'],
        z_threshold=d['z_threshold'],
        min_samples=d['min_samples'],
    )
    det.history = deque(
        [np.array(v, dtype=np.float32) for v in d['history']],
        maxlen=d['history_size'],
    )
    det._cycle = d['cycle']
    return det


# ── Per-location state load/save ──────────────────────────────────────────────

def load_location_state(location_name: str) -> tuple:
    """Returns (CrowdMetrics, AnomalyDetector); fresh instances if no state in Redis."""
    from services.metrics.compression import CrowdMetrics
    from services.engine.anomaly import AnomalyDetector

    try:
        raw = _redis().get(f'cpse:state:{location_name}')
        if raw:
            d = json.loads(raw)
            metrics  = deserialize_metrics_state(json.dumps(d['metrics']))
            detector = deserialize_anomaly_state(json.dumps(d['anomaly']))
            return metrics, detector
    except Exception as exc:
        log.warning(f"State load failed for '{location_name}': {exc}. Using fresh state.")

    return CrowdMetrics(), AnomalyDetector()


def save_location_state(location_name: str, metrics, detector) -> None:
    blob = json.dumps({
        'metrics': json.loads(serialize_metrics_state(metrics)),
        'anomaly': json.loads(serialize_anomaly_state(detector)),
    })
    _redis().setex(f'cpse:state:{location_name}', STATE_TTL, blob)


# ── Concurrency lock ──────────────────────────────────────────────────────────

def acquire_lock(location_name: str, retries: int = 3) -> bool:
    r = _redis()
    key = f'cpse:lock:{location_name}'
    for _ in range(retries):
        if r.set(key, '1', nx=True, ex=LOCK_TTL):
            return True
        time.sleep(1)
    log.warning(f"Could not acquire lock for '{location_name}' after {retries} retries.")
    return False


def release_lock(location_name: str) -> None:
    _redis().delete(f'cpse:lock:{location_name}')
```

- [ ] **Step 4: Run tests**

```bash
cd backend && python -m pytest tests/test_result_store.py -v
```

Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add backend/cache/ backend/tests/test_result_store.py
git commit -m "feat: Redis result store and per-location state serialization"
```

---

## Task 9: analyze_crowd — full pipeline

**Files:**
- Modify: `backend/tasks/analysis.py`
- Create: `backend/tests/test_analyze_task.py`

- [ ] **Step 1: Write failing test**

`backend/tests/test_analyze_task.py`:
```python
import numpy as np
from unittest.mock import patch, MagicMock
from django.test import TestCase


class TestRunPipeline(TestCase):
    def _make_telemetry(self):
        return {
            'congestion': 0.5,
            'current_speed': 25.0,
            'free_flow_speed': 50.0,
            'is_simulated': True,
        }

    def test_pipeline_returns_done_status(self):
        from tasks.analysis import _run_pipeline
        from services.metrics.compression import CrowdMetrics
        from services.engine.anomaly import AnomalyDetector

        with patch('tasks.analysis.TomTomSignal') as MockSignal, \
             patch('tasks.analysis.load_location_state') as mock_load, \
             patch('tasks.analysis.save_location_state'), \
             patch('tasks.analysis.store_result'), \
             patch('tasks.analysis._write_to_db'):

            MockSignal.return_value.fetch_telemetry.return_value = self._make_telemetry()
            mock_load.return_value = (CrowdMetrics(), AnomalyDetector())

            result = _run_pipeline(
                lat=28.6139, lon=77.2090,
                location_name='Delhi',
                env_params={
                    'env_weather_risk': 0.0,
                    'env_width_factor': 1.0,
                    'env_event_active': False,
                },
                task_id='test-abc',
            )

        assert result['status'] == 'done'
        assert result['task_id'] == 'test-abc'
        assert 'state' in result
        assert 'risk_score' in result
        assert 'interventions' in result
        assert 'breakdown' in result

    def test_pipeline_state_is_valid(self):
        from tasks.analysis import _run_pipeline
        from services.metrics.compression import CrowdMetrics
        from services.engine.anomaly import AnomalyDetector

        valid_states = {'Stable', 'Compressing', 'Volatile', 'Agitated', 'Fragmenting'}

        with patch('tasks.analysis.TomTomSignal') as MockSignal, \
             patch('tasks.analysis.load_location_state') as mock_load, \
             patch('tasks.analysis.save_location_state'), \
             patch('tasks.analysis.store_result'), \
             patch('tasks.analysis._write_to_db'):

            MockSignal.return_value.fetch_telemetry.return_value = self._make_telemetry()
            mock_load.return_value = (CrowdMetrics(), AnomalyDetector())

            result = _run_pipeline(
                lat=28.6139, lon=77.2090,
                location_name='Delhi',
                env_params={'env_weather_risk': 0.0, 'env_width_factor': 1.0, 'env_event_active': False},
                task_id='test-xyz',
            )

        base_state = result['state'].split(' (')[0]
        assert base_state in valid_states
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd backend && python -m pytest tests/test_analyze_task.py -v
```

Expected: FAIL — `ImportError: cannot import name '_run_pipeline'`

- [ ] **Step 3: Write full tasks/analysis.py**

`backend/tasks/analysis.py`:
```python
import logging
from datetime import datetime, timezone

from celery import shared_task

from services.signals.tomtom import TomTomSignal
from services.data_layer.vectorizer import CrowdStateVectorizer
from services.engine.classifier import CrowdClassifier
from services.interventions.recommender import InterventionRecommender
from cache.result_store import (
    load_location_state,
    save_location_state,
    store_result,
    acquire_lock,
    release_lock,
)

log = logging.getLogger(__name__)

# Module-level singletons (stateless — safe to share across calls)
_vectorizer  = CrowdStateVectorizer()
_classifier  = CrowdClassifier()
_recommender = InterventionRecommender()


def _run_pipeline(
    lat: float,
    lon: float,
    location_name: str,
    env_params: dict,
    task_id: str,
) -> dict:
    """
    Execute the full analysis pipeline synchronously.
    Separated from the Celery task decorator for unit testability.
    """
    # 1. Fetch telemetry (live or simulated)
    signal = TomTomSignal()
    signal.set_location(lat, lon, location_name)
    telemetry = signal.fetch_telemetry()
    if telemetry is None:
        raise RuntimeError("Telemetry fetch failed and simulation is disabled.")

    congestion    = telemetry['congestion']
    current_speed = telemetry['current_speed']
    is_simulated  = telemetry.get('is_simulated', False)

    # 2. Load per-location rolling state from Redis
    metrics, detector = load_location_state(location_name)

    # 3. Update rolling windows
    metrics.update(congestion, current_speed)

    # 4. Compute compression gradient + velocity variance
    gradient, gradient_quality, _ = metrics.compute_compression_gradient()
    velocity_var, _               = metrics.compute_velocity_variance()

    # 5. Vectorize
    crowd_vector = _vectorizer.create_state_vector(congestion, velocity_var, gradient)

    # 6. Anomaly detection
    _, anomaly_score, _ = detector.update_and_detect(crowd_vector)

    # 7. Classify
    state, confidence, breakdown = _classifier.classify(
        gradient,
        velocity_var,
        anomaly_score,
        is_simulated=is_simulated,
        history_len=len(metrics.congestion_history),
        gradient_quality=gradient_quality,
        env_weather_risk=env_params.get('env_weather_risk', 0.0),
        env_width_factor=env_params.get('env_width_factor', 1.0),
        env_event_active=env_params.get('env_event_active', False),
    )

    risk_score   = breakdown.get('risk_score', {}).get('value', 0)
    interventions = _recommender.get_recommendations(state)

    # 8. Persist rolling state back to Redis
    save_location_state(location_name, metrics, detector)

    # 9. Write record to Supabase via Django ORM
    _write_to_db(lat, lon, location_name, congestion, current_speed,
                 gradient, velocity_var, anomaly_score, risk_score, state)

    # 10. Build and store result payload
    payload = {
        'status':        'done',
        'task_id':       task_id,
        'location':      location_name,
        'timestamp':     datetime.now(timezone.utc).isoformat(),
        'state':         state,
        'confidence':    round(confidence, 4),
        'risk_score':    risk_score,
        'congestion':    round(congestion, 4),
        'gradient':      round(gradient, 4),
        'velocity_var':  round(velocity_var, 4),
        'anomaly_score': round(anomaly_score, 4),
        'is_simulated':  is_simulated,
        'breakdown':     breakdown,
        'interventions': interventions,
    }
    store_result(task_id, location_name, payload)
    return payload


def _write_to_db(lat, lon, location_name, congestion, speed,
                 gradient, velocity_var, anomaly_score, risk_score, state):
    try:
        from api.models import CrowdTelemetry
        CrowdTelemetry.objects.create(
            location_name=location_name,
            latitude=lat,
            longitude=lon,
            congestion=congestion,
            speed=speed,
            gradient=gradient,
            velocity_var=velocity_var,
            anomaly_score=anomaly_score,
            risk_score=risk_score,
            state=state,
        )
    except Exception as exc:
        log.error(f"DB write failed: {exc}")


@shared_task(bind=True, max_retries=3)
def analyze_crowd(
    self,
    lat: float,
    lon: float,
    location_name: str,
    env_params: dict,
    task_id: str,
):
    acquired = acquire_lock(location_name)
    if not acquired:
        raise self.retry(
            countdown=2,
            exc=RuntimeError(f"Lock contention for '{location_name}'"),
        )
    try:
        return _run_pipeline(lat, lon, location_name, env_params, task_id)
    except Exception as exc:
        log.error(f"analyze_crowd failed for '{location_name}': {exc}")
        raise
    finally:
        release_lock(location_name)
```

- [ ] **Step 4: Run tests**

```bash
cd backend && python -m pytest tests/test_analyze_task.py -v
```

Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
git add backend/tasks/ backend/tests/test_analyze_task.py
git commit -m "feat: analyze_crowd Celery task — full 10-step pipeline"
```

---

## Task 10: /analyze and /result/{task_id} endpoints

**Files:**
- Modify: `backend/api/views.py`
- Modify: `backend/api/urls.py`
- Create: `backend/tests/test_api_async.py`

- [ ] **Step 1: Write failing tests**

`backend/tests/test_api_async.py`:
```python
import json
import uuid
from unittest.mock import patch, MagicMock
from django.test import TestCase, Client
from django.contrib.auth.models import User


class TestAnalyzeView(TestCase):
    def setUp(self):
        self.client = Client(enforce_csrf_checks=False)
        User.objects.create_user(username='admin', password='pass', is_staff=True)
        self.client.login(username='admin', password='pass')

    def _post(self, payload):
        return self.client.post(
            '/analyze',
            data=json.dumps(payload),
            content_type='application/json',
        )

    def test_returns_task_id_on_valid_payload(self):
        with patch('api.views.analyze_crowd') as mock_task:
            mock_async = MagicMock()
            mock_async.id = 'mock-id-001'
            mock_task.delay.return_value = mock_async
            resp = self._post({
                'lat': 28.6139, 'lon': 77.2090,
                'location_name': 'Delhi',
                'env_weather_risk': 0.0,
                'env_width_factor': 1.0,
                'env_event_active': False,
            })
        assert resp.status_code == 202
        assert resp.json()['task_id'] == 'mock-id-001'

    def test_returns_400_without_lat_lon(self):
        resp = self._post({'location_name': 'Delhi'})
        assert resp.status_code == 400

    def test_requires_auth(self):
        unauth = Client()
        resp = unauth.post('/analyze', data='{}', content_type='application/json')
        assert resp.status_code in (401, 403)


class TestResultView(TestCase):
    def setUp(self):
        self.client = Client(enforce_csrf_checks=False)
        User.objects.create_user(username='admin', password='pass', is_staff=True)
        self.client.login(username='admin', password='pass')

    def test_returns_pending_for_unknown_task(self):
        with patch('api.views.get_result', return_value=None):
            resp = self.client.get('/result/nonexistent-id')
        assert resp.status_code == 200
        assert resp.json()['status'] == 'pending'

    def test_returns_full_payload_when_done(self):
        mock_result = {
            'status': 'done', 'state': 'Stable',
            'risk_score': 10.0, 'task_id': 'abc-123',
        }
        with patch('api.views.get_result', return_value=mock_result):
            resp = self.client.get('/result/abc-123')
        assert resp.status_code == 200
        assert resp.json()['state'] == 'Stable'
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd backend && python -m pytest tests/test_api_async.py -v
```

Expected: FAIL — 404.

- [ ] **Step 3: Add AnalyzeView and ResultView to api/views.py**

Append to `backend/api/views.py` (after existing imports and views):

```python
import uuid
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

from tasks.analysis import analyze_crowd
from cache.result_store import get_result as _get_result


@method_decorator(csrf_exempt, name='dispatch')
class AnalyzeView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            body = json.loads(request.body)
        except (json.JSONDecodeError, UnicodeDecodeError):
            return Response({'error': 'Invalid JSON'}, status=400)

        lat = body.get('lat')
        lon = body.get('lon')
        if lat is None or lon is None:
            return Response({'error': 'lat and lon are required'}, status=400)

        location_name = body.get('location_name', 'Unknown')
        env_params = {
            'env_weather_risk': float(body.get('env_weather_risk', 0.0)),
            'env_width_factor': float(body.get('env_width_factor', 1.0)),
            'env_event_active': bool(body.get('env_event_active', False)),
        }

        task_id = str(uuid.uuid4())
        analyze_crowd.delay(
            lat=float(lat),
            lon=float(lon),
            location_name=location_name,
            env_params=env_params,
            task_id=task_id,
        )
        return Response({'task_id': task_id}, status=202)


class ResultView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, task_id: str):
        result = _get_result(task_id)
        if result is None:
            return Response({'status': 'pending', 'task_id': task_id})
        return Response(result)
```

- [ ] **Step 4: Update api/urls.py**

`backend/api/urls.py`:
```python
from django.urls import path
from .views import HistoryView, LatestView, AnalyzeView, ResultView

urlpatterns = [
    path('history',            HistoryView.as_view()),
    path('latest',             LatestView.as_view()),
    path('analyze',            AnalyzeView.as_view()),
    path('result/<str:task_id>', ResultView.as_view()),
]
```

- [ ] **Step 5: Run tests**

```bash
cd backend && python -m pytest tests/test_api_async.py -v
```

Expected: 5 passed.

- [ ] **Step 6: Run full test suite**

```bash
cd backend && python -m pytest tests/ -v
```

Expected: all tests pass.

- [ ] **Step 7: Commit**

```bash
git add backend/api/ backend/tests/test_api_async.py
git commit -m "feat: /analyze and /result/{task_id} async endpoints"
```

---

## Task 11: End-to-end smoke test (manual)

Prerequisites: Redis running locally. `.env` at project root with at minimum `REDIS_URL=redis://localhost:6379/0`.

- [ ] **Step 1: Start Redis**

```bash
redis-server --daemonize yes
```

- [ ] **Step 2: Migrate and seed**

```bash
cd backend
python manage.py migrate
python manage.py seed_users
```

Expected:
```
Created admin user: 'admin'
```

- [ ] **Step 3: Start Celery worker in a separate terminal**

```bash
cd backend && celery -A core worker --loglevel=info
```

- [ ] **Step 4: Start Django server in a separate terminal**

```bash
cd backend && python manage.py runserver
```

- [ ] **Step 5: Login**

```bash
curl -s -c /tmp/cpse-cookies.txt -X POST http://localhost:8000/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"username":"admin","password":"cpseisawesome"}' | python -m json.tool
```

Expected:
```json
{"username": "admin", "is_admin": true}
```

- [ ] **Step 6: Trigger analysis**

```bash
curl -s -b /tmp/cpse-cookies.txt -X POST http://localhost:8000/analyze \
  -H 'Content-Type: application/json' \
  -d '{"lat":28.6139,"lon":77.2090,"location_name":"Delhi","env_weather_risk":0.0,"env_width_factor":1.0,"env_event_active":false}' \
  | python -m json.tool
```

Expected:
```json
{"task_id": "<some-uuid>"}
```

- [ ] **Step 7: Poll for result (replace UUID)**

```bash
curl -s -b /tmp/cpse-cookies.txt \
  http://localhost:8000/result/<task-id-from-step-6> | python -m json.tool
```

Expected (within ~3s of task dispatch):
```json
{
  "status": "done",
  "state": "Stable",
  "risk_score": ...,
  "congestion": ...,
  "interventions": {...}
}
```

- [ ] **Step 8: Check history**

```bash
curl -s -b /tmp/cpse-cookies.txt 'http://localhost:8000/history?limit=3' | python -m json.tool
```

Expected: JSON array with at least 1 record.

- [ ] **Step 9: Clean up and final commit**

```bash
rm -f /tmp/cpse-cookies.txt
git add .
git commit -m "chore: backend restructure complete — smoke test verified"
```

---

## Self-Review

### Spec coverage

| CLAUDE.md requirement | Task |
|---|---|
| Django project skeleton (`core/`) | Task 2 |
| `backend/services/` extraction | Task 3 |
| `config.yaml` path resolution | Task 3 Step 2 |
| Remove Streamlit from `weather.py` | Task 3 Step 3 |
| `SUPABASE_DB_URL` in `database.py` | Task 3 Step 4 |
| `CrowdTelemetry` + `AnalysisTask` ORM | Task 4 |
| `POST /auth/login`, `POST /auth/logout` | Task 5 |
| `seed_users` management command | Task 5 |
| `GET /history`, `GET /latest` | Task 6 |
| Celery app + Redis broker | Task 7 |
| Redis key helpers + state serialization | Task 8 |
| `analyze_crowd` full 10-step pipeline | Task 9 |
| `POST /analyze`, `GET /result/{task_id}` | Task 10 |
| End-to-end verification | Task 11 |

### Gaps (acceptable for this plan)

- **CORS headers** are configured in settings and installed but not tested — validated during frontend integration.
- **`AnalysisTask` write** on task completion is not implemented (only `CrowdTelemetry` is written). This is a minor enhancement: if needed, add `AnalysisTask.objects.create(task_id=task_id, status='done', location_name=location_name, result_json=payload)` inside `_run_pipeline` after `store_result`.
- **Supabase connection in tests** falls back to SQLite (no `SUPABASE_DB_URL` set in test env). `CrowdTelemetry` is `managed=False` so no migration touches it — `_write_to_db` calls in tests are mocked.
