from django.apps import AppConfig


class StaffConfig(AppConfig):
    name = 'apps.staff'
    verbose_name = 'Staff portfolios'

    def ready(self):
        from . import signals  # noqa: F401
