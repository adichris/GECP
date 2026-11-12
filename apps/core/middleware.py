from django.http import HttpResponseNotFound
from django.http.request import split_domain_port
from wagtail.models import Site

class StrictSiteMiddleware:
    """Reject unknown hosts instead of Wagtail's default-site fallback."""
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path == '/healthz/':
            return self.get_response(request)
        host, port = split_domain_port(request.get_host())
        port = int(port or (443 if request.is_secure() else 80))
        sites = Site.objects.select_related('root_page')
        site = sites.filter(hostname=host, port=port).first()
        if site is None and port in (80, 443):
            # Behind an HTTPS-terminating proxy the scheme (and so the default port) can differ from
            # the port a site was registered with; standard web ports are treated as equivalent.
            site = sites.filter(hostname=host, port=443 if port == 80 else 80).first()
        if site is None:
            return HttpResponseNotFound('This hostname and port are not configured for a GECP site.')
        request.site = site
        request._wagtail_site = site
        return self.get_response(request)
