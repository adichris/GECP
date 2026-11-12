import pytest
from django.contrib.auth import get_user_model
from django.core.management import CommandError, call_command
from apps.staff.models import PortfolioItem, StaffProfile

pytestmark = pytest.mark.django_db
FOUNDATION = {'HTTP_HOST': 'localhost:8000'}


def owner():
    return get_user_model().objects.create_superuser('owner', 'owner@example.org', 'pw-123456')


def test_seed_staff_creates_owner_and_demo_profiles_idempotently(client):
    user = owner()
    call_command('seed_staff', owner='owner', demo=True)
    call_command('seed_staff', owner='owner', demo=True)
    assert StaffProfile.objects.count() == 7
    profile = StaffProfile.objects.get(user=user)
    assert profile.job_title == 'Director of Technology & Digital Innovation'
    assert profile.items.count() == 3 and profile.programmes.count() == 4
    assert PortfolioItem.objects.filter(projects__isnull=False).exists()
    user.refresh_from_db()
    assert user.check_password('pw-123456') and user.is_superuser  # owner account untouched
    demo = get_user_model().objects.filter(username__startswith='demo.')
    assert demo.count() == 5 and not any(u.has_usable_password() for u in demo)
    page = client.get('/team/', **FOUNDATION)
    assert page.status_code == 200 and b'Addai Christopher' in page.content and b'Akosua Mensah' in page.content


def test_seed_staff_team_member_without_demo(client):
    call_command('seed_staff')
    call_command('seed_staff')
    profile = StaffProfile.objects.get()
    assert profile.display_name == 'Ebenezer Brikum Gmantermi'
    assert profile.photo and profile.programmes.get().code == 'pec'
    user = profile.user
    assert user.is_staff and not user.has_usable_password() and not user.is_superuser
    framework = profile.items.get(kind='project')
    assert framework.projects.get().name.startswith('SPlaSA')
    assert profile.items.get(kind='event').image
    page = client.get(profile.get_absolute_url(), **FOUNDATION)
    assert page.status_code == 200 and b'SPlaSA termly outreach framework' in page.content
    first_photo = profile.photo.name
    call_command('seed_staff')
    profile.refresh_from_db()
    assert profile.photo.name == first_photo  # existing photos are never replaced


def test_seed_staff_remove_demo_and_unknown_owner():
    call_command('seed_staff', demo=True)
    call_command('seed_staff', remove_demo=True)
    assert StaffProfile.objects.count() == 1  # real team members stay
    with pytest.raises(CommandError):
        call_command('seed_staff', owner='nobody')


def owner_profile():
    return StaffProfile.objects.filter(display_name='Addai Christopher').select_related('user').first()


def test_owner_found_without_flag_when_only_one_superuser():
    get_user_model().objects.create_superuser('kofi-admin', 'k@example.org', 'pw-123456')
    call_command('seed_staff')
    assert owner_profile().user.username == 'kofi-admin'


def test_owner_default_username_wins_over_other_superusers():
    User = get_user_model()
    User.objects.create_superuser('someone', 's@example.org', 'pw-123456')
    User.objects.create_superuser('addai', 'a@example.org', 'pw-123456')
    call_command('seed_staff')
    assert owner_profile().user.username == 'addai'


def test_owner_found_by_name():
    User = get_user_model()
    User.objects.create_superuser('one', '1@example.org', 'pw-123456')
    User.objects.create_superuser('chris', 'c@example.org', 'pw-123456', first_name='Addai', last_name='Christopher')
    call_command('seed_staff')
    assert owner_profile().user.username == 'chris'


def test_owner_skipped_with_warning_when_ambiguous(capsys):
    User = get_user_model()
    User.objects.create_superuser('one', '1@example.org', 'pw-123456')
    User.objects.create_superuser('two', '2@example.org', 'pw-123456')
    call_command('seed_staff')
    assert owner_profile() is None
    assert '--owner' in capsys.readouterr().err
