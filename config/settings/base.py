from pathlib import Path
import importlib
import environ

BASE_DIR = Path(__file__).resolve().parents[2]
env = environ.Env(DEBUG=(bool, False))
environ.Env.read_env(BASE_DIR / '.env')
SECRET_KEY = env('SECRET_KEY', default='development-only-change-this-before-deployment')
DEBUG = env('DEBUG')
ALLOWED_HOSTS = env.list('ALLOWED_HOSTS', default=['localhost', '.localhost', '127.0.0.1'])
CSRF_TRUSTED_ORIGINS = env.list('CSRF_TRUSTED_ORIGINS', default=[])
INSTALLED_APPS = [
    'apps.core', 'apps.programmes', 'apps.news', 'apps.events',
    'apps.opportunities', 'apps.resources', 'apps.partners', 'apps.engagement', 'apps.community', 'apps.staff',
    'wagtail.contrib.forms', 'wagtail.contrib.redirects', 'wagtail.contrib.settings',
    'wagtail.embeds', 'wagtail.sites', 'wagtail.users', 'wagtail.snippets',
    'wagtail.documents', 'wagtail.images', 'wagtail.search', 'wagtail.admin', 'wagtail',
    'modelcluster', 'taggit', 'crispy_forms', 'crispy_tailwind',
    'django.contrib.admin', 'django.contrib.auth', 'django.contrib.contenttypes',
    'django.contrib.sessions', 'django.contrib.messages', 'django.contrib.staticfiles',
    'django.contrib.sitemaps',
]
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'apps.core.middleware.StrictSiteMiddleware',
    'wagtail.contrib.redirects.middleware.RedirectMiddleware',
]
ROOT_URLCONF = 'config.urls'
TEMPLATES = [{
    'BACKEND': 'django.template.backends.django.DjangoTemplates',
    'DIRS': [BASE_DIR / 'templates'], 'APP_DIRS': True,
    'OPTIONS': {'context_processors': [
        'django.template.context_processors.request',
        'django.contrib.auth.context_processors.auth',
        'django.contrib.messages.context_processors.messages',
        'apps.core.context_processors.site_context',
    ]},
}]
WSGI_APPLICATION = 'config.wsgi.application'
DATABASES = {'default': env.db('DATABASE_URL', default=f'sqlite:///{BASE_DIR / "db.sqlite3"}')}
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]
LANGUAGE_CODE = 'en-gb'
TIME_ZONE = 'Africa/Accra'
USE_I18N = True
USE_TZ = True
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'
# Production media: Django serves these public image folders itself unless SERVE_MEDIA = False
# in local.py (set that when nginx or an alwaysdata static site already handles /media/).
# Documents are never served from /media/; they go through Wagtail's /documents/ views.
SERVE_MEDIA = True
PUBLIC_MEDIA_PREFIXES = ('images/', 'staff/photos/', 'staff/portfolio/')
MEDIA_CACHE_SECONDS = 60 * 60 * 24 * 30
STORAGES = {
    'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
    'staticfiles': {'BACKEND': 'whitenoise.storage.CompressedManifestStaticFilesStorage'},
}
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
WAGTAIL_SITE_NAME = 'GECP Digital Platform'
WAGTAILADMIN_BASE_URL = env('ADMIN_BASE_URL', default='http://localhost:8000')
WAGTAILSEARCH_BACKENDS = {'default': {'BACKEND': 'wagtail.search.backends.database'}}
WAGTAILDOCS_SERVE_METHOD = 'serve_view'
WAGTAILIMAGES_MAX_UPLOAD_SIZE = 10 * 1024 * 1024
WAGTAILDOCS_MAX_UPLOAD_SIZE = 20 * 1024 * 1024
WAGTAILDOCS_EXTENSIONS = ['pdf', 'docx', 'xlsx', 'pptx', 'txt', 'csv']
CRISPY_ALLOWED_TEMPLATE_PACKS = 'tailwind'
CRISPY_TEMPLATE_PACK = 'tailwind'
EMAIL_BACKEND = env('EMAIL_BACKEND', default='django.core.mail.backends.console.EmailBackend')
DEFAULT_FROM_EMAIL = env('DEFAULT_FROM_EMAIL', default='webmaster@localhost')
DATA_UPLOAD_MAX_MEMORY_SIZE = 2 * 1024 * 1024
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
CSRF_COOKIE_SAMESITE = 'Lax'
X_FRAME_OPTIONS = 'DENY'
LOGGING = {
    'version': 1, 'disable_existing_loggers': False,
    'handlers': {'console': {'class': 'logging.StreamHandler'}},
    'root': {'handlers': ['console'], 'level': 'INFO'},
    'loggers': {'django.tasks': {'level': 'WARNING'}, 'django_tasks': {'level': 'WARNING'}},
}

LOGIN_URL = '/accounts/login/'
LOGIN_REDIRECT_URL = '/community/my-activity/'
LOGOUT_REDIRECT_URL = '/community/'
EMAIL_HOST = env('EMAIL_HOST', default='localhost')
EMAIL_PORT = env.int('EMAIL_PORT', default=587)
EMAIL_HOST_USER = env('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = env('EMAIL_HOST_PASSWORD', default='')
EMAIL_USE_TLS = env.bool('EMAIL_USE_TLS', default=True)
EMAIL_TIMEOUT = 15
TRUSTED_PROXY_IPS = env.list('TRUSTED_PROXY_IPS', default=[])
# Enable only behind a trusted proxy that overwrites X-Forwarded-Proto (applied in production.py).
TRUST_PROXY_SSL_HEADER = env.bool('TRUST_PROXY_SSL_HEADER', default=False)
# Submission emails: a reference receipt to the visitor, and an alert to these addresses plus the site's branding email.
# Submission notifications (override in local.py).
SUBMISSION_EMAILS_ENABLED = True
SUBMISSION_NOTIFY_EMAILS = []


def local_overrides():
    """Settings from config/settings/local.py (git-ignored), or {} when there is none.

    Secrets and infrastructure come from .env / the environment; local.py is the place for
    per-machine and per-server choices. It is applied last, so it can override anything.
    """
    try:
        module = importlib.import_module('config.settings.local')
    except ModuleNotFoundError as exc:
        if exc.name != 'config.settings.local':
            raise  # local.py exists but imports something missing: surface that error
        return {}
    return {name: value for name, value in vars(module).items() if name.isupper()}
