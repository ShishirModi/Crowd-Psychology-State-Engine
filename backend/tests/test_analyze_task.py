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
