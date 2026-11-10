import io
import pytest
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image
from apps.programmes.models import Programme, Project
from apps.staff.models import PortfolioItem, StaffProfile

pytestmark = pytest.mark.django_db
FOUNDATION = {'HTTP_HOST': 'localhost:8000'}
GCCS = {'HTTP_HOST': 'gccs.localhost:8000'}
PEC = {'HTTP_HOST': 'pec.localhost:8000'}


@pytest.fixture(autouse=True)
def media_root(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path


def staff_user(username='ama', is_staff=True):
    return get_user_model().objects.create_user(username, f'{username}@example.org', 'pw-123456', is_staff=is_staff)


def make_profile(user, **extra):
    return StaffProfile.objects.create(user=user, slug=user.username, display_name=user.username.title(),
                                       job_title='Programme officer', **extra)


def gccs_project():
    initiative = Programme.objects.get(code='gccs').initiatives.first()
    return Project.objects.get_or_create(initiative=initiative, name='Community literacy circles')[0]


def jpeg_with_gps():
    image = Image.new('RGB', (2400, 1200), 'green')
    exif = Image.Exif()
    exif[0x010F] = 'TrackingCam'  # camera make; stands in for any identifying metadata
    buffer = io.BytesIO()
    image.save(buffer, 'JPEG', exif=exif)
    return SimpleUploadedFile('me.jpg', buffer.getvalue(), content_type='image/jpeg')


def test_dashboard_requires_signed_in_staff(seeded, client):
    response = client.get('/team/me/', **FOUNDATION)
    assert response.status_code == 302 and '/accounts/login/' in response.url
    client.force_login(staff_user('visitor', is_staff=False))
    response = client.get('/team/me/', **FOUNDATION)
    assert response.status_code == 403 and b'administrator to enable staff status' in response.content
    assert client.post('/team/me/profile/', {'display_name': 'X', 'job_title': 'Y'}, **FOUNDATION).status_code == 403
    assert not StaffProfile.objects.exists()


def test_staff_create_profile_with_clean_photo_then_add_work_linked_to_project(seeded, client):
    user = staff_user()
    client.force_login(user)
    gccs = Programme.objects.get(code='gccs')
    response = client.post('/team/me/profile/', {
        'display_name': 'Ama Mensah', 'job_title': 'Learning lead', 'bio': 'Ten years in adult learning.',
        'programmes': [gccs.pk], 'is_public': 'on', 'photo': jpeg_with_gps(),
    }, **FOUNDATION)
    assert response.status_code == 302
    profile = StaffProfile.objects.get(user=user)
    assert profile.slug == 'ama-mensah'
    with Image.open(profile.photo.path) as stored:
        assert max(stored.size) <= 1600
        assert not stored.getexif()
    project = gccs_project()
    response = client.post('/team/me/work/new/', {
        'title': 'Community literacy circles', 'kind': 'project', 'role': 'Lead facilitator',
        'summary': 'Weekly reading circles.', 'projects': [project.pk], 'started_on': '2025-01-10', 'is_public': 'on',
    }, **FOUNDATION)
    assert response.status_code == 302
    work = PortfolioItem.objects.get()
    assert list(work.projects.all()) == [project] and work.profile == profile
    # Linking a project is optional.
    client.post('/team/me/work/new/', {'title': 'Independent talk', 'kind': 'event', 'summary': 'A talk.', 'is_public': 'on'}, **FOUNDATION)
    assert PortfolioItem.objects.get(title='Independent talk').projects.count() == 0


def test_work_needs_a_profile_and_rejects_bad_dates_and_files(seeded, client):
    client.force_login(staff_user())
    assert client.get('/team/me/work/new/', **FOUNDATION).url == '/team/me/profile/'
    make_profile(get_user_model().objects.get(username='ama'))
    response = client.post('/team/me/work/new/', {
        'title': 'T', 'kind': 'project', 'summary': 'S', 'started_on': '2025-05-01', 'ended_on': '2025-01-01',
        'image': SimpleUploadedFile('x.jpg', b'not an image', content_type='image/jpeg'),
    }, **FOUNDATION)
    assert response.status_code == 200
    assert 'ended_on' in response.context['form'].errors and 'image' in response.context['form'].errors
    assert not PortfolioItem.objects.exists()


def test_staff_cannot_edit_or_delete_someone_elses_work(seeded, client):
    owner = make_profile(staff_user('owner'))
    work = PortfolioItem.objects.create(profile=owner, title='Mine', summary='s')
    intruder = staff_user('intruder')
    make_profile(intruder)
    client.force_login(intruder)
    assert client.get(f'/team/me/work/{work.pk}/edit/', **FOUNDATION).status_code == 404
    assert client.post(f'/team/me/work/{work.pk}/delete/', **FOUNDATION).status_code == 404
    assert PortfolioItem.objects.filter(pk=work.pk).exists()
    client.force_login(owner.user)
    assert client.post(f'/team/me/work/{work.pk}/delete/', **FOUNDATION).status_code == 302
    assert not PortfolioItem.objects.exists()


def test_public_directory_profile_and_item_visibility(seeded, client):
    visible = make_profile(staff_user('visible'))
    shown = PortfolioItem.objects.create(profile=visible, title='Shown work', summary='s')
    private_item = PortfolioItem.objects.create(profile=visible, title='Private work', summary='s', is_public=False)
    hidden_item = PortfolioItem.objects.create(profile=visible, title='Hidden work', summary='s', hidden_by_admin=True)
    make_profile(staff_user('private'), is_public=False)
    make_profile(staff_user('hidden'), hidden_by_admin=True)
    former = make_profile(staff_user('former'))
    former.user.is_staff = False
    former.user.save()
    names = [p.slug for p in client.get('/team/', **FOUNDATION).context['profiles']]
    assert names == ['visible']
    for slug in ['private', 'hidden', 'former']:
        assert client.get(f'/team/{slug}/', **FOUNDATION).status_code == 404
    page = client.get('/team/visible/', **FOUNDATION).content.decode()
    assert 'Shown work' in page and 'Private work' not in page and 'Hidden work' not in page
    assert client.get(f'/team/visible/work/{shown.pk}/', **FOUNDATION).status_code == 200
    for item in (private_item, hidden_item):
        assert client.get(f'/team/visible/work/{item.pk}/', **FOUNDATION).status_code == 404


def test_programme_sites_show_only_their_staff(seeded, client):
    gccs = Programme.objects.get(code='gccs')
    member = make_profile(staff_user('member'))
    member.programmes.add(gccs)
    contributor = make_profile(staff_user('contributor'))
    PortfolioItem.objects.create(profile=contributor, title='GCCS work', summary='s').projects.add(gccs_project())
    make_profile(staff_user('elsewhere'))
    assert {p.slug for p in client.get('/team/', **GCCS).context['profiles']} == {'member', 'contributor'}
    assert client.get('/team/elsewhere/', **GCCS).status_code == 404
    assert client.get('/team/member/', **PEC).status_code == 404
    filtered = client.get('/team/?programme=gccs', **FOUNDATION).context['profiles']
    assert {p.slug for p in filtered} == {'member', 'contributor'}
    assert [p.slug for p in client.get('/team/?q=elsew', **FOUNDATION).context['profiles']] == ['elsewhere']


def test_user_text_is_escaped(seeded, client):
    profile = make_profile(staff_user('xss'), bio='<script>alert(1)</script>')
    PortfolioItem.objects.create(profile=profile, title='<img src=x onerror=alert(1)>', summary='s')
    page = client.get('/team/xss/', **FOUNDATION).content.decode()
    assert '<script>alert(1)</script>' not in page and '<img src=x' not in page


def test_linkedin_url_must_be_linkedin(seeded, client):
    client.force_login(staff_user())
    response = client.post('/team/me/profile/', {'display_name': 'A', 'job_title': 'B',
                                                 'linkedin_url': 'https://linkedin.com.evil.example/in/a'}, **FOUNDATION)
    assert 'linkedin_url' in response.context['form'].errors
    response = client.post('/team/me/profile/', {'display_name': 'A', 'job_title': 'B',
                                                 'linkedin_url': 'https://www.linkedin.com/in/a'}, **FOUNDATION)
    assert response.status_code == 302


def test_deleting_work_removes_its_image(seeded, client, django_capture_on_commit_callbacks):
    client.force_login(staff_user())
    make_profile(get_user_model().objects.get(username='ama'))
    with django_capture_on_commit_callbacks(execute=True):
        client.post('/team/me/work/new/', {'title': 'Pic', 'kind': 'other', 'summary': 's', 'image': jpeg_with_gps()}, **FOUNDATION)
    work = PortfolioItem.objects.get()
    path = work.image.path
    with django_capture_on_commit_callbacks(execute=True):
        client.post(f'/team/me/work/{work.pk}/delete/', **FOUNDATION)
    import os
    assert not os.path.exists(path)


def test_navigation_links_to_team(seeded, client):
    assert b'href="/team/"' in client.get('/', **FOUNDATION).content
