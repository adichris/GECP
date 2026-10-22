from django.core.exceptions import ValidationError
from django.db import models
from wagtail.admin.panels import FieldPanel
from apps.core.models import SharedContentPage

class EventPage(SharedContentPage):
    template = 'core/content_detail.html'
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField()
    location = models.CharField(max_length=200)
    registration_url = models.URLField(blank=True)
    content_panels = SharedContentPage.content_panels + [FieldPanel('starts_at'), FieldPanel('ends_at'), FieldPanel('location'), FieldPanel('registration_url')]
    def clean(self):
        super().clean()
        if self.starts_at and self.ends_at and self.ends_at <= self.starts_at:
            raise ValidationError({'ends_at': 'The event must end after it starts.'})
