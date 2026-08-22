from .services import get_unread_notification_count


def unread_notification_count(request):
    if not getattr(request.user, "is_authenticated", False):
        return {"unread_notification_count": 0}

    return {
        "unread_notification_count": get_unread_notification_count(user=request.user),
    }
