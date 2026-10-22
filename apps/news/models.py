from django.db import models
from django.utils import timezone
from wagtail.admin.panels import FieldPanel
from apps.core.models import SharedContentPage

class NewsPage(SharedContentPage):
    comments_enabled = models.BooleanField(default=True)
    content_kind = models.CharField(max_length=20, choices=[('insight', 'Programme insight'), ('blog', 'Blog post')], default='insight')
    topic = models.CharField(max_length=80, blank=True)
    template = 'core/content_detail.html'
    published_date = models.DateField(default=timezone.localdate)
    content_panels = SharedContentPage.content_panels + [FieldPanel('published_date'), FieldPanel('content_kind'), FieldPanel('topic'), FieldPanel('comments_enabled')]

    def get_context(self, request, *args, **kwargs):
        context = super().get_context(request, *args, **kwargs)
        from django.utils.html import strip_tags
        context['reading_minutes'] = max(1, (len(strip_tags(str(self.body)).split()) + 199) // 200)
        context['related_posts'] = NewsPage.objects.live().public().descendant_of(request.site.root_page).filter(content_kind='blog').exclude(pk=self.pk).order_by('-published_date', '-first_published_at')[:3]
        if self.content_kind == 'blog':
            from apps.community.views import conversation_context
            context.update(conversation_context(request, 'blog', self))
        return context
