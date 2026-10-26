"""Social sharing (Open Graph) and schema.org structured data for public pages."""
import json
from django import template
from django.utils.html import strip_tags
from django.utils.safestring import mark_safe

register = template.Library()
# JSON unicode escapes (backslash-u + 4 hex digits) for characters that could close a <script> element.
JSON_SCRIPT_ESCAPES = {ord(char): '\\u' + format(ord(char), '04x') for char in '<>&'}


def share_image(page, branding):
    for image in (getattr(page, 'image', None), getattr(page, 'hero_image', None), getattr(branding, 'logo', None)):
        if image:
            return image
    return None


@register.simple_tag(takes_context=True)
def share_image_url(context):
    request = context['request']
    image = share_image(context.get('page'), context.get('branding'))
    if not image:
        return ''
    try:
        return request.build_absolute_uri(image.get_rendition('fill-1200x630').url)
    except Exception:  # missing source file must never break page rendering
        return ''


def page_schema(page, request, branding, image_url):
    url = page.get_full_url(request)
    organisation = {'@type': 'Organization', 'name': branding.display_name or request.site.site_name,
                    'url': request.site.root_url}
    description = getattr(page, 'summary', '') or page.search_description or getattr(page, 'introduction', '')
    kind = page.specific_class.__name__
    if kind == 'EventPage':
        data = {
            '@type': 'Event', 'name': page.title, 'description': description, 'url': url,
            'startDate': page.starts_at.isoformat(), 'endDate': page.ends_at.isoformat(),
            'eventStatus': 'https://schema.org/EventScheduled',
            'location': {'@type': 'Place', 'name': page.location, 'address': page.location},
            'organizer': organisation,
        }
    elif kind == 'NewsPage':
        data = {
            '@type': 'BlogPosting' if page.content_kind == 'blog' else 'NewsArticle', 'headline': page.title[:110],
            'description': description, 'url': url, 'datePublished': page.published_date.isoformat(),
            'dateModified': (page.last_published_at or page.latest_revision_created_at).date().isoformat()
            if (page.last_published_at or page.latest_revision_created_at) else page.published_date.isoformat(),
            'publisher': organisation, 'author': organisation, 'mainEntityOfPage': url,
        }
    elif kind == 'HomePage':
        data = {**organisation, 'description': branding.tagline or description}
        if branding.email:
            data['email'] = branding.email
        same_as = [link.url for link in branding.social_links.all()]
        if same_as:
            data['sameAs'] = same_as
    else:
        data = {'@type': 'WebPage', 'name': page.title, 'description': description, 'url': url}
    if image_url:
        data['logo' if kind == 'HomePage' else 'image'] = image_url
    data['description'] = strip_tags(data.get('description') or '')[:500]
    return {'@context': 'https://schema.org', **data}


@register.simple_tag(takes_context=True)
def structured_data(context, image_url=''):
    page, request, branding = context.get('page'), context.get('request'), context.get('branding')
    if not page or not request or branding is None or not getattr(page, 'live', False):
        return ''
    payload = json.dumps(page_schema(page.specific, request, branding, image_url), ensure_ascii=False)
    # Escape characters that could close the script element or start an HTML comment.
    payload = payload.translate(JSON_SCRIPT_ESCAPES)
    return mark_safe(f'<script type="application/ld+json">{payload}</script>')
