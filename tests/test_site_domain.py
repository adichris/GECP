import pytest
from django.core.management import CommandError, call_command
from wagtail.models import Site

pytestmark = pytest.mark.django_db


def hosts():
    return sorted(Site.objects.values_list('hostname', 'port'))


def test_dry_run_changes_nothing():
    before = hosts()
    call_command('set_site_domain', domain='gecpfoundation.org', port=443, dry_run=True)
    assert hosts() == before


def test_moves_foundation_and_programmes_and_serves_them(client, settings):
    settings.ALLOWED_HOSTS = ['.gecpfoundation.org', 'gecpfoundation.org', 'localhost']
    call_command('set_site_domain', domain='gecpfoundation.org', port=443)
    names = dict(Site.objects.values_list('hostname', 'port'))
    assert names['gecpfoundation.org'] == 443 and names['gccs.gecpfoundation.org'] == 443
    assert not Site.objects.filter(hostname__endswith='localhost').exists()
    assert client.get('/', HTTP_HOST='gecpfoundation.org', secure=True).status_code == 200
    assert client.get('/', HTTP_HOST='gccs.gecpfoundation.org', secure=True).status_code == 200
    assert client.get('/', HTTP_HOST='localhost:8000').status_code == 404


def test_https_site_still_found_when_proxy_reports_port_80(client, settings):
    settings.ALLOWED_HOSTS = ['gecpfoundation.org']
    call_command('set_site_domain', domain='gecpfoundation.org', port=443)
    assert client.get('/', HTTP_HOST='gecpfoundation.org', secure=False).status_code == 200


def test_refuses_to_overwrite_an_unrelated_site():
    other = Site.objects.exclude(hostname__endswith='localhost').exclude(hostname='localhost').first()
    root = Site.objects.get(hostname='localhost').root_page
    Site.objects.create(hostname='gecpfoundation.org', port=443, root_page=root, site_name='Stray') if other is None else None
    with pytest.raises(CommandError, match='already used'):
        call_command('set_site_domain', domain='gecpfoundation.org', port=443)


def test_rejects_urls():
    with pytest.raises(CommandError):
        call_command('set_site_domain', domain='https://gecpfoundation.org/', port=443)
