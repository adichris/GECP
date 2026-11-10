from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.urls import reverse
from django.utils.text import slugify


class StaffProfileQuerySet(models.QuerySet):
    def public(self):
        return self.filter(is_public=True, hidden_by_admin=False, user__is_active=True, user__is_staff=True)

    def for_programme(self, programme):
        """Staff who belong to a programme or have public work on one of its projects."""
        if programme is None:
            return self
        return self.filter(
            Q(programmes=programme)
            | Q(items__projects__initiative__programme=programme, items__is_public=True, items__hidden_by_admin=False)
        ).distinct()


class StaffProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='staff_profile')
    slug = models.SlugField(max_length=80, unique=True)
    display_name = models.CharField(max_length=120)
    job_title = models.CharField(max_length=150)
    bio = models.TextField(max_length=3000, blank=True)
    photo = models.ImageField(upload_to='staff/photos/', blank=True)
    programmes = models.ManyToManyField('programmes.Programme', blank=True, related_name='staff_profiles',
                                        help_text='Programmes this person works with. Optional.')
    website_url = models.URLField(blank=True)
    linkedin_url = models.URLField(blank=True)
    is_public = models.BooleanField(default=True, help_text='Show this profile in the public team directory.')
    hidden_by_admin = models.BooleanField(default=False, help_text='Administrators can hide a profile without deleting it.')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    objects = StaffProfileQuerySet.as_manager()

    class Meta:
        ordering = ['display_name']

    def __str__(self):
        return self.display_name

    def get_absolute_url(self):
        return reverse('staff:profile', args=[self.slug])

    @property
    def is_visible(self):
        return self.is_public and not self.hidden_by_admin and self.user.is_active and self.user.is_staff

    def public_items(self):
        return self.items.filter(is_public=True, hidden_by_admin=False).prefetch_related('projects__initiative__programme')

    @classmethod
    def unique_slug(cls, name, exclude_pk=None):
        base = slugify(name)[:70] or 'staff'
        slug, n = base, 2
        while cls.objects.filter(slug=slug).exclude(pk=exclude_pk).exists():
            slug, n = f'{base}-{n}', n + 1
        return slug


class PortfolioItem(models.Model):
    KINDS = [('project', 'Project work'), ('publication', 'Publication or research'), ('training', 'Training delivered'),
             ('event', 'Event or talk'), ('award', 'Award or recognition'), ('other', 'Other')]
    profile = models.ForeignKey(StaffProfile, on_delete=models.CASCADE, related_name='items')
    title = models.CharField(max_length=180)
    kind = models.CharField(max_length=20, choices=KINDS, default='project')
    role = models.CharField(max_length=150, blank=True, help_text='Your role in this work, e.g. "Lead facilitator".')
    summary = models.CharField(max_length=300)
    description = models.TextField(max_length=6000, blank=True)
    projects = models.ManyToManyField('programmes.Project', blank=True, related_name='portfolio_items',
                                      help_text='GECP projects this work belongs to. Optional.')
    started_on = models.DateField(null=True, blank=True)
    ended_on = models.DateField(null=True, blank=True)
    link_url = models.URLField(blank=True)
    image = models.ImageField(upload_to='staff/portfolio/', blank=True)
    is_public = models.BooleanField(default=True)
    hidden_by_admin = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = [models.F('started_on').desc(nulls_last=True), '-created_at']

    def __str__(self):
        return self.title

    def clean(self):
        if self.started_on and self.ended_on and self.ended_on < self.started_on:
            raise ValidationError({'ended_on': 'The end date cannot be before the start date.'})

    def get_absolute_url(self):
        return reverse('staff:item', args=[self.profile.slug, self.pk])
