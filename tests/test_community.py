import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.contrib.admin.sites import AdminSite
from django.test import Client, RequestFactory
from django.core import mail
from django.urls import reverse
from wagtail.models import PageViewRestriction
from apps.programmes.models import Programme, ProgrammeMembership
from apps.news.models import NewsPage
from apps.community.models import Thread, Comment, Report, ModerationLog, Bookmark
from apps.community.admin import ThreadAdmin

pytestmark = pytest.mark.django_db
HOST = {"HTTP_HOST": "wwi.localhost:8000"}
OTHER = {"HTTP_HOST": "pec.localhost:8000"}


@pytest.fixture
def member(db):
    return get_user_model().objects.create_user(
        "member", email="member@example.org", password="Correct-Example-Password-429!"
    )


@pytest.fixture
def site(seeded):
    return Programme.objects.get(code="wwi").site


@pytest.fixture
def topic(site, member):
    return Thread.objects.create(
        site=site, author=member, title="Working together", body="A useful question", visibility="approved"
    )


@pytest.fixture
def article(site):
    return NewsPage.objects.live().descendant_of(site.root_page).filter(content_kind="blog").first()


def test_registration_login_logout_and_csrf(seeded):
    client = Client(enforce_csrf_checks=True)
    page = client.get("/accounts/register/", **HOST)
    assert page.status_code == 200
    data = {
        "username": "reader",
        "email": "reader@example.org",
        "password1": "Example-Unique-Password-387!",
        "password2": "Example-Unique-Password-387!",
        "consent": "on",
    }
    assert client.post("/accounts/register/", data, **HOST).status_code == 403
    data["csrfmiddlewaretoken"] = client.cookies["csrftoken"].value
    assert client.post("/accounts/register/", data, **HOST).status_code == 302
    user = get_user_model().objects.get(username="reader")
    assert not user.is_staff and not user.is_superuser
    assert client.get("/community/my-activity/", **HOST).status_code == 200
    assert client.get("/accounts/logout/", **HOST).status_code == 405
    assert (
        client.post("/accounts/logout/", {"csrfmiddlewaretoken": client.cookies["csrftoken"].value}, **HOST).status_code
        == 302
    )
    assert client.get("/community/my-activity/", **HOST).status_code == 200


def test_new_topic_pending_private_and_rate_limited(site, member, client):
    client.force_login(member)
    data = {"title": "New idea", "category": "issue", "body": "This needs review", "consent": "on"}
    assert client.post("/community/new/", data, **HOST).status_code == 302
    thread = Thread.objects.get()
    assert thread.visibility == "pending"
    assert client.get(thread.get_absolute_url(), **HOST).status_code == 404
    assert b"This needs review" in client.get("/community/my-activity/", **HOST).content
    client.logout()
    assert b"This needs review" not in client.get("/community/", **HOST).content
    client.force_login(member)
    for _ in range(4):
        client.post("/community/new/", data, **HOST)
    assert client.post("/community/new/", data, **HOST).status_code == 429


def test_comment_review_replay_and_xss(topic, member, client):
    client.force_login(member)
    url = reverse("community:comment", args=["thread", topic.pk])
    page = client.get(url, **HOST)
    data = {"body": "<script>alert(1)</script>", "consent": "on", "token": page.context["token"]}
    assert client.post(url, data, **HOST).status_code == 302
    assert client.post(url, data, **HOST).status_code == 200
    comment = Comment.objects.get()
    assert comment.visibility == "pending"
    comment.visibility = "approved"
    comment.save()
    response = client.get(topic.get_absolute_url(), **HOST)
    assert b"&lt;script&gt;alert(1)&lt;/script&gt;" in response.content
    assert b"<script>alert(1)</script>" not in response.content
    assert b"member@example.org" not in response.content


def test_comments_site_and_private_blog_protection(article, topic, member, client):
    client.force_login(member)
    assert client.get(reverse("community:comment", args=["thread", topic.pk]), **OTHER).status_code == 404
    url = reverse("community:comment", args=["blog", article.pk])
    assert client.get(url, **OTHER).status_code == 404
    assert client.get(url, **HOST).status_code == 200
    article.comments_enabled = False
    article.save()
    assert client.get(url, **HOST).status_code == 403
    article.comments_enabled = True
    article.save()
    PageViewRestriction.objects.create(page=article, restriction_type="login")
    assert client.get(url, **HOST).status_code == 404
    assert (
        client.get(reverse("community:comments", args=["blog", article.pk]), HTTP_HX_REQUEST="true", **HOST).status_code
        == 404
    )


def test_cross_target_reply_and_hidden_parent(topic, article, member, client):
    client.force_login(member)
    parent = Comment.objects.create(
        site=topic.site, author=member, blog=article, body="Different article", visibility="approved"
    )
    path = reverse("community:comment", args=["thread", topic.pk]) + f"?reply={parent.pk}"
    assert client.get(path, **HOST).status_code == 404
    parent = Comment.objects.create(site=topic.site, author=member, thread=topic, body="Parent", visibility="approved")
    child = Comment.objects.create(
        site=topic.site, author=member, thread=topic, parent=parent, body="Child text", visibility="approved"
    )
    parent.visibility = "withdrawn"
    parent.save()
    assert child.body.encode() not in client.get(topic.get_absolute_url(), **HOST).content


