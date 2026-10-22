from django.contrib import admin
from apps.core.admin import ProgrammeScopedAdmin, SuperuserOnlyAdmin
from .models import Foundation, Programme, ProgrammeMembership, Initiative, Project, Activity

admin.site.register(Foundation, SuperuserOnlyAdmin)
admin.site.register(Programme, SuperuserOnlyAdmin)
admin.site.register(ProgrammeMembership, SuperuserOnlyAdmin)

@admin.register(Initiative)
class InitiativeAdmin(ProgrammeScopedAdmin):
    list_display = ['name', 'programme']
    parent_fields = {'programme': 'pk'}

    def get_readonly_fields(self, request, obj=None):
        return [] if request.user.is_superuser else ['linked_site']

@admin.register(Project)
class ProjectAdmin(ProgrammeScopedAdmin):
    list_display = ['name', 'initiative']
    programme_lookup = 'initiative__programme'
    parent_fields = {'initiative': 'programme'}

@admin.register(Activity)
class ActivityAdmin(ProgrammeScopedAdmin):
    list_display = ['name', 'project', 'date', 'status']
    programme_lookup = 'project__initiative__programme'
    parent_fields = {'project': 'initiative__programme'}
