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
    # 1. Fetch telemetry
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

    risk_score    = breakdown.get('risk_score', {}).get('value', 0)
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
