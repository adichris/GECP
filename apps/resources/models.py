from django.core.exceptions import ValidationError
from django.db import models
from wagtail.admin.panels import FieldPanel
from apps.core.models import SharedContentPage

class ResourcePage(SharedContentPage):
    template = 'core/content_detail.html'
    document = models.ForeignKey('wagtaildocs.Document', null=True, blank=True, on_delete=models.SET_NULL, related_name='+')
    external_url = models.URLField(blank=True)
    content_panels = SharedContentPage.content_panels + [FieldPanel('document'), FieldPanel('external_url')]
    def clean(self):
        super().clean()
        if self.document_id and self.external_url:
            raise ValidationError('Choose a document or an external link, not both.')


class LibraryAsset(models.Model):
    title = models.CharField(max_length=160)
    slug = models.SlugField(unique=True)
    image = models.ForeignKey('wagtailimages.Image', on_delete=models.PROTECT, related_name='+')
    alt_text = models.CharField(max_length=240)
    caption = models.TextField(blank=True)
    source_note = models.CharField(max_length=250)
    kind = models.CharField(max_length=20, choices=[('identity', 'Brand identity'), ('brochure', 'Programme graphic'), ('illustration', 'Illustration')])
    is_archive = models.BooleanField(default=False)
    is_public = models.BooleanField(default=False)
    sites = models.ManyToManyField('wagtailcore.Site', related_name='library_assets')

    class Meta:
        ordering = ['is_archive', 'title']

    def __str__(self):
        return self.title
