"""Submission emails: a receipt for the visitor and an alert for the site team.

Both are sent after the database commit and never block or fail the submission;
delivery problems are logged for operators instead.
"""
import logging
from django.conf import settings
from django.core.mail import EmailMessage
from django.template.loader import render_to_string
from apps.core.models import SiteBranding

logger = logging.getLogger(__name__)


def staff_recipients(submission):
    configured = list(getattr(settings, 'SUBMISSION_NOTIFY_EMAILS', []))
    site_email = SiteBranding.for_site(submission.site).email
    return sorted({*configured, *([site_email] if site_email else [])})


def _context(submission):
    branding = SiteBranding.for_site(submission.site)
    return {
        'submission': submission,
        'site_name': branding.display_name or submission.site.site_name,
        'reply_email': branding.email,
        'admin_url': f"{settings.WAGTAILADMIN_BASE_URL.rstrip('/')}/operations/engagement/submission/{submission.pk}/change/",
    }


def _send(subject, template, context, recipients, reply_to=None):
    message = EmailMessage(subject, render_to_string(template, context), settings.DEFAULT_FROM_EMAIL, recipients,
                           reply_to=[reply_to] if reply_to else None)
    message.send()


def send_submission_emails(submission):
    if not getattr(settings, 'SUBMISSION_EMAILS_ENABLED', True):
        return
    context = _context(submission)
    try:
        _send(f"We received your {submission.kind_label.lower()} – {context['site_name']}",
              'engagement/email/receipt.txt', context, [submission.email], reply_to=context['reply_email'])
    except Exception:
        logger.exception('Submission receipt email failed for %s', submission.reference)
    recipients = staff_recipients(submission)
    if not recipients:
        return
    try:
        _send(f"New {submission.kind_label.lower()} on {context['site_name']}",
              'engagement/email/staff_alert.txt', context, recipients, reply_to=submission.email)
    except Exception:
        logger.exception('Submission staff alert failed for %s', submission.reference)

