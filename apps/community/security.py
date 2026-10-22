import time
import ipaddress
from django.conf import settings
from functools import wraps
from django.db.models import F
from django.http import HttpResponse
from django.utils.crypto import salted_hmac
from .models import RateLimit


def client_address(request):
    peer = request.META.get("REMOTE_ADDR", "unknown")
    if peer in settings.TRUSTED_PROXY_IPS:
        forwarded = request.META.get("HTTP_X_REAL_IP", "")
        try:
            return str(ipaddress.ip_address(forwarded))
        except ValueError:
            pass
    return peer


def rate_limit(action, limit=10, seconds=600):
    """Database-backed, shared between workers; never trust client-supplied proxy headers."""

    def decorate(view):
        @wraps(view)
        def wrapped(request, *args, **kwargs):
            if request.method == "POST":
                identity = (
                    f"user:{request.user.pk}" if request.user.is_authenticated else f"ip:{client_address(request)}"
                )
                key = salted_hmac("community-rate", f"{action}:{identity}").hexdigest()
                bucket = int(time.time()) // seconds
                row, _ = RateLimit.objects.get_or_create(key=key, bucket=bucket)
                changed = RateLimit.objects.filter(pk=row.pk, count__lt=limit).update(count=F("count") + 1)
                if not changed:
                    response = HttpResponse("Too many attempts. Please wait and try again.", status=429)
                    response["Retry-After"] = str(seconds)
                    return response
            return view(request, *args, **kwargs)

        return wrapped

    return decorate
