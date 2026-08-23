from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from accounts.decorators import role_required
from accounts.models import User
from providers.models import ProviderProfile
from dashboard.services import (
    get_customer_dashboard_data,
    get_provider_dashboard_data,
)


@login_required
@role_required(User.Role.CUSTOMER)
def customer_dashboard(request):
    data = get_customer_dashboard_data(user=request.user)

    context = {
        "total_bookings": data["booking_counts"]["total"],
        "pending_bookings": data["booking_counts"]["pending"],
        "confirmed_bookings": data["booking_counts"]["confirmed"],
        "completed_bookings": data["booking_counts"]["completed"],
        "cancelled_bookings": data["booking_counts"]["cancelled"],
        "upcoming_bookings": data["upcoming_bookings"],
        "recent_bookings": data["recent_bookings"],
        "recent_payments": data["recent_payments"],
        "payment_summary": data["payment_summary"],
        "review_summary": data["review_summary"],
        "unread_notification_count": data["unread_notification_count"],
        "recent_conversations": data.get("recent_conversations", []),
    }

    return render(
        request,
        "dashboard/customer.html",
        context,
    )


@login_required
@role_required(User.Role.PROVIDER)
def provider_dashboard(request):
    if not ProviderProfile.objects.filter(user=request.user).exists():
        return redirect("providers:profile")

    data = get_provider_dashboard_data(user=request.user)

    context = {
        "provider": data["provider"],
        "total_services": data["service_stats"]["total"],
        "published_services": data["service_stats"]["published"],
        "unpublished_services": data["service_stats"]["unpublished"],
        "total_bookings": data["booking_stats"]["total"],
        "pending_bookings": data["booking_stats"]["pending"],
        "confirmed_bookings": data["booking_stats"]["confirmed"],
        "completed_bookings": data["booking_stats"]["completed"],
        "cancelled_bookings": data["booking_stats"]["cancelled"],
        "upcoming_bookings": data["upcoming_bookings"],
        "recent_bookings": data["recent_bookings"],
        "payment_summary": data["payment_summary"],
        "review_summary": data["review_summary"],
        "unread_notification_count": data["unread_notification_count"],
        "recent_conversations": data.get("recent_conversations", []),
    }

    return render(
        request,
        "dashboard/provider.html",
        context,
    )
