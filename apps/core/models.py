from django.core.validators import RegexValidator
from django.db import models
from django.db.models import F
from modelcluster.fields import ParentalKey
from modelcluster.models import ClusterableModel
from wagtail.admin.panels import FieldPanel, InlinePanel, MultiFieldPanel
from wagtail.contrib.settings.models import BaseSiteSetting, register_setting
from wagtail.fields import RichTextField, StreamField
from .blocks import ProgrammeSection
from wagtail.models import Page, Orderable
from wagtail.search import index

THEMES = [(x, x.title()) for x in ['light', 'dark', 'corporate', 'emerald', 'forest', 'business', 'lofi']]

@register_setting
class SiteBranding(BaseSiteSetting, ClusterableModel):
    display_name = models.CharField(max_length=150, blank=True)
    tagline = models.CharField(max_length=200, blank=True)
    logo = models.ForeignKey('wagtailimages.Image', null=True, blank=True, on_delete=models.SET_NULL, related_name='+')
    primary_color = models.CharField(max_length=7, default='#116A53', validators=[RegexValidator(r'^#[0-9a-fA-F]{6}$', 'Use a six-digit hex colour.')])
    default_theme = models.CharField(max_length=20, choices=THEMES, default='light')
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=50, blank=True)
    address = models.TextField(blank=True)
    footer_text = models.CharField(max_length=250, default='Learning. Livelihoods. Lasting opportunity.')
    footer_description = models.TextField(blank=True)
    panels = [
        MultiFieldPanel([FieldPanel('display_name'), FieldPanel('tagline'), FieldPanel('logo'), FieldPanel('primary_color'), FieldPanel('default_theme')], heading='Brand'),
        MultiFieldPanel([FieldPanel('email'), FieldPanel('phone'), FieldPanel('address'), FieldPanel('footer_text'), FieldPanel('footer_description')], heading='Contact and footer'),
        InlinePanel('navigation_links', label='Navigation links'),
        InlinePanel('social_links', label='Social profiles'),
    ]

class NavigationLink(Orderable):
    branding = ParentalKey(SiteBranding, related_name='navigation_links', on_delete=models.CASCADE)
    label = models.CharField(max_length=80)
    page = models.ForeignKey(Page, null=True, blank=True, on_delete=models.CASCADE, related_name='+')
    external_url = models.URLField(blank=True)
    panels = [FieldPanel('label'), FieldPanel('page'), FieldPanel('external_url')]

    def clean(self):
        super().clean()
        from django.core.exceptions import ValidationError
        if bool(self.page_id) == bool(self.external_url):
            raise ValidationError('Choose exactly one page or external URL.')


class SocialLink(Orderable):
    branding = ParentalKey(SiteBranding, related_name='social_links', on_delete=models.CASCADE)
    label = models.CharField(max_length=50)
    url = models.URLField()
    panels = [FieldPanel('label'), FieldPanel('url')]

class HomePage(Page):
    programme_sections = StreamField([('section', ProgrammeSection())], blank=True)
    eyebrow = models.CharField(max_length=100, default='People. Possibility. Progress.')
    hero_title = models.CharField(max_length=200, default='Build skills. Open doors. Create change.')
    introduction = models.TextField(blank=True)
    body = RichTextField(blank=True)
    hero_image = models.ForeignKey('wagtailimages.Image', null=True, blank=True, on_delete=models.SET_NULL, related_name='+')
    hero_caption = models.CharField(max_length=240, blank=True)
    parent_page_types = ['wagtailcore.Page']
    subpage_types = ['core.StandardPage', 'news.NewsPage', 'events.EventPage', 'opportunities.OpportunityPage', 'resources.ResourcePage']
    content_panels = Page.content_panels + [FieldPanel('eyebrow'), FieldPanel('hero_title'), FieldPanel('introduction'), FieldPanel('body'), FieldPanel('hero_image'), FieldPanel('hero_caption'), FieldPanel('programme_sections')]
    search_fields = Page.search_fields + [index.SearchField('introduction'), index.SearchField('body'), index.SearchField('hero_title'), index.SearchField('programme_sections')]
    template = 'core/home.html'

    def get_context(self, request, *args, **kwargs):
        context = super().get_context(request, *args, **kwargs)
        from apps.news.models import NewsPage
        from apps.opportunities.models import OpportunityPage
        from apps.partners.models import Partner
        from apps.resources.models import LibraryAsset
        from apps.core.services import network_context, public_pages
        network = network_context(request)
        is_foundation = network['current_programme'] is None
        context['programmes'] = network['network_programmes']
        context['latest_blogs'] = public_pages(request, NewsPage, across_network=is_foundation).filter(content_kind='blog').order_by('-published_date', '-first_published_at')[:3]
        context['latest_news'] = public_pages(request, NewsPage, across_network=is_foundation).order_by('-published_date', '-first_published_at')[:3]
        context['opportunities'] = OpportunityPage.objects.live().public().descendant_of(self).open().order_by(F('deadline').asc(nulls_last=True), '-first_published_at')[:3]
        context['partners'] = Partner.objects.filter(sites=request.site).distinct()
        context['library_assets'] = LibraryAsset.objects.filter(is_public=True, sites__in=network['network_sites'] if is_foundation else [request.site]).select_related('image').distinct()[:4]
        context['initiatives'] = network['current_programme'].initiatives.prefetch_related('projects__activities').select_related('linked_site') if network['current_programme'] else []
        return context

class StandardPage(Page):
    body = RichTextField(blank=True)
    parent_page_types = ['core.HomePage', 'core.StandardPage']
    subpage_types = ['core.StandardPage']
    content_panels = Page.content_panels + [FieldPanel('body')]
    search_fields = Page.search_fields + [index.SearchField('body')]
    template = 'core/standard.html'

class SharedContentPage(Page):
    summary = models.TextField(max_length=500)
    body = RichTextField(blank=True)
    image = models.ForeignKey('wagtailimages.Image', null=True, blank=True, on_delete=models.SET_NULL, related_name='+')
    parent_page_types = ['core.HomePage']
    subpage_types = []
    content_panels = Page.content_panels + [FieldPanel('summary'), FieldPanel('body'), FieldPanel('image')]
    search_fields = Page.search_fields + [index.SearchField('summary'), index.SearchField('body')]
    template = 'core/content_detail.html'

    class Meta:
        abstract = True
