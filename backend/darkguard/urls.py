"""DarkGuard URL configuration."""

from django.urls import path, include

urlpatterns: list[object] = [
    path("api/", include("core.urls")),
    path("api/scans/", include("scans.urls")),
]
