from django.contrib import admin
from django.urls import include, path

from core.views import health

urlpatterns = [
    path("healthz/", health, name="health"),
    path("admin/", admin.site.urls),
    path("accounts/", include("accounts.urls")),
    path("", include("tracker.urls")),
]
