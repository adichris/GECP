from .dev import *  # noqa: F403
DATABASES = {'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': ':memory:'}}
PASSWORD_HASHERS = ['django.contrib.auth.hashers.MD5PasswordHasher']
ALLOWED_HOSTS = ['testserver', 'localhost', '.localhost', '127.0.0.1']
EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'
