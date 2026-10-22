from django.urls import path
from . import views

app_name = "community"
urlpatterns = [
    path("guest-suggestion/", views.guest_suggestion, name="guest-suggestion"),
    path("status/<uuid:pk>/", views.resolve, name="resolve"),
    path("saved/", views.bookmarks, name="bookmarks"),
    path("save/<int:pk>/", views.bookmark, name="bookmark"),
    path("export/", views.export_account, name="export"),
    path("", views.index, name="index"),
    path("guidelines/", views.guidelines, name="guidelines"),
    path("new/", views.new_thread, name="new"),
    path("my-activity/", views.activity, name="activity"),
    path("topics/<uuid:pk>/", views.thread_detail, name="thread"),
    path("comment/<str:kind>/<str:pk>/", views.add_comment, name="comment"),
    path("comments/<str:kind>/<str:pk>/", views.comments_feed, name="comments"),
    path("report/<str:kind>/<uuid:pk>/", views.report, name="report"),
    path("withdraw/<str:kind>/<uuid:pk>/", views.withdraw, name="withdraw"),
]