def test_locked_topic_rejects_posts(topic, member, client):
    client.force_login(member)
    path = reverse("community:comment", args=["thread", topic.pk])
    token = client.get(path, **HOST).context["token"]
    topic.locked = True
    topic.save()
    assert client.post(path, {"body": "No", "consent": "on", "token": token}, **HOST).status_code == 403
    assert not Comment.objects.exists()


def test_reports_deduplicate_and_are_not_public(topic, member, client):
    client.force_login(member)
    url = reverse("community:report", args=["thread", topic.pk])
    for _ in range(2):
        assert client.post(url, {"reason": "Private moderation detail"}, **HOST).status_code == 302
    assert Report.objects.count() == 1
    assert b"Private moderation detail" not in client.get(topic.get_absolute_url(), **HOST).content
    assert client.post(url, {"reason": "Wrong site"}, **OTHER).status_code == 404


def test_withdraw_is_owner_only_post_only(topic, member, client):
    url = reverse("community:withdraw", args=["thread", topic.pk])
    stranger = get_user_model().objects.create_user("stranger")
    client.force_login(stranger)
    assert client.post(url, **HOST).status_code == 404
    client.force_login(member)
    assert client.get(url, **HOST).status_code == 405
    assert client.post(url, **HOST).status_code == 302
    topic.refresh_from_db()
    assert topic.visibility == "withdrawn"
    assert client.get(topic.get_absolute_url(), **HOST).status_code == 404
    assert ModerationLog.objects.count() == 1


def test_moderators_scoped_and_audited(topic, member):
    member.is_staff = True
    member.save()
    programme = Programme.objects.get(code="wwi")
    ProgrammeMembership.objects.create(user=member, programme=programme)
    member.groups.add(Group.objects.get(name="WWI editors"))
    request = RequestFactory().get("/operations/")
    request.user = member
    admin = ThreadAdmin(Thread, AdminSite())
    foreign = Thread.objects.create(
        site=Programme.objects.get(code="pec").site, author=member, title="Foreign", body="Not ours"
    )
    assert not admin.has_change_permission(request, foreign)
    admin.hide(request, Thread.objects.all())
    topic.refresh_from_db()
    foreign.refresh_from_db()
    assert topic.visibility == "hidden" and foreign.visibility == "pending"
    assert ModerationLog.objects.get().site == topic.site


def test_bookmarks_export_and_feed(article, member, client):
    client.force_login(member)
    url = reverse("community:bookmark", args=[article.pk])
    assert client.post(url, **HOST).status_code == 302
    assert Bookmark.objects.count() == 1
    assert article.title.encode() in client.get("/community/saved/", **HOST).content
    assert client.get("/community/export/", **HOST).json()["email"] == member.email
    assert client.post(url, **OTHER).status_code == 404
    article.unpublish()
    assert article.title.encode() not in client.get("/community/saved/", **HOST).content
    assert article.title.encode() not in client.get("/blog/feed/", **HOST).content
    assert client.get("/blog/feed/", **HOST).status_code == 200


def test_password_recovery_uses_current_site(seeded, member, client):
    assert client.post("/accounts/password-reset/", {"email": member.email}, **HOST).status_code == 302
    assert len(mail.outbox) == 1
    assert "http://wwi.localhost:8000/accounts/reset/" in mail.outbox[0].body
    assert member.email not in client.get("/accounts/password-reset/done/", **HOST).content.decode()


def test_signed_in_users_cannot_cycle_registration(seeded, member, client):
    client.force_login(member)
    before = get_user_model().objects.count()
    response = client.post("/accounts/register/", {"username": "another"}, **HOST)
    assert response.status_code == 302
    assert get_user_model().objects.count() == before


@pytest.mark.parametrize(
    "path",
    [
        "/community/",
        "/community/guidelines/",
        "/accounts/login/",
        "/accounts/register/",
        "/accounts/password-reset/",
        "/accounts/password-reset/done/",
        "/accounts/reset/done/",
        "/blog/feed/",
    ],
)
def test_public_community_routes(seeded, client, path):
    assert client.get(path, **HOST).status_code == 200


def test_invalid_targets_are_404(seeded, member, client):
    client.force_login(member)
    for path in [
        "/community/comment/blog/not-a-number/",
        "/community/comment/blog/99999999999999999999999/",
        "/community/comment/thread/not-a-uuid/",
    ]:
        assert client.get(path, **HOST).status_code == 404


