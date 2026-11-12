"""config/settings/local.py loading. The real local.py (your machine's database and email
settings) is never read or written: each check runs in a fresh interpreter where an import hook
supplies a simulated local.py, or simulates its absence."""
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PRODUCTION_ENV = {'SECRET_KEY': 'x' * 60, 'DATABASE_URL': 'postgres://u:p@localhost:5432/db',
                  'ALLOWED_HOSTS': 'example.org'}
HOOK = '''
import importlib.abc, importlib.util, sys
SOURCE = {source!r}
class SimulatedLocal(importlib.abc.MetaPathFinder, importlib.abc.Loader):
    def find_spec(self, name, path, target=None):
        if name != 'config.settings.local':
            return None
        if SOURCE is None:
            raise ModuleNotFoundError("No module named 'config.settings.local'", name=name)
        return importlib.util.spec_from_loader(name, self)
    def create_module(self, spec):
        return None
    def exec_module(self, module):
        exec(SOURCE, module.__dict__)
sys.meta_path.insert(0, SimulatedLocal())
import django
django.setup()
from django.conf import settings
print(repr({expression}))
'''


def settings_value(module, expression, local_source=None, extra_env=None):
    env = {**os.environ, 'DJANGO_SETTINGS_MODULE': module, **(extra_env or {})}
    code = HOOK.format(source=local_source, expression=expression)
    result = subprocess.run([sys.executable, '-c', code], cwd=ROOT, env=env, capture_output=True, text=True)
    return result.stdout.strip() or result.stderr.strip().splitlines()[-1]


def test_local_py_overrides_database_and_email():
    source = ("DATABASES = {'default': {'ENGINE': 'django.db.backends.postgresql', 'NAME': 'mine', 'HOST': 'db.local'}}\n"
              "EMAIL_HOST = 'mail.local'\nEMAIL_PORT = 1025\n")
    out = settings_value('config.settings.dev', "(settings.DATABASES['default']['NAME'], "
                         "settings.DATABASES['default']['HOST'], settings.EMAIL_HOST, settings.EMAIL_PORT)", source)
    assert out == "('mine', 'db.local', 'mail.local', 1025)"


def test_local_py_overrides_app_options():
    source = 'SERVE_MEDIA = False\nSUBMISSION_NOTIFY_EMAILS = ["team@example.org"]\n'
    assert settings_value('config.settings.dev', '(settings.SERVE_MEDIA, settings.SUBMISSION_NOTIFY_EMAILS)',
                          source) == "(False, ['team@example.org'])"


def test_defaults_without_local_py():
    assert settings_value('config.settings.dev', 'settings.SERVE_MEDIA') == 'True'


def test_test_settings_ignore_local_py():
    assert settings_value('config.settings.test', 'settings.SERVE_MEDIA', 'SERVE_MEDIA = False\n') == 'True'


def test_production_applies_local_py_but_keeps_safety_rules():
    source = 'SERVE_MEDIA = False\nDEBUG = True\n'
    assert settings_value('config.settings.production', '(settings.SERVE_MEDIA, settings.DEBUG)', source,
                          PRODUCTION_ENV) == '(False, False)'


def test_production_still_rejects_weak_settings_from_local_py():
    out = settings_value('config.settings.production', 'settings.DEBUG', "SECRET_KEY = 'short'\n", PRODUCTION_ENV)
    assert 'ImproperlyConfigured' in out


def test_broken_local_py_is_reported_not_ignored():
    out = settings_value('config.settings.dev', 'settings.DEBUG', 'import module_that_does_not_exist\n')
    assert "No module named 'module_that_does_not_exist'" in out
