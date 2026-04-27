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
