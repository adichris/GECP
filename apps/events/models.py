from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
from wagtail.admin.panels import FieldPanel
from wagtail.models import PageManager
from wagtail.query import PageQuerySet
from apps.core.models import SharedContentPage


class EventPageQuerySet(PageQuerySet):
    def upcoming(self):
        """Events still running or yet to start, soonest first."""
        return self.filter(ends_at__gte=timezone.now()).order_by('starts_at')

    def past(self):
        return self.filter(ends_at__lt=timezone.now()).order_by('-starts_at')


class EventPage(SharedContentPage):
    template = 'core/content_detail.html'
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField()
    location = models.CharField(max_length=200)
    registration_url = models.URLField(blank=True)
    content_panels = SharedContentPage.content_panels + [FieldPanel('starts_at'), FieldPanel('ends_at'), FieldPanel('location'), FieldPanel('registration_url')]
    objects = PageManager.from_queryset(EventPageQuerySet)()

    def clean(self):
        super().clean()
        if self.starts_at and self.ends_at and self.ends_at <= self.starts_at:
            raise ValidationError({'ends_at': 'The event must end after it starts.'})

    @property
    def is_past(self):
        return self.ends_at < timezone.now()
