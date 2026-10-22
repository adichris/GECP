import pytest
from django.core.management import call_command
from apps.programmes.models import Programme
from apps.news.models import NewsPage
from apps.programmes.editorial import PROFILES

pytestmark = pytest.mark.django_db

def test_each_programme_has_specific_sections_and_blog(seeded, client):
    for programme in Programme.objects.select_related('site__root_page'):
        home = programme.site.root_page.specific
        assert len(home.programme_sections) == 3
        host = {'HTTP_HOST': f'{programme.site.hostname}:8000'}
        posts = NewsPage.objects.live().descendant_of(home).filter(content_kind='blog')
        assert posts.count() == 2
        response = client.get('/', **host)
        assert response.status_code == 200
        assert PROFILES[programme.code]['audience'][0][0].encode() in response.content
        response = client.get('/blog/', **host)
        assert response.status_code == 200
        assert response.context['items'].paginator.count == 2
        for post in posts:
            assert client.get(post.url, **host).status_code == 200

def test_blog_scope_filter_and_drafts(seeded, client):
    home = Programme.objects.get(code='wwi').site.root_page
    post = NewsPage.objects.descendant_of(home).filter(content_kind='blog').first()
    host = {'HTTP_HOST': 'wwi.localhost:8000'}
    response = client.get('/blog/', {'topic': post.topic}, HTTP_HX_REQUEST='true', **host)
    assert b'<html' not in response.content
    assert response.context['items'].paginator.count == 1
    assert all(p.is_descendant_of(home) for p in response.context['items'])
    post.unpublish()
    assert client.get('/blog/', **host).context['items'].paginator.count == 1
    assert client.get('/blog/', HTTP_HOST='localhost:8000').context['items'].paginator.count == 24

def test_editorial_seed_preserves_edits(seeded):
    home = Programme.objects.get(code='wwi').site.root_page.specific
    home.programme_sections = [('section', {'heading': 'Edited section', 'items': [], 'layout': 'cards'})]
    home.save_revision().publish()
    post = NewsPage.objects.descendant_of(home).filter(content_kind='blog').first()
    post.body = '<p>Edited article</p>'
    post.save_revision().publish()
    count = NewsPage.objects.count()
    call_command('seed_programme_editorial')
    post.refresh_from_db()
    home.refresh_from_db()
    assert post.body == '<p>Edited article</p>'
    assert home.programme_sections[0].value['heading'] == 'Edited section'
    assert NewsPage.objects.count() == count
