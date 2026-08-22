from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .models import Notification
from .services import mark_notification_as_read


@login_required
def notification_list(request):
    notifications_list = Notification.objects.filter(
        recipient=request.user
    ).order_by("-created_at")

    paginator = Paginator(notifications_list, 10)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    context = {
        "page_obj": page_obj,
    }
    return render(request, "notifications/list.html", context)


@login_required
@require_POST
def mark_as_read(request, notification_id):
    notification = get_object_or_404(
        Notification,
        pk=notification_id,
        recipient=request.user,
    )
    try:
        mark_notification_as_read(notification=notification, user=request.user)
    except ValidationError:
        pass
    return redirect("notifications:list")


@login_required
@require_POST
def mark_all_as_read(request):
    notifications = Notification.objects.filter(
        recipient=request.user,
        is_read=False,
    )
    now = timezone.now()
    notifications.update(is_read=True, read_at=now)
    return redirect("notifications:list")

