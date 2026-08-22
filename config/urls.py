from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from django.views.generic import TemplateView

urlpatterns = [
    path("admin/", admin.site.urls),
    path(
        "",
        TemplateView.as_view(template_name="home.html"),
        name="home",
    ),
    path("accounts/", include("accounts.urls")),
    path(
        "dashboard/",
        include("dashboard.urls"),
    ),
    path(
        "providers/",
        include("providers.urls"),
    ),
    path(
        "services/",
        include("services.urls"),
    ),
    path(
        "bookings/",
        include("bookings.urls"),
    ),
    path(
        "payments/",
        include("payments.urls"),
    ),
    path("reviews/", include("reviews.urls")),
    path("notifications/", include("notifications.urls")),
    path("chat/", include("chat.urls")),
]

if settings.DEBUG:
    urlpatterns += static(
        settings.STATIC_URL,
        document_root=settings.STATICFILES_DIRS[0],
    )
    urlpatterns += static(
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT,
    )
