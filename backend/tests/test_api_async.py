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
