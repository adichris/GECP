"""Minimal RFC 5545 (iCalendar) output for public events."""
from datetime import timezone as dt_timezone
from django.utils import timezone

PRODID = '-//GECP Foundation//Digital Platform//EN'


def escape(value):
    return (
        str(value).replace('\\', '\\\\').replace(';', '\\;').replace(',', '\\,')
        .replace('\r\n', '\\n').replace('\n', '\\n').replace('\r', '\\n')
    )


def fold(line):
    """Fold content lines at 75 octets without splitting multi-byte characters."""
    out, current = [], ''
    for char in line:
        limit = 75 if not out else 74  # continuation lines start with a space
        if len((current + char).encode('utf-8')) > limit:
            out.append(current)
            current = char
        else:
            current += char
    out.append(current)
    return '\r\n '.join(out)


def utc_stamp(value):
    return value.astimezone(dt_timezone.utc).strftime('%Y%m%dT%H%M%SZ')


def event_lines(event, request):
    url = event.get_full_url(request)
    return [
        'BEGIN:VEVENT',
        f'UID:event-{event.pk}@{request.site.hostname}',
        f'DTSTAMP:{utc_stamp(event.last_published_at or timezone.now())}',
        f'DTSTART:{utc_stamp(event.starts_at)}',
        f'DTEND:{utc_stamp(event.ends_at)}',
        f'SUMMARY:{escape(event.title)}',
        f'DESCRIPTION:{escape(event.summary + chr(10) + chr(10) + url)}',
        f'LOCATION:{escape(event.location)}',
        f'URL:{url}',
        'END:VEVENT',
    ]


def calendar(events, request, name):
    lines = ['BEGIN:VCALENDAR', 'VERSION:2.0', f'PRODID:{PRODID}', 'CALSCALE:GREGORIAN', 'METHOD:PUBLISH',
             f'X-WR-CALNAME:{escape(name)}']
    for event in events:
        lines.extend(event_lines(event, request))
    lines.append('END:VCALENDAR')
    return '\r\n'.join(fold(line) for line in lines) + '\r\n'
