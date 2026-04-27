def test_celery_app_name():
    from core.celery import app
    assert app.main == 'cpse'


def test_celery_broker_is_redis():
    from django.conf import settings
    assert settings.CELERY_BROKER_URL.startswith('redis://')


def test_celery_result_backend_is_redis():
    from django.conf import settings
    assert settings.CELERY_RESULT_BACKEND.startswith('redis://')
