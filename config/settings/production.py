from django.core.exceptions import ImproperlyConfigured
from .base import *  # noqa: F403

DEBUG = False
if len(SECRET_KEY) < 50 or SECRET_KEY.startswith('development-'):  # noqa: F405
    raise ImproperlyConfigured('Set a unique SECRET_KEY of at least 50 characters.')
if DATABASES['default']['ENGINE'] != 'django.db.backends.postgresql':  # noqa: F405
    raise ImproperlyConfigured('Production requires PostgreSQL via DATABASE_URL.')
if not env('ALLOWED_HOSTS', default=''):  # noqa: F405
    raise ImproperlyConfigured('Set explicit ALLOWED_HOSTS.')
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = False
SECURE_CONTENT_TYPE_NOSNIFF = True
# Enable only behind a trusted proxy that overwrites this header.
if env.bool('TRUST_PROXY_SSL_HEADER', default=False):  # noqa: F405
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SECURE_REDIRECT_EXEMPT = [r'^healthz/$']
