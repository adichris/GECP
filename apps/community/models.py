import uuid
from django.conf import settings
from django.db import models
from django.db.models import Q
from django.urls import reverse

VISIBILITY = [
    ("pending", "Awaiting review"),
    ("approved", "Published"),
    ("hidden", "Hidden"),
    ("withdrawn", "Withdrawn by author"),
]


class Contribution(models.Model):
    guest_key = models.CharField(max_length=64, blank=True, editable=False, db_index=True)
    guest_name = models.CharField(max_length=30, blank=True)
    guest_emoji = models.CharField(max_length=12, blank=True)

    class Meta:
        abstract = True

    @property
    def display_name(self):
        if self.author_id:
            return self.author.username
        return f"{self.guest_emoji} {self.guest_name} (Guest)"


class Thread(Contribution):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    site = models.ForeignKey("wagtailcore.Site", on_delete=models.CASCADE)
    author = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT)
    title = models.CharField(max_length=180)
    body = models.TextField(max_length=8000)
    category = models.CharField(
        max_length=20,
        choices=[
            ("discussion", "Discussion"),
            ("question", "Question"),
            ("issue", "Issue"),
            ("suggestion", "Suggestion"),
        ],
        default="discussion",
    )
    visibility = models.CharField(max_length=15, choices=VISIBILITY, default="pending")
    status = models.CharField(max_length=15, choices=[("open", "Open"), ("resolved", "Resolved")], default="open")
    locked = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["site", "visibility", "created_at"])]

    def get_absolute_url(self):
        return reverse("community:thread", args=[self.pk])

    def __str__(self):
        return self.title


class Comment(Contribution):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    site = models.ForeignKey("wagtailcore.Site", on_delete=models.CASCADE)
    author = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT)
    thread = models.ForeignKey(Thread, null=True, blank=True, on_delete=models.CASCADE, related_name="comments")
    blog = models.ForeignKey(
        "news.NewsPage", null=True, blank=True, on_delete=models.CASCADE, related_name="community_comments"
    )
    parent = models.ForeignKey("self", null=True, blank=True, on_delete=models.SET_NULL, related_name="replies")
    body = models.TextField(max_length=4000)
    visibility = models.CharField(max_length=15, choices=VISIBILITY, default="pending")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]
        constraints = [
            models.CheckConstraint(
                condition=(Q(thread__isnull=False, blog__isnull=True) | Q(thread__isnull=True, blog__isnull=False)),
                name="comment_exactly_one_target",
            )
        ]
        indexes = [models.Index(fields=["site", "visibility", "created_at"])]

    def __str__(self):
        return self.body[:70]


class Report(models.Model):
    site = models.ForeignKey("wagtailcore.Site", on_delete=models.CASCADE)
    reporter = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    thread = models.ForeignKey(Thread, null=True, blank=True, on_delete=models.CASCADE)
    comment = models.ForeignKey(Comment, null=True, blank=True, on_delete=models.CASCADE)
    reason = models.TextField(max_length=1500)
    status = models.CharField(max_length=12, choices=[("open", "Open"), ("reviewed", "Reviewed")], default="open")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=(
                    Q(thread__isnull=False, comment__isnull=True) | Q(thread__isnull=True, comment__isnull=False)
                ),
                name="report_exactly_one_target",
            ),
            models.UniqueConstraint(fields=["reporter", "thread"], name="one_report_per_thread"),
            models.UniqueConstraint(fields=["reporter", "comment"], name="one_report_per_comment"),
        ]


class ModerationLog(models.Model):
    site = models.ForeignKey("wagtailcore.Site", on_delete=models.CASCADE)
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL)
    target_type = models.CharField(max_length=30)
    target_id = models.CharField(max_length=50)
    action = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)


class RateLimit(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    key = models.CharField(max_length=64)
    bucket = models.BigIntegerField()
    count = models.PositiveIntegerField(default=0)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["key", "bucket"], name="unique_rate_bucket")]


class Bookmark(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    site = models.ForeignKey("wagtailcore.Site", on_delete=models.CASCADE)
    blog = models.ForeignKey("news.NewsPage", on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["user", "blog"], name="unique_blog_bookmark")]
