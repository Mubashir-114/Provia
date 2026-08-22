from django.urls import path

from . import views

app_name = "dashboard"


urlpatterns = [
    path(
        "customer/",
        views.customer_dashboard,
        name="customer",
    ),
    path(
        "provider/",
        views.provider_dashboard,
        name="provider",
    ),
]
