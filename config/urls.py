from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from wagtail import urls as wagtail_urls
from wagtail.admin import urls as wagtailadmin_urls
from wagtail.documents import urls as wagtaildocs_urls
from wagtail.contrib.sitemaps.views import sitemap
from apps.core.views import health, search, explore, robots, directory, library, asset_detail, blog
from apps.engagement.views import contact, apply, intake

from django.contrib.auth import views as auth_views
from apps.community import views as community_views
from apps.news.feeds import BlogFeed
from apps.events.views import event_ics, site_calendar

urlpatterns = [
    path('community/', include('apps.community.urls')),
    path('accounts/register/', community_views.register, name='register'),
    path('accounts/login/', community_views.CommunityLoginView.as_view(), name='login'),
    path('accounts/logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('accounts/password-reset/', community_views.CommunityPasswordResetView.as_view(), name='password_reset'),
    path('accounts/password-reset/done/', auth_views.PasswordResetDoneView.as_view(template_name='registration/password_reset_done.html'), name='password_reset_done'),
    path('accounts/reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(template_name='registration/password_reset_confirm.html', success_url='/accounts/reset/done/'), name='password_reset_confirm'),
    path('accounts/reset/done/', auth_views.PasswordResetCompleteView.as_view(template_name='registration/password_reset_complete.html'), name='password_reset_complete'),
    path('accounts/password-change/', auth_views.PasswordChangeView.as_view(template_name='registration/password_change_form.html', success_url='/community/my-activity/'), name='password_change'),
    path('blog/feed/', BlogFeed(), name='blog_feed'),
    path('blog/', blog, name='blog'),
    path('events/calendar.ics', site_calendar, name='events_calendar'),
    path('events/<int:pk>/calendar.ics', event_ics, name='event_ics'),
    path('healthz/', health, name='health'),
    path('admin/', include(wagtailadmin_urls)),
    path('operations/', admin.site.urls),
    path('documents/', include(wagtaildocs_urls)),
    path('search/', search, name='search'),
    path('programmes/', directory, name='programmes'),
    path('library/', library, name='library'),
    path('library/<slug:slug>/', asset_detail, name='asset_detail'),
    path('explore/', explore, name='explore'),
    path('contact/', contact, name='contact'),
    path('participate/<slug:kind>/', intake, name='intake'),
    path('apply/<int:opportunity_id>/', apply, name='apply'),
    path('sitemap.xml', sitemap),
    path('robots.txt', robots),
]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
urlpatterns += [path('', include(wagtail_urls))]
