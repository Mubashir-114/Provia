from django.urls import path

from . import views

app_name = "providers"

urlpatterns = [
    path(
        "profile/",
        views.profile_view,
        name="profile",
    ),
]