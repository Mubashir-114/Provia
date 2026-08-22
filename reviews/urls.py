from django.urls import path

from . import views

app_name = "reviews"

urlpatterns = [
    path(
        "booking/<int:booking_id>/create/",
        views.create_review_view,
        name="create",
    ),
    path(
        "booking/<int:booking_id>/",
        views.review_detail_view,
        name="detail",
    ),
    path(
        "booking/<int:booking_id>/edit/",
        views.update_review_view,
        name="edit",
    ),
    path(
        "booking/<int:booking_id>/delete/",
        views.delete_review_view,
        name="delete",
    ),
]
