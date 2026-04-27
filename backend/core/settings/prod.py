import os
from .base import *  # noqa: F401, F403

DEBUG = False
ALLOWED_HOSTS = ['localhost', '127.0.0.1'] + [
    h for h in os.environ.get('ALLOWED_HOSTS', '').split(',') if h
]
CORS_ALLOW_ALL_ORIGINS = False
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
