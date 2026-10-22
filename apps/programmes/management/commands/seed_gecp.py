from datetime import timedelta
from django.contrib.auth.models import Group, Permission
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
from wagtail.models import Page, Site, GroupPagePermission, Collection, GroupCollectionPermission
from apps.core.models import HomePage, StandardPage, SiteBranding, NavigationLink
from apps.programmes.models import Foundation, Programme, Initiative, Project, Activity
from apps.news.models import NewsPage
from apps.events.models import EventPage
from apps.opportunities.models import OpportunityPage
from apps.resources.models import ResourcePage
from apps.partners.models import Partner

from apps.programmes.catalogue import CATALOGUE, FOUNDATION

def publish(parent, model, slug, **fields):
    page = model.objects.child_of(parent).filter(slug=slug).first()
    if page is None:
        page = parent.add_child(instance=model(slug=slug, **fields))
        page.save_revision().publish()
    return page

class Command(BaseCommand):
    help = 'Create idempotent demonstration sites and editor groups; never creates users or passwords.'
    def add_arguments(self, parser):
        parser.add_argument('--domain', default='localhost')
        parser.add_argument('--port', type=int, default=8000)
        parser.add_argument('--skip-assets', action='store_true', help='Skip importing the supplied original logos.')

    @transaction.atomic
    def handle(self, *args, **options):
        domain, port = options['domain'].lower(), options['port']
        if '://' in domain or '/' in domain or ':' in domain:
            raise CommandError('Use a hostname only; specify the port separately.')
        root = Page.get_first_root_node()
        home = publish(root, HomePage, 'gecp', title='GECP Foundation', introduction=FOUNDATION['intro'], hero_title='Aspiring for action. Inspiring for impact.')
        placeholder = Site.objects.filter(hostname='localhost', port=80, root_page__slug='home').first()
        if placeholder and not Foundation.objects.exists() and not placeholder.root_page.get_children().exists():
            placeholder.hostname = domain
            placeholder.port = port
            placeholder.root_page = home
            placeholder.site_name = 'GECP Foundation'
            placeholder.save()
        site, created = Site.objects.get_or_create(hostname=domain, port=port, defaults={'root_page': home, 'site_name': 'GECP Foundation', 'is_default_site': not Site.objects.filter(is_default_site=True).exists()})
        # A fresh Wagtail migration creates a placeholder localhost:80 site.
        if site.root_page_id != home.pk:
            if site.root_page.slug == 'home' and site.root_page.get_children().count() == 0:
                site.root_page = home
                site.site_name = 'GECP Foundation'
                site.save()
            else:
                raise CommandError('The requested foundation hostname already has unrelated content.')
        foundation, _ = Foundation.objects.get_or_create(site=site, defaults={'name': 'GECP Foundation'})
        self.configure(site, home, 'GECP Foundation', FOUNDATION['tagline'], 'corporate', '#12385B')
        self.content(home, 'GECP')
        for code, entry in CATALOGUE.items():
            name, description, theme, colour = entry['name'], entry['description'], entry['theme'], entry['colour']
            programme_home = publish(root, HomePage, code, title=name, hero_title=entry['hero'], introduction=description, eyebrow=f'{code.upper()} · A GECP Foundation programme')
            programme_site, _ = Site.objects.get_or_create(hostname=f'{code}.{domain}', port=port, defaults={'root_page': programme_home, 'site_name': name})
            if programme_site.root_page_id != programme_home.pk:
                raise CommandError(f'Existing site {programme_site.hostname} has a different root.')
            programme, _ = Programme.objects.get_or_create(code=code, defaults={'foundation': foundation, 'site': programme_site, 'name': name, 'description': description})
            if programme.site_id != programme_site.pk:
                raise CommandError('Seed data already exists on a different domain. Edit site hostnames in Wagtail instead of reseeding a new domain.')
            self.configure(programme_site, programme_home, code.upper() if code != 'eraid' else 'ERAid', entry['tagline'], theme, colour)
            self.content(programme_home, code.upper())
            for initiative_name, initiative_description in entry['initiatives']:
                Initiative.objects.get_or_create(programme=programme, name=initiative_name, defaults={'description': initiative_description})
            # A clearly labelled sample gives the complete hierarchy a runnable example.
            initiative = programme.initiatives.first()
            project, _ = Project.objects.get_or_create(initiative=initiative, name='Demonstration delivery pilot', defaults={'description': 'Sample project for testing the hierarchy; not a scheduled public programme.'})
            Activity.objects.get_or_create(project=project, name='Demonstration planning session')
            self.permissions(code, programme_home)
        gccs = Programme.objects.get(code='gccs')
        for name, code in [('RENGTECH Initiative', 'rengtech'), ('Ghanaian Senior Experts Volunteer Service (GSEVS)', 'gsevs'), ('Tacit Knowledge Research & Documentation (TKRD)', 'tkrd')]:
            Initiative.objects.filter(programme=gccs, name=name, linked_site__isnull=True).update(linked_site=Programme.objects.get(code=code).site)
        self.wwi_projects()
        if not options['skip_assets']:
            from django.core.management import call_command
            call_command('import_gecp_assets')
        from django.core.management import call_command
        call_command('enrich_gecp', skip_assets=options['skip_assets'])
        call_command('seed_programme_editorial')
        call_command('seed_blogs', sites=['gecp'])
        self.stdout.write(self.style.SUCCESS(f'GECP plus {len(CATALOGUE)} programme sites ready. Sample content is clearly marked; no user accounts were created.'))

    def configure(self, site, home, name, tagline, theme, colour):
        branding, _ = SiteBranding.objects.get_or_create(site=site, defaults={'display_name': name, 'tagline': tagline, 'default_theme': theme, 'primary_color': colour})
        about = publish(home, StandardPage, 'about', title=f'About {name}', body=f'<p>{home.introduction}</p><p>{tagline}</p><p>Programme descriptions are working editorial copy drawn from GECP planning materials. Confirm current service availability with the team.</p>')
        publish(home, StandardPage, 'privacy', title='Privacy information', body='<p>Demonstration privacy notice: form submissions are stored by this platform so the site team can respond. Before launch, publish the responsible organisation, contact, purpose, retention period and applicable rights. Do not collect real applications until this notice is approved.</p>')
        NavigationLink.objects.get_or_create(branding=branding, label='About', defaults={'page': about, 'sort_order': 0})

    def content(self, home, code):
        today = timezone.localdate()
        publish(home, NewsPage, 'welcome', title=f'{code}: opening new pathways', summary='Sample story: meet a platform built around learning, skills and community.', body='<p>Demonstration content for editorial review. Add an approved story, photographs and programme updates here.</p>')
        publish(home, OpportunityPage, 'discovery-session', title=f'{code} skills discovery session', summary='Demonstration opportunity for testing the application journey. This is not a live recruitment call.', body='<p>This sample shows how people can discover an opportunity and submit an application.</p>', deadline=today + timedelta(days=90))
        publish(home, EventPage, 'community-open-day', title=f'{code} community open day', summary='A demonstration event. Date and venue require editorial approval.', starts_at=timezone.now() + timedelta(days=30), ends_at=timezone.now() + timedelta(days=30, hours=2), location='To be confirmed — demonstration only')
        publish(home, ResourcePage, 'getting-started', title=f'Getting started with {code}', summary='A sample resource page, ready for an approved guide or publication.', body='<p>Editors can attach a document or link to an approved resource.</p>')
        partner, _ = Partner.objects.get_or_create(name='Demonstration community partner')
        partner.sites.add(Site.objects.get(root_page=home))

    def permissions(self, code, home):
        group, _ = Group.objects.get_or_create(name=f'{code.upper()} editors')
        for codename in ['add_page', 'change_page', 'publish_page']:
            permission = Permission.objects.get(content_type__app_label='wagtailcore', codename=codename)
            GroupPagePermission.objects.get_or_create(group=group, page=home, permission=permission)
        group.permissions.add(Permission.objects.get(content_type__app_label='wagtailadmin', codename='access_admin'))
        for model in ['initiative', 'project', 'activity']:
            group.permissions.add(*Permission.objects.filter(content_type__app_label='programmes', content_type__model=model))
        group.permissions.add(*Permission.objects.filter(content_type__app_label='engagement', codename__in=['view_submission', 'change_submission']))
        for model in ['thread', 'comment', 'report', 'moderationlog']:
            actions = ['view'] if model == 'moderationlog' else ['view', 'change']
            group.permissions.add(*Permission.objects.filter(content_type__app_label='community', codename__in=[f'{action}_{model}' for action in actions]))
        collection_root = Collection.get_first_root_node()
        collection = Collection.objects.filter(name=f'{code.upper()} media').first()
        if collection is None:
            collection = collection_root.add_child(name=f'{code.upper()} media')
        for app, model in [('wagtailimages', 'image'), ('wagtaildocs', 'document')]:
            for action in ['add', 'change', 'view']:
                permission = Permission.objects.get(content_type__app_label=app, codename=f'{action}_{model}')
                GroupCollectionPermission.objects.get_or_create(group=group, collection=collection, permission=permission)

    def wwi_projects(self):
        programme = Programme.objects.get(code='wwi')
        initiative = programme.initiatives.get(name='Work While Studying (WWS)')
        project, _ = Project.objects.get_or_create(initiative=initiative, name='CASMET — Campus Sales & Marketing Enterprise Team', defaults={'description': 'Learn. Sell. Earn. Grow. Ethical, flexible and professionally supervised student sales, marketing and business-development assignments. Proposed workflow: recruit, train, match, supervise, verify and record skills.'})
        for name in ['Business Academy and Sales Ready preparation', 'Academic availability and work-study planning', 'Supervised campaign assignments and Skills Passport', 'Interim Vacation Work (IVW) extension']:
            Activity.objects.get_or_create(project=project, name=name, defaults={'description': 'Programme-design component; delivery details require confirmation.'})