def test_topic_author_can_resolve_but_not_locked_topic(topic, member, client):
    client.force_login(member)
    url = reverse("community:resolve", args=[topic.pk])
    assert client.post(url, {"status": "resolved"}, **HOST).status_code == 302
    topic.refresh_from_db()
    assert topic.status == "resolved"
    topic.locked = True
    topic.save()
    assert client.post(url, {"status": "open"}, **HOST).status_code == 404


def test_proxy_address_is_only_used_for_explicit_trusted_peer(settings):
    from apps.community.security import client_address

    request = RequestFactory().get("/", REMOTE_ADDR="10.0.0.2", HTTP_X_REAL_IP="198.51.100.10")
    settings.TRUSTED_PROXY_IPS = []
    assert client_address(request) == "10.0.0.2"
    settings.TRUSTED_PROXY_IPS = ["10.0.0.2"]
    assert client_address(request) == "198.51.100.10"
    request.META["HTTP_X_REAL_IP"] = "spoofed"
    assert client_address(request) == "10.0.0.2"


def test_throttle_authentication_and_honeypot(seeded, client):
    for _ in range(15):
        assert client.post("/accounts/login/", {"username": "missing", "password": "wrong"}, **HOST).status_code == 200
    assert client.post("/accounts/login/", {"username": "missing", "password": "wrong"}, **HOST).status_code == 429
    data = {
        "username": "trap",
        "email": "trap@example.org",
        "password1": "Example-Unique-Password-387!",
        "password2": "Example-Unique-Password-387!",
        "consent": "on",
        "website": "bot",
    }
    assert client.post("/accounts/register/", data, **HOST).status_code == 200
    assert not get_user_model().objects.filter(username="trap").exists()


def test_guest_identity_ownership_and_moderation(client, site):
    from apps.community.guests import EMOJIS

    suggestion = client.get("/community/guest-suggestion/", **HOST).json()
    assert suggestion["guest_emoji"] in EMOJIS
    data = {
        **suggestion,
        "title": "Guest question",
        "body": "A guest contribution",
        "category": "question",
        "consent": "on",
    }
    assert client.get("/community/new/", **HOST).status_code == 200
    assert client.post("/community/new/", data, **HOST).status_code == 302
    topic = Thread.objects.get(title="Guest question")
    assert topic.author_id is None and topic.visibility == "pending" and topic.guest_key
    assert "Guest question" in client.get("/community/my-activity/", **HOST).content.decode()
    stranger = Client()
    assert "Guest question" not in stranger.get("/community/my-activity/", **HOST).content.decode()
    assert stranger.post(f"/community/withdraw/thread/{topic.pk}/", **HOST).status_code == 404
    assert client.get(topic.get_absolute_url(), **HOST).status_code == 404
    topic.visibility = "approved"
    topic.save()
    page = client.get(topic.get_absolute_url(), **HOST).content.decode()
    assert "(Guest)" in page and topic.guest_key not in page
    assert client.post(f"/community/status/{topic.pk}/", {"status": "resolved"}, **HOST).status_code == 302
    assert client.post(f"/community/withdraw/thread/{topic.pk}/", **OTHER).status_code == 404
    assert client.post(f"/community/withdraw/thread/{topic.pk}/", **HOST).status_code == 302


def test_guest_comments_validation_replay_and_limits(client, topic):
    from apps.community.guests import EMOJIS

    url = f"/community/comment/thread/{topic.pk}/"
    page = client.get(url, **HOST)
    token = page.context["token"]
    data = {
        "guest_name": "Visitor",
        "guest_emoji": EMOJIS[0],
        "body": "Hello from a guest",
        "consent": "on",
        "token": token,
    }
    assert client.post(url, {**data, "guest_name": "<script>"}, **HOST).status_code == 200
    assert not Comment.objects.filter(thread=topic).exists()
    assert client.post(url, {**data, "guest_emoji": "invalid"}, **HOST).status_code == 200
    assert client.post(url, data, **HOST).status_code == 302
    assert client.post(url, data, **HOST).status_code == 200
    comment = Comment.objects.get(thread=topic)
    assert comment.visibility == "pending" and comment.author_id is None
    assert client.get(url, **HOST).context["form"].initial["guest_name"] == "Visitor"
    assert Client().post(f"/community/withdraw/comment/{comment.pk}/", **HOST).status_code == 404
    for _ in range(11):
        client.post(url, data, **HOST)
    assert Client().post(url, data, **HOST).status_code == 429


def test_guest_csrf_and_registered_author(client, site, member):
    strict = Client(enforce_csrf_checks=True)
    assert strict.post("/community/new/", {}, **HOST).status_code == 403
    client.force_login(member)
    page = client.get("/community/new/", **HOST)
    assert "guest_name" not in page.context["form"].fields
    assert (
        client.post(
            "/community/new/",
            {
                "title": "Member topic",
                "category": "discussion",
                "body": "Hello",
                "consent": "on",
                "guest_name": "Spoof",
            },
            **HOST,
        ).status_code
        == 302
    )
    topic = Thread.objects.get(title="Member topic")
    assert topic.author == member and topic.guest_key == ""
