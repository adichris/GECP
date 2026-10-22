from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils.html import escape
from wagtail.models import Page
from apps.core.models import HomePage
from apps.engagement.intake import PROGRAMME_INTAKE
from apps.news.models import NewsPage
from apps.programmes.editorial import PROFILES
from apps.programmes.foundation_blogs import FOUNDATION_BLOGS
from apps.programmes.models import Foundation, Programme


class Command(BaseCommand):
    help = 'Seed 3 GECP and 22 programme blog pages, keeping existing drafts and edited posts unchanged.'

    def add_arguments(self, parser):
        parser.add_argument('--sites', nargs='+', default=['all'], help='all, gecp, or programme codes, e.g. --sites wwi gccs pec')
        parser.add_argument('--draft', action='store_true', help='Create new posts as unpublished drafts for editorial review.')
        parser.add_argument('--dry-run', action='store_true', help='Validate destinations and show the plan without writing anything.')

    @transaction.atomic
    def handle(self, *args, **options):
        requested = list(dict.fromkeys(code.lower() for code in options['sites']))
        allowed = ['gecp', *PROFILES]
        if requested == ['all']:
            requested = allowed
        elif any(code not in allowed for code in requested):
            raise CommandError('Use --sites all, or one or more of: ' + ', '.join(allowed))
        planned = []
        for code in requested:
            if code == 'gecp':
                foundations = list(Foundation.objects.select_related('site__root_page')[:2])
                if len(foundations) != 1:
                    raise CommandError('Expected one GECP foundation. Run scripts/seed_all.py first or inspect the foundation registry.')
                site, entries = foundations[0].site, FOUNDATION_BLOGS
            else:
                programme = Programme.objects.select_related('site__root_page').filter(code=code).first()
                if programme is None:
                    raise CommandError(f'Missing programme {code}. Run scripts/seed_all.py first.')
                site, entries = programme.site, PROFILES[code]['blogs']
            home = site.root_page.specific
            if not isinstance(home, HomePage):
                raise CommandError(f'{code} does not have a GECP homepage root.')
            for slug, title, topic, sections in entries:
                existing = Page.objects.child_of(home).filter(slug=slug).first()
                if existing and not isinstance(existing.specific, NewsPage):
                    raise CommandError(f'{code}/{slug} is already used by another page type. Resolve the conflict before seeding.')
                planned.append((code, home, slug, title, topic, sections, existing))
        created = preserved = 0
        for code, home, slug, title, topic, sections, existing in planned:
            if existing:
                preserved += 1
                self.stdout.write(f'KEEP {code}/{slug}')
                continue
            created += 1
            self.stdout.write(f'{"PLAN" if options["dry_run"] else "CREATE"} {code}/{slug}')
            if options['dry_run']:
                continue
            body = ''.join(f'<h2>{escape(heading)}</h2><p>{escape(text)}</p>' for heading, text in sections)
            path = '/contact/' if code == 'gecp' else f'/participate/{PROGRAMME_INTAKE[code]}/'
            body += f'<h2>Continue the conversation</h2><p><a href="{path}">Contact {escape(code.upper())} about your interests</a></p>'
            page = home.add_child(instance=NewsPage(slug=slug, title=title, content_kind='blog', topic=topic,
                summary=sections[0][1], body=body, search_description=f'{topic}: {title}', live=False))
            revision = page.save_revision()
            if not options['draft']:
                revision.publish()
        self.stdout.write(self.style.SUCCESS(f'{"Planned" if options["dry_run"] else "Created"}: {created}; preserved: {preserved}; sites: {len(requested)}.'))
