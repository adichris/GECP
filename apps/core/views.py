from django.core.paginator import Paginator
from django.db import connection
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_GET
from django.views.decorators.vary import vary_on_headers
from wagtail.models import Page
from .services import public_pages, network_context, is_partial

def health(request):
    try:
        with connection.cursor() as cursor:
            cursor.execute('SELECT 1')
        return JsonResponse({'status': 'ok'})
    except Exception:
        return JsonResponse({'status': 'unavailable'}, status=503)

@require_GET
@vary_on_headers('HX-Request', 'HX-History-Restore-Request')
def search(request):
    query = request.GET.get('q', '').strip()[:200]
    scope = 'all' if request.GET.get('scope') == 'all' else 'site'
    programme_code = request.GET.get('programme', '')[:50] if scope == 'all' else ''
    results = public_pages(request, across_network=scope == 'all', programme_code=programme_code).search(query) if query else Page.objects.none()
    page = Paginator(results, 12).get_page(request.GET.get('page'))
    page.object_list = list(page.object_list)
    for result in page.object_list:
        result.result_site = next((site for site in network_context(request)['network_sites'] if result.path.startswith(site.root_page.path)), request.site)
    template = 'core/partials/search_results.html' if is_partial(request) else 'core/search.html'
    return render(request, template, {'query': query, 'results': page, 'scope': scope, 'programme_code': programme_code, 'title': 'Search'})

@require_GET
@vary_on_headers('HX-Request', 'HX-History-Restore-Request')
def explore(request):
    from apps.news.models import NewsPage
    from apps.events.models import EventPage
    from apps.opportunities.models import OpportunityPage
    from apps.resources.models import ResourcePage
    kinds = {'news': NewsPage, 'events': EventPage, 'opportunities': OpportunityPage, 'resources': ResourcePage}
    kind = request.GET.get('kind', 'opportunities')
    if kind not in kinds:
        kind = 'opportunities'
    items = kinds[kind].objects.live().public().descendant_of(request.site.root_page).order_by('-first_published_at')
    page = Paginator(items, 9).get_page(request.GET.get('page'))
    template = 'core/partials/listing.html' if is_partial(request) else 'core/explore.html'
    return render(request, template, {'items': page, 'kind': kind, 'kinds': kinds})


@require_GET
def directory(request):
    return render(request, 'core/directory.html', {'title': 'Our programmes'})


@require_GET
@vary_on_headers('HX-Request', 'HX-History-Restore-Request')
def blog(request):
    from apps.news.models import NewsPage
    network = network_context(request)
    posts = public_pages(request, NewsPage, across_network=network['current_programme'] is None).filter(content_kind='blog')
    topics = list(posts.order_by('topic').values_list('topic', flat=True).distinct())
    topic = request.GET.get('topic', '')[:80]
    if topic:
        posts = posts.filter(topic=topic)
    items = Paginator(posts.order_by('-published_date', '-first_published_at'), 9).get_page(request.GET.get('page'))
    return render(request, 'core/partials/blog_results.html' if is_partial(request) else 'core/blog.html', {'items': items, 'topics': topics, 'topic': topic, 'title': 'Programme journal'})


@require_GET
def library(request):
    from apps.resources.models import LibraryAsset
    scope = 'all' if request.GET.get('scope') == 'all' else 'site'
    sites = network_context(request)['network_sites'] if scope == 'all' else [request.site]
    items = LibraryAsset.objects.filter(is_public=True, sites__in=sites).select_related('image').distinct()
    return render(request, 'core/library.html', {'title': 'Media library', 'assets': items, 'scope': scope})


@require_GET
def asset_detail(request, slug):
    from apps.resources.models import LibraryAsset
    asset = get_object_or_404(LibraryAsset.objects.filter(is_public=True, sites__in=network_context(request)['network_sites']).select_related('image').distinct(), slug=slug)
    return render(request, 'core/asset_detail.html', {'title': asset.title, 'asset': asset})

def robots(request):
    return HttpResponse('User-agent: *\nDisallow: /admin/\nDisallow: /operations/\n', content_type='text/plain')
