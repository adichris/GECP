from django.contrib import admin
from apps.core.admin import ProgrammeScopedAdmin
from .models import Submission

@admin.register(Submission)
class SubmissionAdmin(ProgrammeScopedAdmin):
    programme_lookup = 'site__programme'
    list_display = ['reference', 'site', 'kind', 'opportunity', 'created_at', 'status']
    list_filter = ['status', 'kind']
    readonly_fields = ['reference', 'site', 'kind', 'details', 'opportunity', 'name', 'email', 'message', 'consent', 'created_at']
    def has_add_permission(self, request):
        return False
