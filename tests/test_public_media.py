import pytest
from django.urls import resolve

from apps.core.media import is_public_media

pytestmark = pytest.mark.django_db
FOUNDATION = {'HTTP_HOST': 'localhost:8000'}
PNG = (b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89'
       b'\x00\x00\x00\rIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82')


@pytest.fixture
def media(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    for rel, body in {
        'images/logo.max-120x120.png': PNG,
        'staff/photos/staff-abc.png': PNG,
        'staff/portfolio/portfolio-abc.png': PNG,
        'documents/private-report.pdf': b'%PDF-1.4 secret',
        'documents/leak.png': PNG,
        'original_images/raw.png': PNG,
        'staff/photos/evil.html': b'<script>alert(1)</script>',
    }.items():
        path = tmp_path / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(body)
    return tmp_path


def test_media_route_is_registered_when_debug_is_off():
    assert resolve('/media/images/x.png').url_name == 'public_media'


@pytest.mark.parametrize('url', ['/media/images/logo.max-120x120.png', '/media/staff/photos/staff-abc.png',
                                 '/media/staff/portfolio/portfolio-abc.png'])
def test_public_images_are_served_with_safe_headers(client, media, url):
    response = client.get(url, **FOUNDATION)
    assert response.status_code == 200
    assert b''.join(response.streaming_content) == PNG
    assert response['Content-Type'] == 'image/png'
    assert response['X-Content-Type-Options'] == 'nosniff'
    assert 'max-age=' in response['Cache-Control'] and 'sandbox' in response['Content-Security-Policy']


@pytest.mark.parametrize('url', ['/media/documents/private-report.pdf', '/media/documents/leak.png',
                                 '/media/original_images/raw.png', '/media/staff/photos/evil.html',
                                 '/media/staff/photos/missing.png', '/media/images/../documents/leak.png',
                                 '/media/images/%2e%2e/documents/leak.png', '/media/images/..%5cdocuments%5cleak.png'])
def test_private_or_unsafe_media_is_refused(client, media, url):
    assert client.get(url, **FOUNDATION).status_code == 404


def test_media_is_read_only(client, media):
    assert client.post('/media/images/logo.max-120x120.png', **FOUNDATION).status_code == 405


def test_unknown_host_cannot_fetch_media(client, media):
    assert client.get('/media/images/logo.max-120x120.png', HTTP_HOST='evil.example').status_code in (400, 404)


def test_is_public_media_rules():
    assert is_public_media('images/a.JPG')
    assert not is_public_media('images/sub/../../documents/a.png')
    assert not is_public_media('/images/a.png')
    assert not is_public_media('imagesx/a.png')
