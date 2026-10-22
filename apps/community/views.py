import secrets
import uuid
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView, PasswordResetView
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods, require_POST, require_GET
from apps.core.services import is_partial
from apps.news.models import NewsPage
from .models import Thread, Comment, Report, ModerationLog
from .forms import ThreadForm, CommentForm, ReportForm, RegistrationForm
from .security import rate_limit
from .guests import author_fields, owner_filter, contribution_form, suggestion


@method_decorator(rate_limit("login", limit=15), name="dispatch")
class CommunityLoginView(LoginView):
    template_name = "registration/login.html"


@method_decorator(rate_limit("password-reset", limit=4, seconds=3600), name="dispatch")
class CommunityPasswordResetView(PasswordResetView):
    template_name = "registration/password_reset_form.html"
    email_template_name = "registration/password_reset_email.txt"
    subject_template_name = "registration/password_reset_subject.txt"
    success_url = "/accounts/password-reset/done/"

    def form_valid(self, form):
        # Wagtail Site is the registered host; never use the global Django Sites fallback.
        opts = {
            "use_https": self.request.is_secure(),
            "domain_override": self.request.get_host(),
            "request": self.request,
            "email_template_name": self.email_template_name,
            "subject_template_name": self.subject_template_name,
        }
        form.save(**opts)
        return redirect(self.success_url)


@never_cache
@rate_limit("registration", limit=5, seconds=3600)
@require_http_methods(["GET", "POST"])
def register(request):
    if request.user.is_authenticated:
        return redirect("community:activity")
    form = RegistrationForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user, backend="django.contrib.auth.backends.ModelBackend")
        messages.success(request, "Your account is ready. New contributions are reviewed before publication.")
        return redirect("community:activity")
    return render(request, "registration/register.html", {"form": form, "title": "Join the community"})


@require_GET
def index(request):
    threads = Thread.objects.filter(site=request.site, visibility="approved")
    query = request.GET.get("q", "").strip()[:150]
    category = request.GET.get("category", "")
    status = request.GET.get("status", "")
    if query:
        threads = threads.filter(Q(title__icontains=query) | Q(body__icontains=query))
    if category:
        threads = threads.filter(category=category)
    if status:
        threads = threads.filter(status=status)
    return render(
        request,
        "community/index.html",
        {
            "threads": Paginator(threads.select_related("author"), 12).get_page(request.GET.get("page")),
            "query": query,
            "category": category,
            "status": status,
            "categories": Thread._meta.get_field("category").choices,
            "title": "Community & issues",
        },
    )


@require_GET
def guidelines(request):
    return render(request, "community/guidelines.html", {"title": "Community guidelines"})


@never_cache
@rate_limit("new-thread", limit=5, seconds=3600)
@require_http_methods(["GET", "POST"])
def new_thread(request):
    form = contribution_form(ThreadForm, request)
    if request.method == "POST" and form.is_valid():
        Thread.objects.create(
            site=request.site,
            **author_fields(request, form),
            **{key: form.cleaned_data[key] for key in ["title", "category", "body"]},
        )
        messages.success(request, "Your topic is awaiting review. You can track it in My activity.")
        return redirect("community:activity")
    return render(
        request,
        "community/form.html",
        {"form": form, "title": "Start a discussion or raise an issue", "button": "Submit for review"},
    )


def public_thread(request, pk):
    try:
        pk = uuid.UUID(str(pk))
    except ValueError:
        raise Http404
    return get_object_or_404(Thread, pk=pk, site=request.site, visibility="approved")


def public_blog(request, pk):
    try:
        pk = int(pk)
    except (ValueError, TypeError):
        raise Http404
    if pk < 1 or pk > 2147483647:
        raise Http404
    return get_object_or_404(
        NewsPage.objects.live().public().descendant_of(request.site.root_page), pk=pk, content_kind="blog"
    )


