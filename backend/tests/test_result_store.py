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
        assert list(m2.congestion_history) == list(m.congestion_history)
        assert list(m2.speed_history) == list(m.speed_history)
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
