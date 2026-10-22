from io import StringIO
import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from apps.core.models import StandardPage
from apps.news.models import NewsPage
from apps.programmes.models import Foundation, Programme

pytestmark = pytest.mark.django_db


def remove_blogs(home):
    for post in NewsPage.objects.child_of(home).filter(content_kind='blog'):
        post.delete()


def test_all_blogs_and_repeat_preserve_edits(seeded):
    assert NewsPage.objects.filter(content_kind='blog').count() == 25
    post = NewsPage.objects.filter(content_kind='blog').first()
    post.body = '<p>Edited and unpublished</p>'
    post.save_revision().publish()
    post.unpublish()
    call_command('seed_blogs', stdout=StringIO())
    post.refresh_from_db()
    assert post.body == '<p>Edited and unpublished</p>'
    assert not post.live
    assert NewsPage.objects.filter(content_kind='blog').count() == 25


def test_foundation_only_dry_run_and_public_pages(seeded, client):
    home = Foundation.objects.get().site.root_page
    remove_blogs(home)
    before = NewsPage.objects.count()
    output = StringIO()
    call_command('seed_blogs', sites=['gecp'], dry_run=True, stdout=output)
    assert 'Planned: 3' in output.getvalue()
    assert NewsPage.objects.count() == before
    call_command('seed_blogs', sites=['gecp'], stdout=StringIO())
    posts = NewsPage.objects.child_of(home).filter(content_kind='blog')
    assert posts.count() == 3
    for post in posts:
        assert client.get(post.url, HTTP_HOST='localhost:8000').status_code == 200


def test_selected_site_drafts_remain_unpublished(seeded):
    home = Programme.objects.get(code='wwi').site.root_page
    remove_blogs(home)
    call_command('seed_blogs', sites=['wwi'], draft=True, stdout=StringIO())
    posts = NewsPage.objects.child_of(home).filter(content_kind='blog')
    assert posts.count() == 2
    assert not posts.filter(live=True).exists()
    call_command('seed_blogs', sites=['wwi'], stdout=StringIO())
    assert not posts.filter(live=True).exists()


def test_bad_site_is_rejected_before_writes(seeded):
    before = NewsPage.objects.count()
    with pytest.raises(CommandError):
        call_command('seed_blogs', sites=['gecp', 'unknown'])
    assert NewsPage.objects.count() == before


def test_slug_collision_prevents_partial_seed(seeded):
    home = Programme.objects.get(code='wwi').site.root_page
    remove_blogs(home)
    home.add_child(instance=StandardPage(title='Existing content', slug='work-learning-record'))
    with pytest.raises(CommandError, match='another page type'):
        call_command('seed_blogs', sites=['wwi'])
    assert not NewsPage.objects.child_of(home).filter(content_kind='blog').exists()
