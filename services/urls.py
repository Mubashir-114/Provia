from django.urls import path

from . import views

app_name = "services"


urlpatterns = [
    path(
        "",
        views.service_list,
        name="list",
    ),
    path(
        "create/",
        views.service_create,
        name="create",
    ),
    path(
        "<int:pk>/edit/",
        views.service_update,
        name="update",
    ),
    path(
        "<int:pk>/delete/",
        views.service_delete,
        name="delete",
    ),
    path(
        "<int:pk>/publish/",
        views.service_publish,
        name="publish",
    ),
    path(
        "<int:pk>/unpublish/",
        views.service_unpublish,
        name="unpublish",
    ),
    path(
        "availability/",
        views.availability_list,
        name="availability_list",
    ),
    path(
        "availability/create/",
        views.availability_create,
        name="availability_create",
    ),
    path(
        "availability/<int:pk>/edit/",
        views.availability_update,
        name="availability_update",
    ),
    path(
        "availability/<int:pk>/delete/",
        views.availability_delete,
        name="availability_delete",
    ),
    path(
        "discover/",
        views.public_service_list,
        name="public_list",
    ),
    path(
        "discover/<int:pk>/",
        views.public_service_detail,
        name="public_detail",
    ),
]
