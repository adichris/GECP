"""Run from any directory: python /path/to/gecp-platform/scripts/seed_all.py."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]


def validate_assets(folder):
    """Validate all bundled originals before any database changes."""
    manifest = json.loads((folder / 'manifest.json').read_text(encoding='utf-8'))
    illustration = json.loads((folder / 'illustration-provenance.json').read_text(encoding='utf-8'))
    entries = [*manifest, illustration]
    seen = set()
    for entry in entries:
        name = entry['file']
        path = (folder / name).resolve()
        if path.parent != folder.resolve() or name in seen:
            raise ValueError(f'Invalid or duplicate asset filename: {name}')
        seen.add(name)
        if not path.is_file():
            raise ValueError(f'Missing asset: {name}')
        if hashlib.sha256(path.read_bytes()).hexdigest() != entry['sha256']:
            raise ValueError(f'Asset checksum mismatch: {name}')
    return entries


def main(argv=None):
    parser = argparse.ArgumentParser(description='Seed GECP Foundation, all 11 programmes, editorial content, permissions and bundled assets.')
    parser.add_argument('--domain', default='localhost', help='Foundation hostname, without scheme or port.')
    parser.add_argument('--port', type=int, default=8000, help='Wagtail site port: 8000 locally, 443 for HTTPS.')
    parser.add_argument('--settings', help='Django settings module; otherwise use the environment or config.settings.dev.')
    parser.add_argument('--skip-assets', action='store_true', help='Seed data only; omit media validation/import.')
    parser.add_argument('--check-assets', action='store_true', help='Verify media checksums and exit without accessing the database.')
    parser.add_argument('--no-migrate', action='store_true', help='Require migrations to have already been applied.')
    parser.add_argument('--report', type=Path, help='Optional destination for a JSON inventory report.')
    args = parser.parse_args(argv)
    domain = args.domain.lower().strip()
    if not re.fullmatch(r'[a-z0-9](?:[a-z0-9.-]*[a-z0-9])?', domain) or '..' in domain or any(not label or len(label) > 63 or label.startswith('-') or label.endswith('-') for label in domain.split('.')) or len(domain) > 253:
        parser.error('--domain must be a valid hostname without a scheme, path or port.')
    if not 1 <= args.port <= 65535:
        parser.error('--port must be between 1 and 65535.')
    if args.skip_assets and args.check_assets:
        parser.error('--skip-assets and --check-assets cannot be combined.')
    entries = []
    if not args.skip_assets:
        entries = validate_assets(ROOT / 'seed_assets')
        print(f'Verified {len(entries)} bundled media files.')
    if args.check_assets:
        return 0

    sys.path.insert(0, str(ROOT))
    if args.settings:
        os.environ['DJANGO_SETTINGS_MODULE'] = args.settings
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.dev')
    import django
    django.setup()
    from django.core.management import call_command
    from django.db import connection
    from django.db.migrations.executor import MigrationExecutor
    call_command('check')
    if args.no_migrate:
        executor = MigrationExecutor(connection)
        if executor.migration_plan(executor.loader.graph.leaf_nodes()):
            raise ValueError('Unapplied migrations found. Run without --no-migrate first.')
    else:
        call_command('migrate', interactive=False)

    from apps.programmes.models import Foundation, Programme
    from apps.resources.models import LibraryAsset
    existing = Foundation.objects.select_related('site').first()
    if existing and (existing.site.hostname, existing.site.port) != (domain, args.port):
        raise ValueError(f'Existing foundation is {existing.site.hostname}:{existing.site.port}. Use those values; change hostnames in Wagtail when moving domains.')
    # Existing command wraps database seeding in a transaction and preserves pages.
    call_command('seed_gecp', domain=domain, port=args.port, skip_assets=args.skip_assets)
    call_command('update_index')
    foundation = Foundation.objects.get(site__hostname=domain, site__port=args.port)
    programmes = list(Programme.objects.filter(foundation=foundation).select_related('site').order_by('code'))
    site_ids = [foundation.site_id, *[p.site_id for p in programmes]]
    report = {
        'foundation': foundation.site.root_url,
        'programmes': [{'code': p.code, 'name': p.name, 'url': p.site.root_url, 'initiatives': p.initiatives.count()} for p in programmes],
        'library_assets': list(LibraryAsset.objects.filter(sites__in=site_ids).distinct().values_list('slug', flat=True)),
        'validated_asset_files': len(entries),
        'assets_skipped': args.skip_assets,
    }
    from apps.programmes.catalogue import CATALOGUE
    if set(CATALOGUE) - {p.code for p in programmes}:
        raise ValueError('Some expected programme sites are missing; inspect the programme registry.')
    if not args.skip_assets:
        missing = {Path(entry['file']).stem for entry in entries} - set(report['library_assets'])
        if missing:
            raise ValueError(f'Media library import is incomplete: {sorted(missing)}')
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(report, indent=2))
    print('Seed complete. No user accounts or passwords were created.')
    return 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f'Seed failed: {exc}', file=sys.stderr)
        raise SystemExit(1)
