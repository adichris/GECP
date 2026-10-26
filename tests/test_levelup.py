import csv
import io
import json
import re
from datetime import timedelta
from unittest import mock
import pytest
from django.contrib.admin.sites import AdminSite
from django.contrib.auth import get_user_model
from django.core import mail
from django.test import RequestFactory
from django.utils import timezone
from apps.core.models import SiteBranding
from apps.engagement.admin import SubmissionAdmin, spreadsheet_safe
from apps.engagement.models import Submission
from apps.events.calendar import fold
from apps.events.models import EventPage
from apps.opportunities.models import OpportunityPage
from apps.programmes.models import Programme

pytestmark = pytest.mark.django_db
HOST = {'HTTP_HOST': 'gccs.localhost:8000'}


def gccs_root():
    return Programme.objects.get(code='gccs').site.root_page


def add_event(title, start_offset_days, live=True, location='Accra'):
    start = timezone.now() + timedelta(days=start_offset_days)
    event = EventPage(title=title, slug=re.sub(r'\W+', '-', title.lower()).strip('-'), summary=f'{title} summary',
                      starts_at=start, ends_at=start + timedelta(hours=2), location=location, live=live)
    return gccs_root().add_child(instance=event)


def add_opportunity(title, deadline=None, accepts=True):
    page = OpportunityPage(title=title, slug=re.sub(r'\W+', '-', title.lower()).strip('-'), summary='s',
                           deadline=deadline, accepts_applications=accepts)
    return gccs_root().add_child(instance=page)


def test_homepage_search_offers_site_scope(seeded, client):
    content = client.get('/', **HOST).content.decode()
    assert '<option value="site" selected>This site</option>' in content
    assert '</option value' not in content


def test_events_split_into_upcoming_and_past(seeded, client):
    later, sooner, past = add_event('Later fair', 20), add_event('Sooner fair', 2), add_event('Past fair', -10)
    upcoming = list(client.get('/explore/?kind=events', **HOST).context['items'])
    assert past not in upcoming
    assert upcoming.index(sooner) < upcoming.index(later)
    response = client.get('/explore/?kind=events&when=past', HTTP_HX_REQUEST='true', **HOST)
    assert past in list(response.context['items']) and sooner not in list(response.context['items'])
    assert b'Past events' in response.content


def test_open_opportunities_listed_first_and_closed_hidden_from_home(seeded, client):
    today = timezone.localdate()
    closed = add_opportunity('Closed call', deadline=today - timedelta(days=1))
    paused = add_opportunity('Paused call', accepts=False)
    closing = add_opportunity('Closing soon', deadline=today + timedelta(days=1))
    items = list(client.get('/explore/?kind=opportunities', **HOST).context['items'])
    assert items[0] == closing
    assert items.index(closing) < items.index(closed) and items.index(closing) < items.index(paused)
    home = list(client.get('/', **HOST).context['opportunities'])
    assert closing in home and closed not in home and paused not in home
    assert all(item.is_open for item in home)


def test_event_ics_download(seeded, client):
    event = add_event('Careers, skills; and more\\ ' + 'x' * 120, 5, location='Hall 1, Accra')
    response = client.get(f'/events/{event.pk}/calendar.ics', **HOST)
    assert response.status_code == 200
    assert response['Content-Type'].startswith('text/calendar')
    body = response.content.decode()
    assert body.startswith('BEGIN:VCALENDAR\r\n') and body.endswith('END:VCALENDAR\r\n')
    unfolded = body.replace('\r\n ', '')
    assert 'SUMMARY:Careers\\, skills\\; and more\\\\ ' in unfolded
    assert 'LOCATION:Hall 1\\, Accra' in unfolded
    assert f'UID:event-{event.pk}@gccs.localhost' in unfolded
    assert all(len(line.encode()) <= 75 for line in body.split('\r\n'))
    detail = client.get(event.url, **HOST).content.decode()
    assert f'/events/{event.pk}/calendar.ics' in detail


def test_ics_respects_site_scope_and_drafts(seeded, client):
    event, draft = add_event('Scoped event', 3), add_event('Draft event', 3, live=False)
    assert client.get(f'/events/{event.pk}/calendar.ics', HTTP_HOST='pec.localhost:8000').status_code == 404
    assert client.get(f'/events/{draft.pk}/calendar.ics', **HOST).status_code == 404
    feed = client.get('/events/calendar.ics', **HOST).content.decode()
    assert 'SUMMARY:Scoped event' in feed and 'Draft event' not in feed


def test_fold_never_splits_multibyte_characters():
    folded = fold('DESCRIPTION:' + 'é🌱' * 60)
    for line in folded.split('\r\n'):
        assert len(line.encode('utf-8')) <= 75
    assert folded.replace('\r\n ', '') == 'DESCRIPTION:' + 'é🌱' * 60


