from django.contrib import admin
from apps.core.admin import SuperuserOnlyAdmin
from .models import LibraryAsset


@admin.register(LibraryAsset)
class LibraryAssetAdmin(SuperuserOnlyAdmin):
    list_display = ['title', 'kind', 'is_public', 'is_archive']
    list_filter = ['kind', 'is_public', 'is_archive']
    filter_horizontal = ['sites']
    prepopulated_fields = {'slug': ['title']}
