"""Seed the team directory.

    python manage.py seed_staff                      # your profile + GECP team members
    python manage.py seed_staff --owner USERNAME     # attach your profile to a specific account
    python manage.py seed_staff --demo               # also add fictional sample colleagues
    python manage.py seed_staff --remove-demo        # delete the sample colleagues again

Safe to re-run: records are updated in place, never duplicated. Team members and demo staff get
accounts with unusable passwords; an administrator can set a password (or the person can use
password reset with the email on file) when they are ready to manage their own portfolio.
The owner's password and permissions are never changed. Seeded photos are only applied when the
profile has none, so photos uploaded at /team/me/ are never overwritten.
"""
from datetime import date
from pathlib import Path

from django.core.files import File

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.programmes.models import Initiative, Programme, Project
from apps.staff.images import clean_image
from apps.staff.models import PortfolioItem, StaffProfile

PHOTOS = Path(__file__).resolve().parents[2] / 'seed_photos'

PILOT = 'Demonstration delivery pilot'
CASMET = 'CASMET — Campus Sales & Marketing Enterprise Team'
SPSOW = 'SPSOW — School Placements & Scholarships Opportunities Watch'
SPLASA = 'SPlaSA — School Placement & Scholarship Assistance (UENR, Sunyani)'
# Real projects created on demand: (programme code, initiative name, project name, description).
PROJECTS = [
    ('pec', SPSOW, SPLASA,
     'Campus chapter at the University of Energy and Natural Resources helping students find school '
     'placements, scholarships and career guidance through GECP Foundation.'),
]

OWNER = {
    'username': 'addai',
    'first_name': 'Addai', 'last_name': 'Christopher',
    'display_name': 'Addai Christopher',
    'job_title': 'Director of Technology & Digital Innovation',
    'programmes': ['spin', 'dricd', 'evm', 'eraid'],
    'bio': (
        'Addai leads technology and digital innovation across the GECP Foundation and its eleven programmes. '
        'He designed and built the shared multisite platform that gives every programme its own branded website, '
        'editorial workflow, search and secure intake forms, while keeping one organisational record behind them.\n\n'
        'His work focuses on practical digital infrastructure for education and employability: tools that let '
        'programme teams publish, collect applications and document their impact without depending on outside '
        'vendors. He also mentors staff and volunteers on digital skills, data protection and content publishing.'
    ),
    'items': [
        {'title': 'GECP multisite digital platform', 'kind': 'project', 'role': 'Architect and lead developer',
         'summary': 'One secure platform powering the foundation website and eleven branded programme subdomains.',
         'description': (
             'Designed and delivered the Django/Wagtail platform behind gecpfoundation and every programme site: '
             'per-site branding, scoped editor permissions, search, events calendar, opportunities, resource '
             'library, contact and application intake with moderation, and automated, rollback-ready deployments.'
         ),
         'programme_projects': [('spin', PILOT), ('dricd', PILOT)], 'started_on': date(2025, 9, 1)},
        {'title': 'Staff portfolios and team directory', 'kind': 'project', 'role': 'Product lead',
         'summary': 'A public team directory where staff showcase their work and link it to GECP projects.',
         'programme_projects': [('evm', PILOT)], 'started_on': date(2026, 10, 1), 'ended_on': date(2026, 11, 1)},
        {'title': 'Digital publishing training for programme editors', 'kind': 'training', 'role': 'Lead facilitator',
         'summary': 'Hands-on sessions training programme teams to publish news, events and resources safely.',
         'programme_projects': [('eraid', PILOT)], 'started_on': date(2026, 6, 1), 'ended_on': date(2026, 7, 15)},
    ],
}

