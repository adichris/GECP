import csv
from django.contrib import admin
from django.http import HttpResponse
from django.utils import timezone
from apps.core.admin import ProgrammeScopedAdmin
from .models import Submission

EXPORT_FIELDS = ['reference', 'created_at', 'site', 'kind', 'opportunity', 'status', 'name', 'email', 'message']


def spreadsheet_safe(value):
    """Neutralise values a spreadsheet would otherwise execute as a formula (CSV injection)."""
    text = '' if value is None else str(value)
    return "'" + text if text[:1] in ('=', '+', '-', '@', '\t', '\r') else text


@admin.register(Submission)
class SubmissionAdmin(ProgrammeScopedAdmin):
    programme_lookup = 'site__programme'
    list_display = ['reference', 'name', 'kind', 'site', 'opportunity', 'created_at', 'status']
    list_filter = ['status', 'kind', 'site', 'created_at']
    list_select_related = ['site', 'opportunity']
    search_fields = ['reference', 'name', 'email', 'message']
    date_hierarchy = 'created_at'
    readonly_fields = ['reference', 'site', 'kind', 'details', 'opportunity', 'name', 'email', 'message', 'consent', 'created_at', 'updated_at']
    fields = ['status', 'staff_notes', *readonly_fields]
    actions = ['mark_reviewing', 'mark_closed', 'export_csv']

    def has_add_permission(self, request):
        return False

    def _set_status(self, request, queryset, status):
        count = queryset.update(status=status, updated_at=timezone.now())
        self.message_user(request, f'{count} submission(s) marked as {dict(Submission.STATUSES)[status].lower()}.')

    @admin.action(description='Mark selected as reviewing', permissions=['change'])
    def mark_reviewing(self, request, queryset):
        self._set_status(request, queryset, 'reviewing')

    @admin.action(description='Mark selected as closed', permissions=['change'])
    def mark_closed(self, request, queryset):
        self._set_status(request, queryset, 'closed')

    @admin.action(description='Export selected to CSV', permissions=['view'])
    def export_csv(self, request, queryset):
        response = HttpResponse(content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = f'attachment; filename="submissions-{timezone.localdate():%Y-%m-%d}.csv"'
        response.write(chr(0xFEFF))  # byte-order mark lets Excel detect UTF-8
        writer = csv.writer(response)
        detail_keys = sorted({key for item in queryset for key in item.details})
        writer.writerow([*EXPORT_FIELDS, *detail_keys])
        for item in queryset.select_related('site', 'opportunity'):
            row = [getattr(item, field) for field in EXPORT_FIELDS] + [item.details.get(key, '') for key in detail_keys]
            writer.writerow([spreadsheet_safe(value) for value in row])
        return response
