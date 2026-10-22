import json
from pathlib import Path
from django.conf import settings
from django.core.files import File
from django.core.management.base import BaseCommand
from wagtail.images import get_image_model
from apps.core.models import SiteBranding, StandardPage
from apps.programmes.models import Foundation, Programme
from apps.programmes.catalogue import CATALOGUE
from apps.resources.models import LibraryAsset, ResourcePage
from apps.news.models import NewsPage
from apps.events.models import EventPage
from apps.opportunities.models import OpportunityPage
from apps.partners.models import Partner
from .seed_gecp import publish


class Command(BaseCommand):
    help = 'Add source-based editorial starter content and attributed media without replacing edited pages.'

    def add_arguments(self, parser):
        parser.add_argument('--skip-assets', action='store_true')

    def handle(self, *args, **options):
        foundation = Foundation.objects.first()
        if not foundation:
            return
        pillars = {'gccs': 'learning', 'pec': 'pathways', 'wwi': 'work', 'rengtech': 'enterprise', 'spin': 'expertise', 'gsevs': 'expertise', 'tradestart': 'enterprise', 'eraid': 'learning', 'evm': 'knowledge', 'dricd': 'knowledge', 'tkrd': 'knowledge'}
        sites = [(foundation.site, None)] + [(p.site, p) for p in Programme.objects.filter(foundation=foundation)]
        for site, programme in sites:
            home = site.root_page.specific
            brand = SiteBranding.for_site(site)
            for field, value in {'email': 'info@gecpfoundation.org', 'phone': '+233244736051', 'address': 'P.O. Box AN 29512, Accra, Ghana', 'footer_description': home.introduction}.items():
                if not getattr(brand, field):
                    setattr(brand, field, value)
            brand.save()
            privacy = StandardPage.objects.child_of(home).filter(slug='privacy').first()
            if privacy and 'Demonstration privacy notice:' in str(privacy.body):
                privacy.body = '<h2>Information you provide</h2><p>Enquiry forms store the name, email, message, consent and programme details you submit so the responsible team can review and respond. Community accounts store a username, email and a securely hashed password. Password recovery uses your email address.</p><h2>Public and private contributions</h2><p>Your community username and approved topics and comments are public. Pending contributions, content reports and moderation records are reviewed by authorised administrators. Your email address is not displayed with public comments. Do not post sensitive documents or another person’s private information.</p><h2>Cookies and preferences</h2><p>The site uses session and security cookies to support sign-in and forms. Your appearance preference is saved in your browser for each programme site. Hashed request identifiers and short-lived counters help limit abusive submissions. The application does not include advertising trackers.</p><h2>Managing your information</h2><p>Signed-in users can download their community contributions for the current site and withdraw their own posts from public view. Withdrawal retains an administrative record. Contact GECP about account corrections, deletion requests or the retention of enquiries and moderation records. Backup copies may remain until they are replaced under the operator’s backup process.</p><h2>Contact</h2><p>Use the contact page for privacy questions. GECP Foundation’s contact details are shown in the footer. This notice describes the platform’s functions; the site operator must confirm its retention periods and service-provider arrangements before public operation.</p>'
                privacy.save_revision().publish()

            # Retire only recognisable starter material; preserve editorial replacements.
            for model, slug in [(EventPage, 'community-open-day'), (NewsPage, 'welcome'), (ResourcePage, 'getting-started')]:
                sample = model.objects.child_of(home).filter(slug=slug).first()
                if sample and sample.live and ('demonstration' in sample.summary.lower() or 'sample' in sample.summary.lower()):
                    sample.unpublish()
            opportunity = OpportunityPage.objects.child_of(home).filter(slug='discovery-session').first()
            if opportunity and opportunity.summary.startswith('Demonstration opportunity'):
                opportunity.title = f'{brand.display_name}: discover your next pathway'
                opportunity.summary = 'Express an interest in learning, practical skills or shared expertise. The programme team can discuss relevant next steps.'
                opportunity.body = '<p>Tell us about your interests and the support you would like to explore. This is an open enquiry, not a confirmed course, funded place or employment offer.</p><p>Participation requirements and delivery arrangements are confirmed separately by the programme team.</p>'
                opportunity.category = 'interest'
                opportunity.deadline = None
                opportunity.save_revision().publish()
            for partner in Partner.objects.filter(name='Demonstration community partner'):
                partner.sites.remove(site)
            pages = {
                'approach': ('Learning connected to action', '<p>Start with a question, a skill or a community need. GECP connects education, career guidance, work experience, technical skills and shared expertise through a family of complementary programmes.</p><h2>Discover your pathway</h2><p>Explore the programme directory, read the initiative descriptions and tell the relevant team what you hope to achieve. Learning interests, experience and availability help shape the next conversation.</p><h2>Build through collaboration</h2><p>Our programme designs bring together learners, practitioners, volunteers and institutions. Individual opportunities, delivery arrangements and participation requirements are confirmed by the responsible team.</p>'),
                'partner': ('Build possibilities together', '<p>Institutions, employers, educators and community organisations can contribute knowledge, learning spaces, practical assignments, resources or mentoring.</p><h2>Start a partnership conversation</h2><p>Describe your organisation, the community you serve and the kind of collaboration you have in mind.</p><p><a href="/participate/partnership/">Send a partnership enquiry</a></p>'),
                'volunteer': ('Put your experience to work', '<p>Share professional knowledge through mentoring, guest teaching, technical advice, community assignments or knowledge documentation. GSEVS brings lifelong experience into conversations with the next generation.</p><p>Tell us about your expertise, availability and preferred way to contribute. Assignments and safeguarding arrangements are agreed before participation.</p><p><a href="/participate/volunteer/">Register your volunteering interest</a></p>'),
                'accessibility': ('Access and inclusion', '<p>This website supports keyboard navigation, responsive layouts, colour-theme choices and reduced-motion preferences. Forms display validation messages and essential journeys work without animation.</p><p>If you encounter a barrier, please contact the team with the page address and a description of the problem. We welcome requests for alternative formats.</p><p><a href="/contact/">Report an accessibility issue</a></p>'),
                'terms': ('Using this website', '<p>Programme pages describe areas of focus and developing initiatives. An enquiry does not guarantee a scholarship, placement, grant, job or admission. Confirm eligibility and current delivery arrangements with the relevant programme team.</p><p>Original logos and programme graphics belong to their respective owners. Archive materials may contain earlier names or planning details. Illustrations are labelled and do not document actual programme participants.</p>'),
            }
            for slug, (title, body) in pages.items():
                publish(home, StandardPage, slug, title=title, body=body)
            if programme:
                Programme.objects.filter(pk=programme.pk, pillar='learning').update(pillar=pillars[programme.code])
                entry = CATALOGUE[programme.code]
                body = f'<p>{entry["description"]}</p><h2>Explore the programme</h2>' + ''.join(f'<h3>{name}</h3><p>{description}</p>' for name, description in entry['initiatives']) + '<p>These focus areas are drawn from GECP programme planning. Contact the team to confirm current participation and delivery arrangements.</p>'
                publish(home, NewsPage, 'programme-pathways', title=f'Explore the pathways within {programme.code.upper()}', summary=entry['description'], body=body)
                publish(home, ResourcePage, 'plan-your-next-step', title=f'Plan your next step with {programme.code.upper()}', summary='A practical guide to preparing a useful first conversation with the programme team.', body='<h2>1. Define your goal</h2><p>Write down the skill, opportunity or challenge you want to explore and what a useful outcome would look like.</p><h2>2. Describe your starting point</h2><p>Note your learning or work experience, strengths and questions. You do not need to upload identity documents to make an enquiry.</p><h2>3. Consider your availability</h2><p>Think about the time, location and support you need. The team can discuss delivery options and requirements.</p><h2>4. Start a conversation</h2><p>Use the programme enquiry form. Keep a copy of your submission reference for follow-up.</p>')
            else:
                publish(home, NewsPage, 'connected-pathways', title='A connected network for learning, work and shared expertise', summary='Discover how GECP’s programme family connects education, practical skills, career pathways and community knowledge.', body='<p>Global Education and Career Pathways Foundation brings complementary areas of work into one connected network.</p><h2>Learn and navigate</h2><p>GCCS supports lifelong learning. Pathfinder Education Clinic focuses on educational and career choices. ERAid connects learning with educational resources.</p><h2>Build and contribute</h2><p>WWI connects learning with work. RENGTECH explores technical skills and productive reuse, while TRADESTART supports pathways from apprenticeship into enterprise.</p><h2>Share and preserve</h2><p>SPIN connects talent and collaboration. GSEVS mobilises experienced professionals. EVM, DRICD and TKRD help communicate, organise and preserve knowledge.</p>')
        if not options['skip_assets']:
            self.import_library(foundation)
        self.stdout.write(self.style.SUCCESS('Editorial pages, contact information and media library are ready.'))

    def import_library(self, foundation):
        folder = Path(settings.BASE_DIR) / 'seed_assets'
        entries = json.loads((folder / 'manifest.json').read_text(encoding='utf-8'))
        entries.append({'file': 'learning-together-illustration.png', 'programme': 'foundation', 'role': 'illustration', 'source_title': 'AI-generated conceptual learning illustration'})
        for entry in entries:
            path = folder / entry['file']
            if not path.exists():
                continue
            slug = path.stem
            asset = LibraryAsset.objects.filter(slug=slug).first()
            if asset is None:
                image = get_image_model().objects.filter(title=f'GECP library: {slug}').first()
                if image is None:
                    with path.open('rb') as source:
                        image = get_image_model()(title=f'GECP library: {slug}', file=File(source, name=path.name))
                        image.save()
                archive = entry['role'] == 'reference'
                title = slug.replace('-', ' ').capitalize()
                asset = LibraryAsset.objects.create(slug=slug, title=title, image=image, alt_text=title, source_note=entry['source_title'], kind='illustration' if entry['role'] == 'illustration' else ('identity' if 'logo' in slug else 'brochure'), is_archive=archive, is_public=True, caption='Conceptual illustration; not a photograph of programme participants.' if entry['role'] == 'illustration' else ('Planning archive: names, contact details and delivery proposals may have changed.' if archive else 'Original identity supplied in GECP programme materials.'))
            site = foundation.site if entry['programme'] == 'foundation' else Programme.objects.get(code=entry['programme']).site
            asset.sites.add(site)
            if entry['role'] == 'illustration':
                home = foundation.site.root_page.specific
                brand = SiteBranding.for_site(foundation.site)
                if not home.hero_image_id or home.hero_image_id == brand.logo_id:
                    home.hero_image = asset.image
                    home.hero_caption = 'Conceptual illustration · learning together'
                    home.save_revision().publish()
                NewsPage.objects.filter(slug='connected-pathways', image__isnull=True).update(image=asset.image)
