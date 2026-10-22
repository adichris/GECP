from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

class Foundation(models.Model):
    name = models.CharField(max_length=160)
    site = models.OneToOneField('wagtailcore.Site', on_delete=models.PROTECT, related_name='foundation')

    def __str__(self):
        return self.name

class Programme(models.Model):
    PILLARS = [('learning', 'Education & lifelong learning'), ('pathways', 'Career guidance & pathways'), ('work', 'Employability & work'), ('enterprise', 'Technical skills & enterprise'), ('expertise', 'Talent & expertise'), ('knowledge', 'Research & knowledge')]
    foundation = models.ForeignKey(Foundation, on_delete=models.PROTECT, related_name='programmes')
    site = models.OneToOneField('wagtailcore.Site', on_delete=models.PROTECT, related_name='programme')
    name = models.CharField(max_length=160)
    code = models.SlugField(unique=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    pillar = models.CharField(max_length=20, choices=PILLARS, default='learning')

    def clean(self):
        if self.foundation_id and self.site_id == self.foundation.site_id:
            raise ValidationError('A programme needs its own site, separate from its foundation.')

    def __str__(self):
        return self.name

class ProgrammeMembership(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    programme = models.ForeignKey(Programme, on_delete=models.CASCADE)
    class Meta:
        constraints = [models.UniqueConstraint(fields=['user', 'programme'], name='unique_programme_member')]

class Initiative(models.Model):
    programme = models.ForeignKey(Programme, on_delete=models.PROTECT, related_name='initiatives')
    linked_site = models.OneToOneField('wagtailcore.Site', null=True, blank=True, on_delete=models.SET_NULL, related_name='organisational_initiative', help_text='Optional independently branded website for this initiative.')
    name = models.CharField(max_length=180)
    description = models.TextField(blank=True)
    def clean(self):
        if self.programme_id and self.linked_site_id == self.programme.site_id:
            raise ValidationError('An initiative microsite must differ from its umbrella programme site.')
    def __str__(self):
        return self.name

class Project(models.Model):
    initiative = models.ForeignKey(Initiative, on_delete=models.PROTECT, related_name='projects')
    name = models.CharField(max_length=180)
    description = models.TextField(blank=True)
    def __str__(self):
        return self.name

class Activity(models.Model):
    project = models.ForeignKey(Project, on_delete=models.PROTECT, related_name='activities')
    name = models.CharField(max_length=180)
    description = models.TextField(blank=True)
    date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=[('planned', 'Planned'), ('active', 'Active'), ('complete', 'Complete')], default='planned')
    def __str__(self):
        return self.name
