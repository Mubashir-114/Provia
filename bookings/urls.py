from django.urls import path

from . import views

app_name = "bookings"


urlpatterns = [
    path(
        "my/",
        views.my_bookings,
        name="my_bookings",
    ),
    path(
        "service/<int:service_id>/book/",
        views.booking_create,
        name="create",
    ),
    path(
        "service/<int:service_id>/slots/",
        views.available_slots,
        name="available_slots",
    ),
    path(
        "<int:pk>/",
        views.booking_detail,
        name="detail",
    ),
    path(
        "<int:pk>/cancel/",
        views.booking_cancel,
        name="cancel",
    ),
    path(
        "<int:pk>/chat/",
        views.booking_chat,
        name="chat",
    ),
    path(
        "provider/",
        views.provider_bookings,
        name="provider_bookings",
    ),
    path(
        "provider/<int:pk>/",
        views.provider_booking_detail,
        name="provider_detail",
    ),
    path(
        "provider/<int:pk>/status/",
        views.provider_update_booking_status,
        name="update_status",
    ),
]
