import os
from celery import Celery

# Defaults to dev; production systemd unit must set DJANGO_SETTINGS_MODULE=core.settings.prod
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings.dev')
app = Celery('cpse')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()