def conversation_context(request, kind, target):
    field = "blog" if kind == "blog" else "thread"
    qs = (
        Comment.objects.filter(site=request.site, visibility="approved", **{field: target})
        .filter(Q(parent__isnull=True) | Q(parent__visibility="approved"))
        .select_related("author", "parent__author")
        .order_by("-created_at")
    )
    return {
        "comments": Paginator(qs, 20).get_page(request.GET.get("comments_page")),
        "comment_target": target,
        "comment_kind": kind,
        "comments_locked": (getattr(target, "locked", False) or not getattr(target, "comments_enabled", True)),
    }


@never_cache
@require_GET
def thread_detail(request, pk):
    thread = public_thread(request, pk)
    return render(
        request,
        "community/thread.html",
        {
            "thread": thread,
            "is_owner": Thread.objects.filter(pk=thread.pk, **owner_filter(request)).exists(),
            "title": thread.title,
            **conversation_context(request, "thread", thread),
        },
    )


@never_cache
@rate_limit("comment", limit=15)
@require_http_methods(["GET", "POST"])
def add_comment(request, kind, pk):
    if kind not in ["blog", "thread"]:
        raise Http404
    target = public_blog(request, pk) if kind == "blog" else public_thread(request, pk)
    if getattr(target, "locked", False) or not getattr(target, "comments_enabled", True):
        return HttpResponse("This discussion is locked.", status=403)
    parent = None
    if request.GET.get("reply"):
        try:
            parent_id = uuid.UUID(request.GET["reply"])
        except ValueError:
            raise Http404
        parent = get_object_or_404(Comment, pk=parent_id, site=request.site, visibility="approved", **{kind: target})
        if parent.parent_id:
            parent = parent.parent
        if parent.visibility != "approved":
            raise Http404
    form = contribution_form(CommentForm, request)
    token_key = f"comment-token:{kind}:{target.pk}:{parent.pk if parent else 'root'}"
    if request.method == "GET":
        request.session[token_key] = str(uuid.uuid4())
    if request.method == "POST" and form.is_valid():
        token = request.POST.get("token", "")
        expected = request.session.get(token_key, "")
        if not expected or not secrets.compare_digest(token, expected):
            form.add_error(None, "This form expired or was already submitted. Reload to try again.")
        else:
            with transaction.atomic():
                # Lock the target so a simultaneous moderation lock is respected.
                locked = type(target).objects.select_for_update().get(pk=target.pk)
                if getattr(locked, "locked", False) or not getattr(locked, "comments_enabled", True):
                    return HttpResponse("This discussion is locked.", status=403)
                Comment.objects.get_or_create(
                    pk=uuid.UUID(token),
                    defaults={
                        "site": request.site,
                        **author_fields(request, form),
                        "body": form.cleaned_data["body"],
                        "parent": parent,
                        kind: target,
                    },
                )
            request.session.pop(token_key, None)
            messages.success(request, "Your comment is awaiting moderation. It is visible in My activity.")
            return redirect("community:activity")
    return render(
        request,
        "community/form.html",
        {
            "form": form,
            "title": "Reply to a contribution" if parent else "Join the conversation",
            "button": "Submit comment for review",
            "token": request.session.get(token_key, ""),
            "parent": parent,
        },
    )


@never_cache
@require_GET
def comments_feed(request, kind, pk):
    if kind not in ["blog", "thread"]:
        raise Http404
    target = public_blog(request, pk) if kind == "blog" else public_thread(request, pk)
    if not is_partial(request):
        return redirect(target.url if kind == "blog" else target.get_absolute_url())
    return render(request, "community/comments.html", conversation_context(request, kind, target))


@never_cache
@require_GET
def activity(request):
    return render(
        request,
        "community/activity.html",
        {
            "title": "My activity",
            "own_threads": Thread.objects.filter(site=request.site, **owner_filter(request)).order_by("-created_at")[
                :50
            ],
            "own_comments": Comment.objects.filter(site=request.site, **owner_filter(request)).order_by("-created_at")[
                :50
            ],
        },
    )


