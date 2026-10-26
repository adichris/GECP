import uuid
from django.db import models

class Submission(models.Model):
    STATUSES = [('new', 'New'), ('reviewing', 'Reviewing'), ('closed', 'Closed')]
    reference = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    site = models.ForeignKey('wagtailcore.Site', on_delete=models.PROTECT)
    opportunity = models.ForeignKey('opportunities.OpportunityPage', null=True, blank=True, on_delete=models.PROTECT)
    name = models.CharField(max_length=120)
    email = models.EmailField()
    message = models.TextField(max_length=5000)
    kind = models.CharField(max_length=30, default='contact', db_index=True)
    details = models.JSONField(default=dict, blank=True)
    consent = models.BooleanField()
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, default='new', choices=STATUSES)
    staff_notes = models.TextField(blank=True, help_text='Internal only. Never shown to the person who submitted.')
    updated_at = models.DateTimeField(auto_now=True, null=True)
    class Meta:
        ordering = ['-created_at']
    def __str__(self):
        return str(self.reference)

    @property
    def kind_label(self):
        from .intake import INTAKES
        if self.kind in INTAKES:
            return INTAKES[self.kind]['label']
        return 'Application' if self.kind == 'application' else 'Enquiry'

    @property
    def detail_items(self):
        """(label, value) pairs for intake answers, labelled as the visitor saw them."""
        from .intake import INTAKES
        labels = dict(INTAKES.get(self.kind, {}).get('fields', []))
        return [(labels.get(key, key.replace('_', ' ').capitalize()), value) for key, value in self.details.items()]
