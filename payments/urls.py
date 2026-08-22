from django.urls import path

from . import views

app_name = "payments"


urlpatterns = [
    path(
        "booking/<int:booking_id>/checkout/",
        views.checkout,
        name="checkout",
    ),
    path(
        "<int:payment_id>/initiate/",
        views.initiate,
        name="initiate",
    ),
    path(
        "<int:payment_id>/mock-success/",
        views.mock_success,
        name="mock_success",
    ),
    path(
        "<int:payment_id>/mock-failure/",
        views.mock_failure,
        name="mock_failure",
    ),
    path(
        "<int:payment_id>/cancel/",
        views.cancel,
        name="cancel",
    ),
    path(
        "<int:payment_id>/",
        views.detail,
        name="detail",
    ),
    path(
        "experience-v2/",
        views.experience_v2,
        name="experience_v2",
    ),
]

