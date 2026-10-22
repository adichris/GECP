from django.db import models
from django.utils import timezone
from wagtail.admin.panels import FieldPanel
from apps.core.models import SharedContentPage

class OpportunityPage(SharedContentPage):
    template = 'core/content_detail.html'
    category = models.CharField(max_length=30, choices=[('interest', 'Expression of interest'), ('training', 'Training'), ('work', 'Work experience'), ('scholarship', 'Scholarship'), ('volunteer', 'Volunteering')], default='training')
    deadline = models.DateField(null=True, blank=True)
    accepts_applications = models.BooleanField(default=True)
    content_panels = SharedContentPage.content_panels + [FieldPanel('category'), FieldPanel('deadline'), FieldPanel('accepts_applications')]
    @property
    def is_open(self):
        return self.accepts_applications and (not self.deadline or self.deadline >= timezone.localdate())
