from django.contrib import admin
from django.db import transaction
from apps.core.admin import ProgrammeScopedAdmin
from .models import Thread, Comment, Report, ModerationLog


class ModeratedAdmin(ProgrammeScopedAdmin):
    programme_lookup = "site__programme"
    actions = ["approve", "hide"]
    list_filter = ["visibility", "site"]
    search_fields = ["body", "author__username", "guest_name"]

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def get_readonly_fields(self, request, obj=None):
        return [
            field.name
            for field in self.model._meta.fields
            if field.name
            not in (
                ["status", "locked"] if obj and obj.visibility == "withdrawn" else ["visibility", "status", "locked"]
            )
        ]

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        ModerationLog.objects.create(
            site=obj.site,
            actor=request.user,
            target_type=obj._meta.model_name,
            target_id=str(obj.pk),
            action="Updated " + ", ".join(form.changed_data),
        )

    def moderate(self, request, queryset, status):
        if not self.has_change_permission(request):
            return
        with transaction.atomic():
            for obj in self.get_queryset(request).filter(pk__in=queryset.values("pk")).select_for_update():
                if obj.visibility == "withdrawn":
                    continue
                obj.visibility = status
                obj.save(update_fields=["visibility"])
                ModerationLog.objects.create(
                    site=obj.site,
                    actor=request.user,
                    target_type=obj._meta.model_name,
                    target_id=str(obj.pk),
                    action=status,
                )

    @admin.action(description="Publish selected contributions", permissions=["change"])
    def approve(self, request, queryset):
        self.moderate(request, queryset, "approved")

    @admin.action(description="Hide selected contributions", permissions=["change"])
    def hide(self, request, queryset):
        self.moderate(request, queryset, "hidden")


@admin.register(Thread)
class ThreadAdmin(ModeratedAdmin):
    list_display = ["title", "site", "display_name", "category", "visibility", "status", "locked", "created_at"]


@admin.register(Comment)
class CommentAdmin(ModeratedAdmin):
    list_display = ["__str__", "site", "display_name", "visibility", "created_at"]


@admin.register(Report)
class ReportAdmin(ProgrammeScopedAdmin):
    programme_lookup = "site__programme"
    list_display = ["id", "site", "reporter", "status", "created_at"]
    list_filter = ["status"]
    readonly_fields = ["site", "reporter", "thread", "comment", "reason", "created_at"]

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        ModerationLog.objects.create(
            site=obj.site,
            actor=request.user,
            target_type="report",
            target_id=str(obj.pk),
            action="Report " + obj.status,
        )


@admin.register(ModerationLog)
class ModerationLogAdmin(ProgrammeScopedAdmin):
    programme_lookup = "site__programme"
    list_display = ["site", "actor", "target_type", "target_id", "action", "created_at"]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
