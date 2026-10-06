from django.conf import settings


class SecurityHeadersMiddleware:
    """Add the response headers listed in ``settings.SECURITY_HEADERS``.

    Django's own SecurityMiddleware covers HSTS, nosniff, referrer and COOP;
    this adds the rest (Content-Security-Policy, Permissions-Policy). A header
    already set by a view is left alone.
    """

    def __init__(self, get_response):
        self.get_response = get_response
        self.headers = getattr(settings, "SECURITY_HEADERS", {})

    def __call__(self, request):
        response = self.get_response(request)
        for name, value in self.headers.items():
            response.setdefault(name, value)
        return response