def submit_contact(client):
    token = client.get('/contact/', **HOST).context['form_token']
    data = {'name': 'Ama', 'email': 'ama@example.org', 'message': 'Unique visitor text', 'consent': 'on', 'form_token': token}
    return client.post('/contact/', data, HTTP_HX_REQUEST='true', **HOST), data


def test_submission_sends_receipt_and_staff_alert_once(seeded, client, django_capture_on_commit_callbacks, settings):
    settings.SUBMISSION_NOTIFY_EMAILS = ['team@example.org']
    brand = SiteBranding.for_site(Programme.objects.get(code='gccs').site)
    brand.email = 'gccs@example.org'
    brand.save()
    with django_capture_on_commit_callbacks(execute=True):
        response, data = submit_contact(client)
    assert b'confirmation' in response.content
    submission = Submission.objects.get()
    receipt, alert = mail.outbox
    assert receipt.to == ['ama@example.org'] and str(submission.reference) in receipt.body
    assert 'Unique visitor text' not in receipt.body  # visitor-supplied text is never echoed to an unverified address
    assert receipt.reply_to == ['gccs@example.org']
    assert sorted(alert.to) == ['gccs@example.org', 'team@example.org']
    assert alert.reply_to == ['ama@example.org']
    assert f'/operations/engagement/submission/{submission.pk}/change/' in alert.body
    with django_capture_on_commit_callbacks(execute=True):
        client.post('/contact/', data, HTTP_HX_REQUEST='true', **HOST)  # replayed token
    assert len(mail.outbox) == 2


def test_intake_alert_uses_visitor_labels(seeded, client, django_capture_on_commit_callbacks, settings):
    settings.SUBMISSION_NOTIFY_EMAILS = ['team@example.org']
    token = client.get('/participate/learning/', **HOST).context['form_token']
    data = {'name': 'Kofi', 'email': 'k@example.org', 'consent': 'on', 'form_token': token,
            'learning_interest': 'Robotics', 'learning_format': 'Online', 'availability': 'Weekends'}
    with django_capture_on_commit_callbacks(execute=True):
        client.post('/participate/learning/', data, **HOST)
    alert = mail.outbox[1]
    assert 'What would you like to learn?: Robotics' in alert.body
    assert alert.subject == 'New learning enquiry on ' + SiteBranding.for_site(Programme.objects.get(code='gccs').site).display_name


def test_email_failure_never_breaks_submission(seeded, client, django_capture_on_commit_callbacks):
    with mock.patch('apps.engagement.notifications.EmailMessage.send', side_effect=OSError('smtp down')):
        with django_capture_on_commit_callbacks(execute=True):
            response, _ = submit_contact(client)
    assert response.status_code == 200 and Submission.objects.count() == 1


def test_submission_admin_actions_and_safe_csv(seeded):
    site = Programme.objects.get(code='gccs').site
    item = Submission.objects.create(site=site, name='=HYPERLINK("x")', email='a@example.org', message='-2+3',
                                     consent=True, kind='learning', details={'learning_interest': '@cmd'})
    admin = SubmissionAdmin(Submission, AdminSite())
    request = RequestFactory().get('/operations/')
    request.user = get_user_model().objects.create_superuser('root', 'root@example.org', 'pw')
    request._messages = mock.MagicMock()
    queryset = Submission.objects.filter(pk=item.pk)
    admin.mark_reviewing(request, queryset)
    item.refresh_from_db()
    assert item.status == 'reviewing'
    rows = list(csv.reader(io.StringIO(admin.export_csv(request, queryset).content.decode('utf-8-sig'))))
    header, row = rows
    assert header[-1] == 'learning_interest'
    assert row[header.index('name')] == "'=HYPERLINK(\"x\")"
    assert row[header.index('message')] == "'-2+3"
    assert row[-1] == "'@cmd"
    assert spreadsheet_safe('Plain') == 'Plain'
    assert 'staff_notes' in admin.fields and 'staff_notes' not in admin.readonly_fields


def test_social_metadata_and_structured_data(seeded, client):
    event = add_event('Open </script><script>alert(1)</script> day', 4)
    content = client.get(event.url, **HOST).content.decode()
    assert '<meta property="og:title"' in content and 'og:url' in content
    match = re.search(r'<script type="application/ld\+json">(.*?)</script>', content, re.S)
    assert '<script>alert' not in match.group(1)
    data = json.loads(match.group(1))
    assert data['@type'] == 'Event' and data['name'].startswith('Open </script>')
    assert data['location']['name'] == 'Accra'
    home = client.get('/', **HOST).content.decode()
    data = json.loads(re.search(r'<script type="application/ld\+json">(.*?)</script>', home, re.S).group(1))
    assert data['@type'] == 'Organization'


def test_robots_lists_sitemap(seeded, client):
    body = client.get('/robots.txt', **HOST).content.decode()
    assert 'Sitemap: http://gccs.localhost:8000/sitemap.xml' in body
