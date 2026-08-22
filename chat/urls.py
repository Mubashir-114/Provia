from django.urls import path

from . import views

app_name = "chat"


urlpatterns = [
    path(
        "",
        views.conversation_list,
        name="list",
    ),
    path(
        "<int:conversation_id>/",
        views.conversation_detail,
        name="conversation",
    ),
]
