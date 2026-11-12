"""Move the foundation and every programme site to a new domain/port in one step.

    python manage.py set_site_domain --domain gecpfoundation.org --port 443 --dry-run
    python manage.py set_site_domain --domain gecpfoundation.org --port 443

The foundation site's hostname becomes DOMAIN and each "<code>.<old domain>" programme site
becomes "<code>.DOMAIN". Pages, programmes and content are untouched: only Wagtail Site
hostnames and ports change. Use this instead of reseeding when moving from localhost to the
real domain (or between domains).
"""
import re

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from wagtail.models import Site

from apps.programmes.models import Foundation

HOSTNAME = re.compile(r'^(?=.{1,253}$)([a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)*[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$')


class Command(BaseCommand):
    help = 'Change the hostname/port of the foundation and all programme sites together.'

    def add_arguments(self, parser):
        parser.add_argument('--domain', required=True, help='Foundation hostname, e.g. gecpfoundation.org')
        parser.add_argument('--port', type=int, default=443, help='443 for HTTPS (default), 8000 locally.')
        parser.add_argument('--dry-run', action='store_true', help='Show the changes without saving them.')

    @transaction.atomic
    def handle(self, *args, domain, port, dry_run=False, **options):
        domain = domain.lower().strip().rstrip('.')
        if not HOSTNAME.match(domain):
            raise CommandError('--domain must be a hostname only: no scheme, path or port.')
        if not 1 <= port <= 65535:
            raise CommandError('--port must be between 1 and 65535.')
        foundation = Foundation.objects.select_related('site').first()
        if foundation is None or foundation.site is None:
            raise CommandError('No foundation site yet. Seed first: scripts/seed_all.py --domain '
                               f'{domain} --port {port} --settings config.settings.production')

        old_root = foundation.site.hostname
        changes = []
        for site in Site.objects.order_by('hostname'):
            if site.hostname == old_root:
                new_host = domain
            elif site.hostname.endswith('.' + old_root):
                new_host = site.hostname[: -len(old_root)] + domain
            else:
                self.stdout.write(f'  leaving {site.hostname}:{site.port} (not under {old_root})')
                continue
            changes.append((site, new_host))

        moving = {site.pk for site, _ in changes}
        for site, new_host in changes:
            clash = Site.objects.filter(hostname=new_host, port=port).exclude(pk__in=moving).first()
            if clash:
                raise CommandError(f'{new_host}:{port} is already used by another site ("{clash.site_name}"). '
                                   'Remove or rename it in the Wagtail admin first.')

        for site, new_host in changes:
            self.stdout.write(f'  {site.hostname}:{site.port}  ->  {new_host}:{port}')
        if dry_run:
            transaction.set_rollback(True)
            self.stdout.write(self.style.WARNING(f'Dry run: {len(changes)} sites would change. Nothing saved.'))
            return
        # Two passes so swapping hostnames between sites can never hit the unique constraint.
        for index, (site, _) in enumerate(changes):
            site.hostname, site.port = f'moving-{index}.invalid', port
            site.save(update_fields=['hostname', 'port'])
        for site, new_host in changes:
            site.hostname = new_host
            site.save(update_fields=['hostname'])
        Site.clear_site_root_paths_cache()
        self.stdout.write(self.style.SUCCESS(f'Moved {len(changes)} sites to {domain}:{port}. '
                                             'Add every hostname in the hosting panel and DNS too.'))
