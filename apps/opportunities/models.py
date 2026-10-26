from django.db import models
from django.db.models import BooleanField, Case, F, Q, Value, When
from django.utils import timezone
from wagtail.admin.panels import FieldPanel
from wagtail.models import PageManager
from wagtail.query import PageQuerySet
from apps.core.models import SharedContentPage


class OpportunityPageQuerySet(PageQuerySet):
    def _open_q(self):
        return Q(accepts_applications=True) & (Q(deadline__isnull=True) | Q(deadline__gte=timezone.localdate()))

    def open(self):
        return self.filter(self._open_q())

    def open_first(self):
        """Open opportunities first, closing soonest; closed ones follow, newest first."""
        return self.annotate(
            open_now=Case(When(self._open_q(), then=Value(True)), default=Value(False), output_field=BooleanField())
        ).order_by('-open_now', F('deadline').asc(nulls_last=True), '-first_published_at')


class OpportunityPage(SharedContentPage):
    template = 'core/content_detail.html'
    category = models.CharField(max_length=30, choices=[('interest', 'Expression of interest'), ('training', 'Training'), ('work', 'Work experience'), ('scholarship', 'Scholarship'), ('volunteer', 'Volunteering')], default='training')
    deadline = models.DateField(null=True, blank=True)
    accepts_applications = models.BooleanField(default=True)
    content_panels = SharedContentPage.content_panels + [FieldPanel('category'), FieldPanel('deadline'), FieldPanel('accepts_applications')]
    objects = PageManager.from_queryset(OpportunityPageQuerySet)()

    @property
    def is_open(self):
        return self.accepts_applications and (not self.deadline or self.deadline >= timezone.localdate())
