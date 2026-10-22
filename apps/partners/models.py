from django.db import models

class Partner(models.Model):
    name = models.CharField(max_length=160)
    website = models.URLField(blank=True)
    logo = models.ForeignKey('wagtailimages.Image', null=True, blank=True, on_delete=models.SET_NULL, related_name='+')
    sites = models.ManyToManyField('wagtailcore.Site', related_name='partners')
    def __str__(self):
        return self.name