DEMO = [
    {'username': 'demo.akosua', 'display_name': 'Akosua Mensah', 'job_title': 'Head of Programmes',
     'programmes': ['gccs', 'pec'],
     'bio': 'Akosua coordinates delivery across the education programmes, working with schools, '
            'parents and volunteers to turn programme plans into measurable learning outcomes.',
     'items': [
         {'title': 'Community learning circles pilot', 'kind': 'project', 'role': 'Programme lead',
          'summary': 'After-school learning circles supporting literacy and numeracy in partner communities.',
          'programme_projects': [('gccs', PILOT)], 'started_on': date(2026, 2, 1)},
         {'title': 'Education clinic guidance sessions', 'kind': 'event', 'role': 'Facilitator',
          'summary': 'Guidance sessions helping students and parents plan subject choices and next steps.',
          'programme_projects': [('pec', PILOT)], 'started_on': date(2026, 8, 10), 'ended_on': date(2026, 8, 14)},
     ]},
    {'username': 'demo.kwame', 'display_name': 'Kwame Boateng', 'job_title': 'Partnerships & Employability Lead',
     'programmes': ['wwi', 'tradestart'],
     'bio': 'Kwame builds partnerships with employers and trade associations, connecting graduates and '
            'apprentices with supervised work experience and enterprise opportunities.',
     'items': [
         {'title': 'CASMET student sales team launch', 'kind': 'project', 'role': 'Partnership manager',
          'summary': 'Recruited and matched the first cohort of students to supervised sales and marketing assignments.',
          'programme_projects': [('wwi', CASMET)], 'started_on': date(2026, 3, 1)},
         {'title': 'Apprenticeship graduate employer forum', 'kind': 'event', 'role': 'Organiser',
          'summary': 'A forum bringing apprenticeship graduates together with local employers and lenders.',
          'programme_projects': [('tradestart', PILOT)], 'started_on': date(2026, 9, 18), 'ended_on': date(2026, 9, 18)},
     ]},
    {'username': 'demo.efua', 'display_name': 'Efua Asante', 'job_title': 'Research & Documentation Officer',
     'programmes': ['dricd', 'tkrd'],
     'bio': 'Efua leads desk research and documents the tacit knowledge of experienced practitioners, '
            'so that programme lessons are preserved and reusable.',
     'items': [
         {'title': 'Craft knowledge interview series', 'kind': 'publication', 'role': 'Lead researcher',
          'summary': 'Recorded and transcribed interviews capturing the working knowledge of senior artisans.',
          'programme_projects': [('tkrd', PILOT)], 'started_on': date(2026, 1, 15), 'ended_on': date(2026, 6, 30)},
     ]},
    {'username': 'demo.yaw', 'display_name': 'Yaw Owusu', 'job_title': 'Engineering & Skills Coordinator',
     'programmes': ['rengtech', 'spin'],
     'bio': 'Yaw runs practical refurbishment and repair workshops, training young people to restore '
            'equipment for schools while building marketable technical skills.',
     'items': [
         {'title': 'Laptop refurbishment workshop', 'kind': 'training', 'role': 'Workshop lead',
          'summary': 'Trainees refurbished donated laptops for partner schools while learning diagnostics and repair.',
          'programme_projects': [('rengtech', PILOT), ('spin', PILOT)], 'started_on': date(2026, 4, 6),
          'ended_on': date(2026, 5, 29)},
     ]},
    {'username': 'demo.abena', 'display_name': 'Abena Darko', 'job_title': 'Media & Communications Officer',
     'programmes': ['evm', 'eraid'],
     'bio': 'Abena tells the stories behind GECP programmes through video, radio and social media, and '
            'coordinates the distribution of donated learning resources.',
     'items': [
         {'title': 'Educational Voices podcast, season one', 'kind': 'publication', 'role': 'Producer and host',
          'summary': 'Eight episodes with teachers, students and volunteers on learning in their communities.',
          'programme_projects': [('evm', PILOT)], 'started_on': date(2026, 5, 1), 'ended_on': date(2026, 10, 31)},
         {'title': 'Book and resource drive', 'kind': 'project', 'role': 'Communications lead',
          'summary': 'Campaign collecting and distributing textbooks and reading materials to partner schools.',
          'programme_projects': [('eraid', PILOT)], 'started_on': date(2026, 7, 1)},
     ]},
]

