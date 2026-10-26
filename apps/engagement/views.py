import secrets
import uuid
from django.db import transaction
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods
from django.views.decorators.cache import never_cache
from apps.opportunities.models import OpportunityPage
from .forms import SubmissionForm, ProgrammeIntakeForm
from .models import Submission
from .notifications import send_submission_emails
from apps.community.security import rate_limit
from .intake import INTAKES, PROGRAMME_INTAKE
from apps.core.services import network_context

def handle_submission(request, opportunity=None, kind='contact'):
    intake_config = INTAKES.get(kind)
    title = intake_config['title'] if intake_config else (f'Apply: {opportunity.title}' if opportunity else 'Let’s start a conversation')
    session_key = f'form_token_{request.site.pk}_{opportunity.pk if opportunity else kind}'
    def build_form(data=None):
        return ProgrammeIntakeForm(data, intake=intake_config) if intake_config else SubmissionForm(data)
    if request.method == 'POST':
        form = build_form(request.POST)
        token = request.POST.get('form_token', '')
        expected = request.session.get(session_key, '')
        if not expected or not secrets.compare_digest(token, expected):
            form.add_error(None, 'This form expired or was already submitted. Please reload and try again.')
        elif form.is_valid():
            # Session throttling is supplemented by reverse-proxy rate limiting in production.
            last = request.session.get('last_submission', 0)
            if timezone.now().timestamp() - last < 30:
                return HttpResponse('Please wait 30 seconds before submitting again.', status=429)
            with transaction.atomic():
                obj = form.save(commit=False)
                obj.site = request.site
                obj.opportunity = opportunity
                obj.kind = kind
                obj, created = Submission.objects.get_or_create(
                    reference=uuid.UUID(token),
                    defaults={field: getattr(obj, field) for field in ['site', 'opportunity', 'name', 'email', 'message', 'consent', 'kind', 'details']},
                )
                if created:
                    transaction.on_commit(lambda submission=obj: send_submission_emails(submission))
            request.session.pop(session_key, None)
            request.session['last_submission'] = timezone.now().timestamp()
            request.session['submission_receipt'] = str(obj.reference)
            if request.headers.get('HX-Request') == 'true':
                return render(request, 'engagement/success.html', {'reference': obj.reference})
            return redirect(request.path + '?submitted=1')
    else:
        receipt = request.session.get('submission_receipt')
        if request.GET.get('submitted') and receipt and Submission.objects.filter(reference=receipt, site=request.site, opportunity=opportunity, kind=kind).exists():
            return render(request, 'engagement/form.html', {'reference': receipt, 'title': 'Thank you'})
        form = build_form()
        request.session[session_key] = str(uuid.uuid4())
    context = {'form': form, 'form_token': request.session.get(session_key, ''), 'title': title, 'opportunity': opportunity, 'intake': intake_config}
    template = 'engagement/partial.html' if request.headers.get('HX-Request') == 'true' else 'engagement/form.html'
    return render(request, template, context)

@require_http_methods(['GET', 'POST'])
@never_cache
@rate_limit('enquiries', limit=12, seconds=3600)
def contact(request):
    return handle_submission(request)

@require_http_methods(['GET', 'POST'])
@never_cache
@rate_limit('enquiries', limit=12, seconds=3600)
def apply(request, opportunity_id):
    opportunity = get_object_or_404(OpportunityPage.objects.live().public().descendant_of(request.site.root_page), pk=opportunity_id)
    if not opportunity.is_open:
        return HttpResponse('Applications for this opportunity are closed.', status=410)
    return handle_submission(request, opportunity, kind='application')


@require_http_methods(['GET', 'POST'])
@never_cache
@rate_limit('enquiries', limit=12, seconds=3600)
def intake(request, kind):
    programme = network_context(request)['current_programme']
    allowed = {'volunteer', 'partnership', 'learning', 'media'} if programme is None else {'volunteer', 'partnership', PROGRAMME_INTAKE.get(programme.code)}
    if kind not in INTAKES or kind not in allowed:
        raise Http404('This enquiry type is not available on this site.')
    return handle_submission(request, kind=kind)
