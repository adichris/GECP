"""Serve public uploads (images only) when no web server or static site handles /media/.

Only folders listed in settings.PUBLIC_MEDIA_PREFIXES and image extensions are served. Everything
else under MEDIA_ROOT returns 404, so Wagtail documents (media/documents/) keep going through
Wagtail's permission-checked /documents/ views and original uploads are never exposed.
"""
import posixpath

from django.conf import settings
from django.http import Http404
from django.views.decorators.http import require_safe
from django.views.static import serve

IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp', '.gif', '.avif'}


def is_public_media(path):
    normalised = posixpath.normpath(path).lstrip('/')
    if normalised != path or normalised.startswith('..') or '\\' in path:
        return False
    if posixpath.splitext(normalised)[1].lower() not in IMAGE_EXTENSIONS:
        return False
    return any(normalised.startswith(prefix) for prefix in settings.PUBLIC_MEDIA_PREFIXES)


@require_safe
def public_media(request, path):
    if not is_public_media(path):
        raise Http404('Not a public media file.')
    # django.views.static.serve uses safe_join, handles If-Modified-Since and streams the file.
    response = serve(request, path, document_root=settings.MEDIA_ROOT)
    response['Cache-Control'] = f'public, max-age={settings.MEDIA_CACHE_SECONDS}'
    response['X-Content-Type-Options'] = 'nosniff'
    response['Content-Security-Policy'] = "default-src 'none'; img-src 'self'; sandbox"
    response['Cross-Origin-Resource-Policy'] = 'cross-origin'  # programme subdomains embed foundation images
    return response
