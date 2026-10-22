from django.contrib import admin
from apps.core.admin import SuperuserOnlyAdmin
from .models import Partner

@admin.register(Partner)
class PartnerAdmin(SuperuserOnlyAdmin):
    filter_horizontal = ['sites']
