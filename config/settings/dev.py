import os

from .base import *  # noqa: F403
DEBUG = True
STORAGES['staticfiles'] = {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'}  # noqa: F405

# Personal overrides from config/settings/local.py. The test and CI settings import this module,
# so they skip local.py to stay reproducible on every machine.
if os.environ.get('DJANGO_SETTINGS_MODULE', '').rsplit('.', 1)[-1] not in {'test', 'ci'}:
    globals().update(local_overrides())  # noqa: F405
