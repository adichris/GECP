from functools import wraps
from django.contrib import messages
from django.contrib.auth.views import redirect_to_login
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET, require_http_methods, require_POST
from apps.community.security import rate_limit
from apps.core.services import network_context
from .forms import PortfolioItemForm, StaffProfileForm
from .models import PortfolioItem, StaffProfile


def staff_required(view):
    """Signed-in staff accounts only; other visitors get a clear explanation, not a bare 403."""
    @wraps(view)
    def wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect_to_login(request.get_full_path())
        if not (request.user.is_active and request.user.is_staff):
            return render(request, 'staff/not_staff.html', {'title': 'Staff portfolios'}, status=403)
        return view(request, *args, **kwargs)
    return wrapped


def visible_profiles(request):
    programme = network_context(request)['current_programme']
    return StaffProfile.objects.public().for_programme(programme)


@require_GET
def directory(request):
    network = network_context(request)
    profiles = visible_profiles(request)
    query = request.GET.get('q', '').strip()[:100]
    programme_code = request.GET.get('programme', '')[:50] if network['current_programme'] is None else ''
    if query:
        profiles = profiles.filter(Q(display_name__icontains=query) | Q(job_title__icontains=query) | Q(bio__icontains=query))
    if programme_code:
        profiles = profiles.filter(Q(programmes__code=programme_code) | Q(items__projects__initiative__programme__code=programme_code)).distinct()
    profiles = profiles.prefetch_related('programmes').annotate(
        work_count=Count('items', filter=Q(items__is_public=True, items__hidden_by_admin=False), distinct=True))
    return render(request, 'staff/directory.html', {
        'title': 'Our team', 'profiles': Paginator(profiles, 24).get_page(request.GET.get('page')),
        'query': query, 'programme_code': programme_code,
    })


def public_profile(request, slug):
    return get_object_or_404(visible_profiles(request).prefetch_related('programmes__site'), slug=slug)


@require_GET
def profile(request, slug):
    person = public_profile(request, slug)
    items = person.public_items()
    return render(request, 'staff/profile.html', {'title': person.display_name, 'person': person, 'items': items})


@require_GET
def item(request, slug, pk):
    person = public_profile(request, slug)
    work = get_object_or_404(person.public_items(), pk=pk)
    return render(request, 'staff/item.html', {'title': work.title, 'person': person, 'work': work})


@never_cache
@staff_required
@require_GET
def dashboard(request):
    person = StaffProfile.objects.filter(user=request.user).first()
    items = person.items.prefetch_related('projects__initiative__programme') if person else []
    return render(request, 'staff/dashboard.html', {'title': 'My portfolio', 'person': person, 'items': items})


@never_cache
@staff_required
@rate_limit('staff-portfolio', limit=60, seconds=3600)
@require_http_methods(['GET', 'POST'])
def edit_profile(request):
    person = StaffProfile.objects.filter(user=request.user).first()
    form = StaffProfileForm(request.POST or None, request.FILES or None, instance=person)
    if request.method == 'POST' and form.is_valid():
        obj = form.save(commit=False)
        if not person:
            obj.user = request.user
            obj.slug = StaffProfile.unique_slug(obj.display_name)
        obj.save()
        form.save_m2m()
        messages.success(request, 'Your profile has been saved.')
        return redirect('staff:dashboard')
    return render(request, 'staff/form.html', {
        'form': form, 'title': 'Edit my profile' if person else 'Create my staff profile',
        'button': 'Save profile', 'intro': 'Your profile is public unless you untick the directory option. Do not include private contact details.',
    })


def own_item(request, pk):
    return get_object_or_404(PortfolioItem, pk=pk, profile__user=request.user)


@never_cache
@staff_required
@rate_limit('staff-portfolio', limit=60, seconds=3600)
@require_http_methods(['GET', 'POST'])
def edit_item(request, pk=None):
    person = StaffProfile.objects.filter(user=request.user).first()
    if not person:
        messages.info(request, 'Create your profile first, then add your work.')
        return redirect('staff:edit_profile')
    work = own_item(request, pk) if pk else None
    form = PortfolioItemForm(request.POST or None, request.FILES or None, instance=work)
    if request.method == 'POST' and form.is_valid():
        obj = form.save(commit=False)
        obj.profile = person
        obj.save()
        form.save_m2m()
        messages.success(request, f'“{obj.title}” has been saved.')
        return redirect('staff:dashboard')
    return render(request, 'staff/form.html', {
        'form': form, 'title': 'Edit portfolio item' if work else 'Add to my portfolio', 'button': 'Save item',
        'intro': 'Share work you are proud of. Linking a GECP project is optional. Only share material you have permission to publish.',
    })


@staff_required
@require_POST
def delete_item(request, pk):
    work = own_item(request, pk)
    title = work.title
    work.delete()
    messages.success(request, f'“{title}” has been removed from your portfolio.')
    return redirect('staff:dashboard')
