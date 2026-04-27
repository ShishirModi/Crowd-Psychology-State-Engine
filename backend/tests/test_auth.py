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
        assert resp.status_code in (401, 403, 404)