# Real GECP team members (not demo data).
TEAM = [
    {'username': 'ebenezer.gmantermi', 'email': 'gmanterimiebenezerbrikum@gmail.com',
     'first_name': 'Ebenezer', 'last_name': 'Gmantermi',
     'display_name': 'Ebenezer Brikum Gmantermi',
     'job_title': 'Coordinator, School Placement & Scholarship Assistance (SPlaSA), UENR',
     'programmes': ['pec'], 'photo': 'ebenezer-gmantermi.jpg',
     'bio': (
         'Ebenezer Brikum Gmantermi is a passionate student leader and the appointed coordinator for School '
         'Placement and Scholarship Assistance (SPlaSA) under the Global Education and Career Pathways (GECP) '
         'Foundation at the University of Energy and Natural Resources (UENR), Sunyani. He is a Petroleum and '
         'Natural Gas Engineering student at UENR and a public speaker.\n\n'
         'A beneficiary of the MTN Foundation Scholarship and a team member of GWOSSU, Ebenezer specialises in '
         'writing scholarship applications and has years of experience helping others do the same. He '
         'understands what students need at every level, from career guidance to finding funding for their '
         'education.'
     ),
     'items': [
         {'title': 'SPlaSA termly outreach framework', 'kind': 'project', 'role': 'Coordinator',
          'summary': 'A termly plan to make UENR students aware of the placement, scholarship and career '
                     'support available through GECP Foundation.',
          'description': (
              '- Publicity through flyers and other available platforms, so students know where to find '
              'SPlaSA, what it covers and the opportunities they can access.\n'
              '- Early meetings with student leaders of the SRC, LNUGS, GESA (engineering students) and SCISA '
              '(School of Sciences) to engage freshers and continuing students about SPlaSA under GECP '
              'Foundation, so students know where to turn in times of need.\n'
              '- Outreach to students on and off campus at convenient periods.\n'
              '- Collaboration with student bloggers within the SRC to spread the word about GECP Foundation '
              'and its benefits for students.\n'
              '- Partnerships with other universities, such as Catholic University and STU, to speak to their '
              'students during major events like Engineering Week celebrations and SRC Week.'
          ),
          'programme_projects': [('pec', SPLASA)]},
         {'title': 'NSU Freshers Akwaaba Summit', 'kind': 'event', 'role': 'Speaker',
          'summary': 'Spoke to new students at the NSU Freshers Akwaaba Summit.',
          'image': 'ebenezer-akwaaba-summit.jpg', 'programme_projects': []},
     ]},
]

ITEM_FIELDS = ('kind', 'role', 'summary', 'description', 'started_on', 'ended_on')


