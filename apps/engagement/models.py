import uuid
from django.db import models

class Submission(models.Model):
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
    status = models.CharField(max_length=20, default='new', choices=[('new', 'New'), ('reviewing', 'Reviewing'), ('closed', 'Closed')])
    class Meta:
        ordering = ['-created_at']
    def __str__(self):
        return str(self.reference)
