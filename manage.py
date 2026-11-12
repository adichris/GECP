import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
VENV = BASE_DIR / '.venv'


def use_project_venv():
    """Re-run with the project's .venv when started by another interpreter (e.g. plain `python`
    on the server), so the installed requirements are always available."""
    if os.name != 'posix' or os.environ.get('GECP_VENV_REEXEC'):
        return
    venv_python = VENV / 'bin' / 'python'
    if not venv_python.exists() or Path(sys.prefix).resolve() == VENV.resolve():
        return
    os.environ['GECP_VENV_REEXEC'] = '1'  # never loop
    os.execv(str(venv_python), [str(venv_python), *sys.argv])


def settings_from_dotenv():
    """DJANGO_SETTINGS_MODULE from .env, so the server's .env selects production settings."""
    try:
        lines = (BASE_DIR / '.env').read_text(encoding='utf-8').splitlines()
    except OSError:
        return None
    for line in lines:
        key, sep, value = line.strip().partition('=')
        if sep and key.strip().removeprefix('export ').strip() == 'DJANGO_SETTINGS_MODULE':
            return value.strip().strip('"\'') or None
    return None


if __name__ == '__main__':
    use_project_venv()
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', settings_from_dotenv() or 'config.settings.dev')
    from django.core.management import execute_from_command_line
    execute_from_command_line(sys.argv)
