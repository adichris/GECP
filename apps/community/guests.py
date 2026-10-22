import secrets
from django.utils.crypto import salted_hmac

EMOJIS = ["🌱", "🌟", "🦋", "🌍", "🚀", "🎨", "🦉", "🐘", "🌻", "🐬", "💡", "📚"]


def suggestion():
    name = (
        secrets.choice(["Curious", "Kind", "Bright", "Creative", "Hopeful", "Friendly"])
        + secrets.choice(["Explorer", "Owl", "Learner", "Builder", "Dolphin", "Star"])
        + str(secrets.randbelow(900) + 100)
    )
    return {"guest_name": name, "guest_emoji": secrets.choice(EMOJIS)}


def owner_filter(request):
    if request.user.is_authenticated:
        return {"author": request.user}
    token = request.session.get("community_guest_token")
    if not token:
        return {"pk__in": []}
    return {"author__isnull": True, "guest_key": salted_hmac("community-guest", token).hexdigest()}


def author_fields(request, form):
    if request.user.is_authenticated:
        return {"author": request.user}
    token = request.session.get("community_guest_token")
    if not token:
        token = secrets.token_urlsafe(32)
        request.session["community_guest_token"] = token
    profile = {key: form.cleaned_data[key] for key in ("guest_name", "guest_emoji")}
    request.session["community_guest_profile"] = profile
    return {"author": None, "guest_key": salted_hmac("community-guest", token).hexdigest(), **profile}


def contribution_form(form_class, request):
    initial = request.session.get("community_guest_profile") or suggestion()
    return form_class(
        request.POST if request.method == "POST" else None, initial=initial, guest=not request.user.is_authenticated
    )
