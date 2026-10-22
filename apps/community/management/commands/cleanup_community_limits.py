from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.community.models import RateLimit


class Command(BaseCommand):
    help = "Remove expired request-rate counters. Run daily."

    def handle(self, *args, **options):
        count, _ = RateLimit.objects.filter(created_at__lt=timezone.now() - timedelta(days=2)).delete()
        self.stdout.write(f"Removed {count} expired counters.")
