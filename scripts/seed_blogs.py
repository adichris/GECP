"""Standalone entry point; accepts all options of manage.py seed_blogs."""
import os
from pathlib import Path
import sys


def main():
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.dev')
    from django.core.management import execute_from_command_line
    execute_from_command_line([sys.argv[0], 'seed_blogs', *sys.argv[1:]])


if __name__ == '__main__':
    main()
