import pytest
from django.test import Client
from wagtail.models import PageViewRestriction
from apps.programmes.models import Programme
from apps.core.models import StandardPage
from apps.engagement.models import Submission
from apps.engagement.intake import PROGRAMME_INTAKE, INTAKES

pytestmark = pytest.mark.django_db

@pytest.mark.parametrize('code,kind', list(PROGRAMME_INTAKE.items()))
def test_programme_intake_saves_scoped_details(seeded, code, kind):
    client = Client()
    host = {'HTTP_HOST': f'{code}.localhost:8000'}
    path = f'/participate/{kind}/'
    response = client.get(path, **host)
    assert response.status_code == 200
    data = {'name': 'Test Person', 'email': 'test@example.org', 'consent': 'on', 'form_token': response.context['form_token']}
    for field, label in INTAKES[kind]['fields']:
        data[field] = 'https://example.org' if field.endswith('_url') else 'Testing this field'
    response = client.post(path, data, **host)
    assert response.status_code == 302
    saved = Submission.objects.get()
    assert saved.kind == kind
    assert saved.site.hostname == f'{code}.localhost'
    assert set(saved.details) == {field for field, label in INTAKES[kind]['fields']}
    client.post(path, data, **host)
    assert Submission.objects.count() == 1

def test_intake_scope_validation_and_rate_limit(seeded, client):
    host = {'HTTP_HOST': 'gccs.localhost:8000'}
    assert client.get('/participate/training/', **host).status_code == 404
    response = client.get('/participate/learning/', **host)
    response = client.post('/participate/learning/', {'form_token': response.context['form_token']}, **host)
    assert 'learning_interest' in response.context['form'].errors
    assert not Submission.objects.exists()

def test_global_search_scopes_and_private_pages(seeded, client):
    pec = Programme.objects.get(code='pec')
    page = pec.site.root_page.add_child(instance=StandardPage(title='Zebrasearch shared', slug='zebra', body='<p>Shared</p>'))
    page.save_revision().publish()
    private = pec.site.root_page.add_child(instance=StandardPage(title='Zebrasearch private', slug='zebra-private'))
    private.save_revision().publish()
    PageViewRestriction.objects.create(page=private, restriction_type='login')
    host = {'HTTP_HOST': 'gccs.localhost:8000'}
    assert client.get('/search/?q=Zebrasearch', **host).context['results'].paginator.count == 0
    response = client.get('/search/?q=Zebrasearch&scope=all', **host)
    assert response.context['results'].paginator.count == 1
    assert response.context['results'][0].pk == page.pk
    assert client.get('/search/?q=Zebrasearch&scope=all&programme=gccs', **host).context['results'].paginator.count == 0
    assert client.get('/search/?q=Zebrasearch&scope=all&programme=invalid', **host).context['results'].paginator.count == 0
    partial = client.get('/search/?q=Zebrasearch&scope=all', HTTP_HX_REQUEST='true', **host)
    assert b'<html' not in partial.content
    restored = client.get('/search/?q=Zebrasearch&scope=all', HTTP_HX_REQUEST='true', HTTP_HX_HISTORY_RESTORE_REQUEST='true', **host)
    assert b'<html' in restored.content

def test_new_public_routes(seeded, client):
    for path in ['/programmes/', '/library/?scope=all', '/approach/', '/partner/', '/volunteer/', '/terms/', '/accessibility/', '/participate/partnership/', '/participate/volunteer/']:
        assert client.get(path, HTTP_HOST='localhost:8000').status_code == 200, path
