"""
URL configuration for tms_project project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

import os

from approvals.views import approval_history, bulk_approve, unified_approvals
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.http import HttpResponse, JsonResponse
from django.urls import include, path
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.static import serve
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)


@ensure_csrf_cookie
def csrf_token_view(request):
    """Return CSRF token for Angular SPA"""
    return JsonResponse({"detail": "CSRF cookie set"})


def serve_spa(request, path=""):
    index_path = os.path.join(
        settings.BASE_DIR.parent,
        "frontend",
        "dist",
        "tms-frontend",
        "browser",
        "index.html",
    )
    try:
        with open(index_path, "rb") as f:
            return HttpResponse(f.read(), content_type="text/html")
    except FileNotFoundError:
        return HttpResponse(
            "Frontend not built. Run 'ng build' in the frontend/ directory.",
            status=503,
            content_type="text/plain",
        )


def security_txt(request):
    """Serve the security.txt file per RFC 9116"""
    security_txt_path = os.path.join(
        settings.BASE_DIR, "static", ".well-known", "security.txt"
    )
    try:
        with open(security_txt_path, "r") as f:
            content = f.read()
        return HttpResponse(content, content_type="text/plain")
    except FileNotFoundError:
        return HttpResponse("security.txt not found", status=404)


urlpatterns = [
    path("django-admin/", admin.site.urls),
    path("api/csrf/", csrf_token_view, name="csrf-token"),
    path("api/", include("accounts.urls")),
    path("api/trf/", include("trf.urls")),
    path("api/bookings/", include("bookings.urls")),
    path("api/insights/", include("insights.urls")),
    path("api/visa/", include("visa.urls")),
    path("api/accommodation/", include("accommodation.urls")),
    path("api/transport/", include("transport.urls")),
    path("api/workflows/", include("workflows.urls")),
    path("api/notifications/", include("notifications.urls")),
    path("api/reports/", include("reports.urls")),
    # Unified approvals endpoints
    path("api/admin/approvals/", unified_approvals, name="unified-approvals"),
    path("api/admin/approvals/bulk/", bulk_approve, name="bulk-approve"),
    path("api/admin/approvals/history/", approval_history, name="approval-history"),
    # Security.txt per RFC 9116
    path(".well-known/security.txt", security_txt, name="security-txt"),
    # API Documentation (drf-spectacular)
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "api/docs/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
    path("api/redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
]

# Serve media and static files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

# Catch-all: serve Angular SPA index.html for any non-API path
# WhiteNoise handles the actual JS/CSS/image asset files at root URL
urlpatterns += [
    path("", serve_spa, name="spa-root"),
    path("<path:path>", serve_spa, name="spa"),
]
