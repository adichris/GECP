from .dev import *  # noqa: F403
ALLOWED_HOSTS = ['localhost', '.localhost', 'testserver']
PASSWORD_HASHERS = ['django.contrib.auth.hashers.MD5PasswordHasher']
EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'
