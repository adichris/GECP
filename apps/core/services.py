from django.db.models import Q
from wagtail.models import Page, Site
from apps.programmes.models import Foundation, Programme
from .models import SiteBranding


def network_context(request):
    if hasattr(request, '_gecp_network'):
        return request._gecp_network
    site = request.site
    programme = Programme.objects.filter(site=site).select_related('foundation__site').first()
    foundation = programme.foundation if programme else Foundation.objects.filter(site=site).first()
    programmes = list(Programme.objects.filter(foundation=foundation, is_active=True).select_related('site__root_page')) if foundation else []
    sites = list(Site.objects.filter(pk__in=[p.site_id for p in programmes] + [foundation.site_id if foundation else site.pk]).select_related('root_page'))
    brands = {b.site_id: b for b in SiteBranding.objects.filter(site__in=sites).select_related('logo')}
    for item in programmes:
        item.branding = brands.get(item.site_id)
    groups = [{'key': key, 'title': title, 'programmes': [p for p in programmes if p.pillar == key]} for key, title in Programme.PILLARS]
    request._gecp_network = {
        'current_programme': programme, 'foundation': foundation,
        'network_programmes': programmes, 'network_sites': sites,
        'programme_groups': [group for group in groups if group['programmes']],
        'foundation_url': foundation.site.root_url if foundation else site.root_url,
    }
    return request._gecp_network


def public_pages(request, model=Page, across_network=False, programme_code=''):
    """Search only public pages in the registered foundation network."""
    sites = network_context(request)['network_sites'] if across_network else [request.site]
    if programme_code and across_network:
        allowed = [p.site_id for p in network_context(request)['network_programmes'] if p.code == programme_code]
        sites = [site for site in sites if site.pk in allowed]
    query = Q(pk__in=[])
    for site in sites:
        query |= Q(path__startswith=site.root_page.path)
    return model.objects.live().public().filter(query)


def is_partial(request):
    # HTMX history restoration needs the complete document, not a fragment.
    return request.headers.get('HX-Request') == 'true' and request.headers.get('HX-History-Restore-Request') != 'true'