@never_cache
@login_required
@rate_limit("report", limit=8, seconds=3600)
@require_http_methods(["GET", "POST"])
def report(request, kind, pk):
    if kind == "thread":
        target = public_thread(request, pk)
    elif kind == "comment":
        target = get_object_or_404(Comment, pk=pk, site=request.site, visibility="approved")
        if target.thread_id:
            public_thread(request, target.thread_id)
        else:
            public_blog(request, target.blog_id)
        if target.parent_id and target.parent.visibility != "approved":
            raise Http404
    else:
        raise Http404
    form = ReportForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        Report.objects.get_or_create(
            reporter=request.user,
            **{kind: target},
            defaults={"site": request.site, "reason": form.cleaned_data["reason"]},
        )
        messages.success(request, "Your report has been sent to the site moderators.")
        return redirect("community:activity")
    return render(
        request, "community/form.html", {"form": form, "title": "Report a contribution", "button": "Send report"}
    )


@never_cache
@require_POST
def withdraw(request, kind, pk):
    model = {"thread": Thread, "comment": Comment}.get(kind)
    if model is None:
        raise Http404
    with transaction.atomic():
        obj = get_object_or_404(model.objects.select_for_update(), pk=pk, site=request.site, **owner_filter(request))
        obj.visibility = "withdrawn"
        obj.save(update_fields=["visibility"])
        ModerationLog.objects.create(
            site=request.site,
            actor=request.user if request.user.is_authenticated else None,
            target_type=kind,
            target_id=str(obj.pk),
            action="Author withdrew contribution",
        )
    messages.success(request, "Your contribution has been withdrawn from public view.")
    return redirect("community:activity")


@never_cache
@login_required
@require_POST
def bookmark(request, pk):
    from .models import Bookmark

    page = public_blog(request, pk)
    obj, created = Bookmark.objects.get_or_create(user=request.user, site=request.site, blog=page)
    if not created:
        obj.delete()
    messages.success(request, "Article saved." if created else "Article removed from saved articles.")
    return redirect("community:bookmarks")


@never_cache
@login_required
@require_GET
def bookmarks(request):
    from .models import Bookmark

    public = NewsPage.objects.live().public().descendant_of(request.site.root_page)
    saved = (
        Bookmark.objects.filter(user=request.user, site=request.site, blog__in=public)
        .select_related("blog")
        .order_by("-created_at")
    )
    return render(
        request,
        "community/bookmarks.html",
        {"title": "Saved articles", "saved": Paginator(saved, 20).get_page(request.GET.get("page"))},
    )


@never_cache
@login_required
@require_GET
def export_account(request):
    from django.http import JsonResponse

    data = {
        "username": request.user.username,
        "email": request.user.email,
        "scope": request.site.hostname,
        "topics": list(
            Thread.objects.filter(site=request.site, **owner_filter(request)).values(
                "title", "body", "visibility", "status", "created_at"
            )
        ),
        "comments": list(
            Comment.objects.filter(site=request.site, **owner_filter(request)).values(
                "body", "visibility", "created_at"
            )
        ),
    }
    response = JsonResponse(data)
    response["Content-Disposition"] = 'attachment; filename="gecp-community-data.json"'
    return response


@never_cache
@require_POST
def resolve(request, pk):
    with transaction.atomic():
        obj = get_object_or_404(
            Thread.objects.select_for_update(),
            pk=pk,
            site=request.site,
            **owner_filter(request),
            visibility="approved",
            locked=False,
        )
        status = request.POST.get("status")
        if status not in ["open", "resolved"]:
            return HttpResponse("Choose a valid status.", status=400)
        obj.status = status
        obj.save(update_fields=["status", "updated_at"])
        ModerationLog.objects.create(
            site=request.site,
            actor=request.user if request.user.is_authenticated else None,
            target_type="thread",
            target_id=str(obj.pk),
            action="Author marked " + status,
        )
    messages.success(request, "Topic status updated.")
    return redirect(obj.get_absolute_url())


@never_cache
@require_GET
def guest_suggestion(request):
    from django.http import JsonResponse

    return JsonResponse(suggestion())
