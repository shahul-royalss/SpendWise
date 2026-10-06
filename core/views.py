from django.contrib.auth import get_user_model
from django.db import DatabaseError
from django.http import JsonResponse
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET


@never_cache
@require_GET
def health(request):
    """Health check for hosting platforms.

    Runs a real query against a migrated table, so it also catches a database
    that exists but has no schema yet. Reveals nothing beyond up or down.
    """
    try:
        get_user_model().objects.exists()
    except DatabaseError:
        return JsonResponse({"status": "unavailable"}, status=503)
    return JsonResponse({"status": "ok"})
