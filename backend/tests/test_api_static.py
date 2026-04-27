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
            # DRF renders None as empty body, not as 'null'
            assert resp.content == b''

    def test_returns_cached_result(self):
        cached = json.dumps({'state': 'Stable', 'risk_score': 5.0})
        with patch('api.views._redis') as mock_redis_fn:
            mock_redis_fn.return_value.get.return_value = cached
            resp = self.client.get('/latest?location=Delhi')
        assert resp.status_code == 200
        assert resp.json()['state'] == 'Stable'
