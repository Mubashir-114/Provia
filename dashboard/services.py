from decimal import Decimal

from django.db.models import Avg, Count, Q, Sum
from django.utils import timezone

from bookings.models import Booking
from chat.models import Conversation
from notifications.services import get_unread_notification_count
from payments.models import Payment
from providers.models import ProviderProfile
from reviews.models import Review
from services.models import Service


def get_customer_dashboard_data(*, user):
    customer = user

    bookings = Booking.objects.filter(
        customer=customer,
    )

    booking_counts = bookings.aggregate(
        total=Count("id"),
        pending=Count(
            "id",
            filter=Q(status=Booking.Status.PENDING),
        ),
        confirmed=Count(
            "id",
            filter=Q(status=Booking.Status.CONFIRMED),
        ),
        completed=Count(
            "id",
            filter=Q(status=Booking.Status.COMPLETED),
        ),
        cancelled=Count(
            "id",
            filter=Q(status=Booking.Status.CANCELLED),
        ),
    )

    now = timezone.localtime()
    today = now.date()
    current_time = now.time()

    upcoming_bookings = (
        bookings.filter(
            Q(booking_date__gt=today)
            | Q(
                booking_date=today,
                start_time__gte=current_time,
            )
        )
        .select_related(
            "service",
            "provider",
        )
        .order_by(
            "booking_date",
            "start_time",
        )[:5]
    )

    recent_bookings = bookings.select_related(
        "service",
        "provider",
    ).order_by(
        "-created_at",
    )[:5]

    recent_payments = (
        Payment.objects.filter(
            booking__customer=customer,
        )
        .select_related(
            "booking",
            "booking__service",
        )
        .order_by(
            "-created_at",
        )[:5]
    )

    payment_summary = Payment.objects.filter(
        booking__customer=customer,
    ).aggregate(
        total_payments=Count("id"),
        successful_payments=Count(
            "id",
            filter=Q(status=Payment.Status.SUCCESS),
        ),
        total_amount=Sum("amount"),
        successful_amount=Sum(
            "amount",
            filter=Q(status=Payment.Status.SUCCESS),
        ),
    )

    review_summary = Review.objects.filter(
        customer=customer,
    ).aggregate(
        review_count=Count("id"),
        average_rating=Avg("rating"),
    )

    unread_notification_count = get_unread_notification_count(
        user=customer,
    )

    # Phase 8: Recent Conversations / Messages
    recent_conv_qs = (
        Conversation.objects.filter(customer=customer)
        .select_related("booking", "booking__service", "provider", "provider__user")
        .prefetch_related("messages")
        .order_by("-updated_at")[:4]
    )
    recent_conversations = []
    for conv in recent_conv_qs:
        last_msg = conv.messages.order_by("-created_at").first()
        unread_cnt = conv.messages.filter(is_read=False).exclude(sender=customer).count()
        recent_conversations.append({
            "id": conv.id,
            "booking_id": conv.booking_id,
            "service_title": conv.booking.service.title,
            "other_name": conv.provider.business_name or conv.provider.user.username,
            "latest_message": last_msg,
            "unread_count": unread_cnt,
        })

    return {
        "booking_counts": booking_counts,
        "upcoming_bookings": upcoming_bookings,
        "recent_bookings": recent_bookings,
        "recent_payments": recent_payments,
        "payment_summary": payment_summary,
        "review_summary": review_summary,
        "unread_notification_count": unread_notification_count,
        "recent_conversations": recent_conversations,
    }


def get_provider_dashboard_data(*, user):
    provider = ProviderProfile.objects.get(user=user)

    now = timezone.localtime()
    today = now.date()
    current_time = now.time()

    services = Service.objects.filter(provider=provider)
    service_stats = services.aggregate(
        total=Count("id"),
        published=Count("id", filter=Q(is_published=True)),
        unpublished=Count("id", filter=Q(is_published=False)),
    )

    bookings = Booking.objects.filter(provider=provider)
    booking_stats = bookings.aggregate(
        total=Count("id"),
        pending=Count("id", filter=Q(status=Booking.Status.PENDING)),
        confirmed=Count("id", filter=Q(status=Booking.Status.CONFIRMED)),
        completed=Count("id", filter=Q(status=Booking.Status.COMPLETED)),
        cancelled=Count("id", filter=Q(status=Booking.Status.CANCELLED)),
    )

    upcoming_bookings = (
        bookings.filter(
            Q(booking_date__gt=today)
            | Q(
                booking_date=today,
                start_time__gte=current_time,
            )
        )
        .select_related("customer", "service")
        .order_by("booking_date", "start_time")[:5]
    )

    recent_bookings = (
        bookings.select_related("customer", "service")
        .order_by("-created_at")[:5]
    )

    payment_summary = Payment.objects.filter(
        booking__provider=provider,
    ).aggregate(
        total_payments=Count("id"),
        successful_payments=Count(
            "id",
            filter=Q(status=Payment.Status.SUCCESS),
        ),
        total_amount=Sum("amount"),
        revenue=Sum(
            "amount",
            filter=Q(status=Payment.Status.SUCCESS),
        ),
    )

    review_summary = Review.objects.filter(
        provider=provider,
    ).aggregate(
        review_count=Count("id"),
        average_rating=Avg("rating"),
    )

    unread_notification_count = get_unread_notification_count(user=user)

    # Phase 8: Recent Conversations / Messages
    recent_conv_qs = (
        Conversation.objects.filter(provider=provider)
        .select_related("booking", "booking__service", "customer")
        .prefetch_related("messages")
        .order_by("-updated_at")[:4]
    )
    recent_conversations = []
    for conv in recent_conv_qs:
        last_msg = conv.messages.order_by("-created_at").first()
        unread_cnt = conv.messages.filter(is_read=False).exclude(sender=user).count()
        recent_conversations.append({
            "id": conv.id,
            "booking_id": conv.booking_id,
            "service_title": conv.booking.service.title,
            "other_name": conv.customer.get_full_name() or conv.customer.username,
            "latest_message": last_msg,
            "unread_count": unread_cnt,
        })

    return {
        "provider": provider,
        "service_stats": service_stats,
        "booking_stats": booking_stats,
        "upcoming_bookings": upcoming_bookings,
        "recent_bookings": recent_bookings,
        "payment_summary": payment_summary,
        "review_summary": review_summary,
        "unread_notification_count": unread_notification_count,
        "recent_conversations": recent_conversations,
    }

