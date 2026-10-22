from django.contrib.syndication.views import Feed
from apps.core.services import network_context, public_pages
from .models import NewsPage


class BlogFeed(Feed):
    def get_object(self, request):
        return request

    def title(self, obj):
        return f"{obj.site.site_name} journal"

    def link(self, obj):
        return obj.site.root_url + "/blog/"

    def description(self, obj):
        return "Public articles from the GECP programme community."

    def items(self, obj):
        network = network_context(obj)
        return (
            public_pages(obj, NewsPage, across_network=network["current_programme"] is None)
            .filter(content_kind="blog")
            .order_by("-published_date", "-first_published_at")[:25]
        )

    def item_title(self, item):
        return item.title

    def item_description(self, item):
        return item.summary

    def item_link(self, item):
        return item.full_url