class Command(BaseCommand):
    help = 'Seed the staff directory with your profile (--owner) and sample colleagues.'

    def add_arguments(self, parser):
        parser.add_argument('--owner', help='Username for your profile. Default: "addai", an account named '
                            'Addai Christopher, or the only superuser.')
        parser.add_argument('--demo', action='store_true', help='Also add fictional sample colleagues.')
        parser.add_argument('--remove-demo', action='store_true', help='Delete the sample colleagues and exit.')

    @transaction.atomic
    def handle(self, *args, owner=None, demo=False, remove_demo=False, **options):
        User = get_user_model()
        if remove_demo:
            deleted = 0
            for user in User.objects.filter(username__startswith='demo.'):
                user.delete()  # cascades to the profile and portfolio items, removing any uploads
                deleted += 1
            self.stdout.write(self.style.SUCCESS(f'Removed {deleted} demo staff accounts.'))
            return
        if not Programme.objects.exists():
            raise CommandError('No programmes found. Run scripts/seed_all.py first.')

        user, how = self._find_owner(User, owner)
        if user is None:
            self.stderr.write(self.style.WARNING(
                f'Skipped {OWNER["display_name"]}\'s profile: no matching account found ({how}). '
                'Create your account (manage.py createsuperuser), then re-run with --owner <your-username>.'))
        else:
            self.stdout.write(f'Owner account: {user.username} ({how})')
            changed = []
            for field in ('first_name', 'last_name'):
                if not getattr(user, field):
                    setattr(user, field, OWNER[field])
                    changed.append(field)
            if not user.is_staff:
                user.is_staff = True  # required to appear in the team directory
                changed.append('is_staff')
            if changed:
                user.save(update_fields=changed)
            profile = self._profile(user, OWNER)
            self.stdout.write(f'Profile for {user.username}: {profile.display_name}, {profile.job_title}')

        for code, initiative_name, name, description in PROJECTS:
            initiative = Initiative.objects.filter(programme__code=code, name=initiative_name).first()
            if initiative:
                Project.objects.get_or_create(initiative=initiative, name=name, defaults={'description': description})
        for spec in TEAM:
            user, created = User.objects.get_or_create(username=spec['username'], defaults={
                'is_staff': True, 'email': spec['email'],
                'first_name': spec['first_name'], 'last_name': spec['last_name']})
            if created:
                user.set_unusable_password()
                user.save()
            profile = self._profile(user, spec)
            self.stdout.write(f'Team member: {profile.display_name}, {profile.job_title}')

        if demo:
            for spec in DEMO:
                user, created = User.objects.get_or_create(username=spec['username'], defaults={'is_staff': True})
                if created:
                    user.set_unusable_password()
                    user.save()
                self._profile(user, spec)
            self.stdout.write(f'Demo staff: {len(DEMO)} profiles (accounts cannot sign in; remove with --remove-demo)')
        self.stdout.write(self.style.SUCCESS('Team directory seeded: /team/'))

    def _profile(self, user, spec):
        profile = getattr(user, 'staff_profile', None) or StaffProfile(
            user=user, slug=StaffProfile.unique_slug(spec['display_name']))
        profile.display_name = spec['display_name']
        profile.job_title = spec['job_title']
        profile.bio = spec['bio']
        if spec.get('photo') and not profile.photo:
            profile.photo = self._image(spec['photo'], 'staff')
        profile.save()
        profile.programmes.set(Programme.objects.filter(code__in=spec['programmes']))
        for item_spec in spec['items']:
            item = PortfolioItem.objects.filter(profile=profile, title=item_spec['title']).first() or PortfolioItem(
                profile=profile, title=item_spec['title'])
            for field in ITEM_FIELDS:
                setattr(item, field, item_spec.get(field, '' if field in ('role', 'description') else None))
            if item_spec.get('image') and not item.image:
                item.image = self._image(item_spec['image'], 'portfolio')
            item.full_clean(exclude=['image'])
            item.save()
            item.projects.set(self._projects(item_spec['programme_projects']))
        return profile

    @staticmethod
    def _find_owner(User, username=None):
        """The account that gets the owner's profile, and how it was chosen.

        --owner wins; otherwise the default username, then an account with the owner's name,
        then the only superuser (the usual case on a fresh server).
        """
        if username:
            user = User.objects.filter(username=username).first()
            if user is None:
                raise CommandError(f'No account named "{username}". Create it first: manage.py createsuperuser')
            return user, '--owner'
        user = User.objects.filter(username=OWNER['username']).first()
        if user:
            return user, f'default username "{OWNER["username"]}"'
        named = User.objects.filter(first_name__iexact=OWNER['first_name'], last_name__iexact=OWNER['last_name'])
        if named.count() == 1:
            return named.get(), f'name {OWNER["first_name"]} {OWNER["last_name"]}'
        superusers = User.objects.filter(is_superuser=True, is_active=True)
        if superusers.count() == 1:
            return superusers.get(), 'the only superuser'
        return None, f'{superusers.count()} superusers, none named "{OWNER["username"]}"'

    @staticmethod
    def _image(filename, prefix):
        with (PHOTOS / filename).open('rb') as handle:
            return clean_image(File(handle), prefix)  # same metadata stripping as user uploads

    @staticmethod
    def _projects(pairs):
        projects = []
        for code, name in pairs:
            project = Project.objects.filter(initiative__programme__code=code, name=name).first()
            if project:
                projects.append(project)
        return projects
