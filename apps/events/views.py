from datetime import timedelta
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.text import slugify
from django.views.decorators.http import require_GET
from apps.core.models import SiteBranding
from .calendar import calendar
from .models import EventPage


def site_events(request):
    return EventPage.objects.live().public().descendant_of(request.site.root_page)


def ics_response(body, filename):
    response = HttpResponse(body, content_type='text/calendar; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="{filename}.ics"'
    return response


@require_GET
def event_ics(request, pk):
    event = get_object_or_404(site_events(request), pk=pk)
    return ics_response(calendar([event], request, event.title), slugify(event.title) or f'event-{event.pk}')


@require_GET
def site_calendar(request):
    """Subscribable feed: upcoming events plus the last 90 days for context."""
    events = site_events(request).filter(ends_at__gte=timezone.now() - timedelta(days=90)).order_by('starts_at')[:200]
    name = SiteBranding.for_site(request.site).display_name or request.site.site_name
    response = ics_response(calendar(events, request, f'{name} events'), 'events')
    response['Content-Disposition'] = 'inline; filename="events.ics"'
    return response
