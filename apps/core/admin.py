from django.contrib import admin

class ProgrammeScopedAdmin(admin.ModelAdmin):
    """Django permissions AND programme membership are required."""
    programme_lookup = 'programme'
    parent_fields = {}

    def programme_ids(self, request):
        return request.user.programmemembership_set.values_list('programme_id', flat=True)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs if request.user.is_superuser else qs.filter(**{f'{self.programme_lookup}__in': self.programme_ids(request)})

    def allowed(self, request, obj):
        return obj is None or request.user.is_superuser or self.get_queryset(request).filter(pk=obj.pk).exists()

    def has_view_permission(self, request, obj=None):
        return super().has_view_permission(request, obj) and self.allowed(request, obj)

    def has_change_permission(self, request, obj=None):
        return super().has_change_permission(request, obj) and self.allowed(request, obj)

    def has_delete_permission(self, request, obj=None):
        return super().has_delete_permission(request, obj) and self.allowed(request, obj)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        lookup = self.parent_fields.get(db_field.name)
        if lookup is not None and not request.user.is_superuser:
            kwargs['queryset'] = db_field.remote_field.model.objects.filter(**{f'{lookup}__in': self.programme_ids(request)})
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

class SuperuserOnlyAdmin(admin.ModelAdmin):
    def has_module_permission(self, request):
        return request.user.is_superuser
    def has_view_permission(self, request, obj=None):
        return request.user.is_superuser
    def has_add_permission(self, request):
        return request.user.is_superuser
    def has_change_permission(self, request, obj=None):
        return request.user.is_superuser
    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser
