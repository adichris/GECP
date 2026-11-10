from django.contrib import admin
from apps.core.admin import SuperuserOnlyAdmin
from .models import PortfolioItem, StaffProfile


class PortfolioItemInline(admin.StackedInline):
    model = PortfolioItem
    extra = 0
    fields = ['title', 'kind', 'summary', 'projects', 'is_public', 'hidden_by_admin']
    filter_horizontal = ['projects']
    show_change_link = True


@admin.register(StaffProfile)
class StaffProfileAdmin(SuperuserOnlyAdmin):
    list_display = ['display_name', 'job_title', 'user', 'is_public', 'hidden_by_admin', 'updated_at']
    list_filter = ['is_public', 'hidden_by_admin', 'programmes']
    search_fields = ['display_name', 'job_title', 'user__username', 'user__email']
    prepopulated_fields = {'slug': ['display_name']}
    filter_horizontal = ['programmes']
    raw_id_fields = ['user']
    inlines = [PortfolioItemInline]
    actions = ['hide', 'unhide']

    @admin.action(description='Hide selected profiles from the public site')
    def hide(self, request, queryset):
        self.message_user(request, f'{queryset.update(hidden_by_admin=True)} profile(s) hidden.')

    @admin.action(description='Restore selected profiles')
    def unhide(self, request, queryset):
        self.message_user(request, f'{queryset.update(hidden_by_admin=False)} profile(s) restored.')


@admin.register(PortfolioItem)
class PortfolioItemAdmin(SuperuserOnlyAdmin):
    list_display = ['title', 'profile', 'kind', 'is_public', 'hidden_by_admin', 'updated_at']
    list_filter = ['kind', 'is_public', 'hidden_by_admin']
    search_fields = ['title', 'summary', 'profile__display_name']
    filter_horizontal = ['projects']
    list_select_related = ['profile']
    actions = ['hide', 'unhide']

    @admin.action(description='Hide selected items from the public site')
    def hide(self, request, queryset):
        self.message_user(request, f'{queryset.update(hidden_by_admin=True)} item(s) hidden.')

    @admin.action(description='Restore selected items')
    def unhide(self, request, queryset):
        self.message_user(request, f'{queryset.update(hidden_by_admin=False)} item(s) restored.')
