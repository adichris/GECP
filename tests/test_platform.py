from datetime import timedelta
import pytest
from django.contrib.admin.sites import AdminSite
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.test import Client, RequestFactory
from django.utils import timezone
from wagtail.models import Site, Page
from apps.core.models import SiteBranding, NavigationLink
from apps.programmes.models import Programme, ProgrammeMembership, Initiative, Project, Activity
from apps.programmes.admin import InitiativeAdmin, ProjectAdmin
from apps.engagement.models import Submission
from apps.engagement.admin import SubmissionAdmin
from apps.opportunities.models import OpportunityPage
from apps.events.models import EventPage

pytestmark = pytest.mark.django_db
HOST = {'HTTP_HOST': 'gccs.localhost:8000'}

def test_seed_is_idempotent_and_hierarchy_connected(seeded):
    counts = (Page.objects.count(), Site.objects.count(), Programme.objects.count(), Activity.objects.count())
    call_command('seed_gecp', skip_assets=True)
    assert counts == (Page.objects.count(), Site.objects.count(), Programme.objects.count(), Activity.objects.count())
    assert Programme.objects.count() == 11
    assert Activity.objects.first().project.initiative.programme.foundation.name == 'GECP Foundation'

def test_all_sites_render_distinct_branding(seeded, client):
    for programme in Programme.objects.select_related('site'):
        response = client.get('/', HTTP_HOST=f'{programme.site.hostname}:8000')
        assert response.status_code == 200
        assert response.context['current_programme'] == programme
        assert response.context['branding'].site == programme.site
    response = client.get('/', HTTP_HOST='localhost:8000')
    assert response.status_code == 200
    assert response.context['current_programme'] is None

def test_unknown_host_or_port_never_falls_back(seeded, client):
    assert client.get('/', HTTP_HOST='missing.localhost:8000').status_code == 404
    assert client.get('/', HTTP_HOST='gccs.localhost:9999').status_code == 404

def test_search_and_lists_do_not_leak_other_sites_or_drafts(seeded, client):
    gccs = Programme.objects.get(code='gccs')
    draft = gccs.site.root_page.add_child(instance=OpportunityPage(title='Hidden opportunity', slug='hidden', summary='hidden', live=False))
    response = client.get('/search/?q=PEC', **HOST)
    assert response.context['results'].paginator.count == 0
    response = client.get('/search/?q=discover', **HOST)
    assert response.context['results'].paginator.count >= 1
    assert all(item.is_descendant_of(gccs.site.root_page) for item in response.context['results'])
    response = client.get('/explore/?kind=opportunities', **HOST)
    assert all(item.is_descendant_of(gccs.site.root_page) for item in response.context['items'])
    assert draft not in response.context['items']
    partial = client.get('/explore/?kind=news', HTTP_HX_REQUEST='true', **HOST)
    assert b'<html' not in partial.content
    assert b'id="listing"' in partial.content

def test_public_routes_and_detail_pages(seeded, client):
    for path in ['/about/', '/privacy/', '/discovery-session/', '/search/', '/contact/', '/sitemap.xml', '/robots.txt', '/healthz/']:
        assert client.get(path, **HOST).status_code == 200, path

def test_application_scope_deadline_and_consent(seeded, client):
    own = OpportunityPage.objects.descendant_of(Programme.objects.get(code='gccs').site.root_page).first()
    other = OpportunityPage.objects.descendant_of(Programme.objects.get(code='pec').site.root_page).first()
    assert client.get(f'/apply/{other.pk}/', **HOST).status_code == 404
    own.deadline = timezone.localdate() - timedelta(days=1)
    own.save()
    assert client.get(f'/apply/{own.pk}/', **HOST).status_code == 410
    response = client.get('/contact/', **HOST)
    token = response.context['form_token']
    response = client.post('/contact/', {'name': 'Test', 'email': 'test@example.org', 'message': 'Hello', 'form_token': token}, **HOST)
    assert 'consent' in response.context['form'].errors
    assert not Submission.objects.exists()

def test_submission_htmx_success_and_replay_protection(seeded, client):
    response = client.get('/contact/', **HOST)
    data = {'name': 'Test', 'email': 'test@example.org', 'message': 'Hello', 'consent': 'on', 'form_token': response.context['form_token']}
    response = client.post('/contact/', data, HTTP_HX_REQUEST='true', **HOST)
    assert b'has been received' in response.content
    assert Submission.objects.get().site.hostname == 'gccs.localhost'
    client.post('/contact/', data, **HOST)
    assert Submission.objects.count() == 1

def test_csrf_required_and_standard_post_redirect(seeded):
    client = Client(enforce_csrf_checks=True)
    response = client.get('/contact/', **HOST)
    data = {'name': 'Test', 'email': 'test@example.org', 'message': 'Hello', 'consent': 'on', 'form_token': response.context['form_token']}
    assert client.post('/contact/', data, **HOST).status_code == 403
    data['csrfmiddlewaretoken'] = client.cookies['csrftoken'].value
    response = client.post('/contact/', data, **HOST)
    assert response.status_code == 302
    assert client.get(response.url, **HOST).status_code == 200

def test_programme_admin_scopes_and_foreign_key_choices(seeded):
    user = get_user_model().objects.create_user('editor', is_staff=True)
    programme = Programme.objects.get(code='gccs')
    user.groups.add(Group.objects.get(name='GCCS editors'))
    ProgrammeMembership.objects.create(user=user, programme=programme)
    request = RequestFactory().get('/operations/')
    request.user = user
    admin = InitiativeAdmin(Initiative, AdminSite())
    assert admin.get_queryset(request).exists()
    assert all(item.programme_id == programme.pk for item in admin.get_queryset(request))
    foreign = Initiative.objects.exclude(programme=programme).first()
    assert not admin.has_change_permission(request, foreign)
    field = admin.formfield_for_foreignkey(Initiative._meta.get_field('programme'), request)
    assert list(field.queryset) == [programme]
    project_admin = ProjectAdmin(Project, AdminSite())
    form_class = project_admin.get_form(request)
    form = form_class({'name': 'Invalid move', 'initiative': foreign.pk, 'description': ''})
    assert not form.is_valid()
    assert 'initiative' in form.errors
    submission_admin = SubmissionAdmin(Submission, AdminSite())
    assert not submission_admin.has_add_permission(request)

def test_wagtail_editor_permissions_are_site_scoped(seeded):
    user = get_user_model().objects.create_user('wagtail-editor', is_staff=True)
    user.groups.add(Group.objects.get(name='GCCS editors'))
    own = Programme.objects.get(code='gccs').site.root_page
    other = Programme.objects.get(code='pec').site.root_page
    assert own.permissions_for_user(user).can_edit()
    assert not other.permissions_for_user(user).can_edit()

def test_model_validation(seeded):
    brand = SiteBranding.objects.first()
    brand.primary_color = 'red; display:none'
    with pytest.raises(ValidationError):
        brand.full_clean()
    event = EventPage.objects.first()
    event.ends_at = event.starts_at
    with pytest.raises(ValidationError):
        event.clean()
    link = NavigationLink(branding=brand, label='Broken')
    with pytest.raises(ValidationError):
        link.clean()
