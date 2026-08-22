from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from .models import Notification
from .email_utils import build_absolute_url, send_transactional_email


@transaction.atomic
def create_notification(
    *,
    recipient,
    notification_type,
    title,
    message,
    link="",
):
    return Notification.objects.create(
        recipient=recipient,
        notification_type=notification_type,
        title=title,
        message=message,
        link=link,
    )


def get_unread_notification_count(*, user):
    return Notification.objects.filter(recipient=user, is_read=False).count()


def _booking_context(booking):
    customer_name = booking.customer.get_full_name() or booking.customer.username
    provider_name = booking.provider.business_name
    return {
        "booking": booking,
        "customer_name": customer_name,
        "provider_name": provider_name,
        "service_title": booking.service.title,
        "status_display": booking.get_status_display(),
        "booking_date": booking.booking_date,
        "start_time": booking.start_time,
        "end_time": booking.end_time,
        "booking_link": build_absolute_url(
            "bookings:detail",
            args=[booking.pk],
        ),
    }


def notify_booking_created(
    *,
    provider,
    booking,
):
    create_notification(
        recipient=provider.user,
        notification_type=Notification.NotificationType.BOOKING_CREATED,
        title="New Booking Request",
        message=(
            f"You received a new booking request for " f"{booking.service.title}."
        ),
        link="",
    )

    customer_context = _booking_context(booking)
    send_transactional_email(
        subject="Your Provia booking request was received",
        template_prefix="bookings/booking_created_customer",
        context=customer_context,
        to=booking.customer.email,
    )

    provider_context = _booking_context(booking)
    send_transactional_email(
        subject="New Provia booking request",
        template_prefix="bookings/booking_created_provider",
        context=provider_context,
        to=provider.user.email,
    )


def notify_booking_confirmed(
    *,
    customer,
    booking,
):
    create_notification(
        recipient=customer,
        notification_type=Notification.NotificationType.BOOKING_CONFIRMED,
        title="Booking Confirmed",
        message=(f"Your booking for {booking.service.title} " f"has been confirmed."),
        link="",
    )

    send_transactional_email(
        subject="Your Provia booking is confirmed",
        template_prefix="bookings/booking_confirmed",
        context=_booking_context(booking),
        to=customer.email,
    )


def notify_booking_cancelled(
    *,
    recipient,
    booking,
):
    create_notification(
        recipient=recipient,
        notification_type=Notification.NotificationType.BOOKING_CANCELLED,
        title="Booking Cancelled",
        message=(f"Your booking for {booking.service.title} " f"has been cancelled."),
        link="",
    )

    send_transactional_email(
        subject="Your Provia booking was cancelled",
        template_prefix="bookings/booking_cancelled",
        context=_booking_context(booking),
        to=recipient.email,
    )


def notify_booking_completed(
    *,
    customer,
    booking,
):
    create_notification(
        recipient=customer,
        notification_type=Notification.NotificationType.BOOKING_COMPLETED,
        title="Booking Completed",
        message=(f"Your booking for {booking.service.title} " f"has been completed."),
        link="",
    )

    context = _booking_context(booking)
    context["review_link"] = build_absolute_url(
        "reviews:create",
        args=[booking.pk],
    )
    send_transactional_email(
        subject="Your Provia service is complete",
        template_prefix="bookings/booking_completed",
        context=context,
        to=customer.email,
    )


def notify_payment_success(
    *,
    customer,
    payment,
):
    create_notification(
        recipient=customer,
        notification_type=Notification.NotificationType.PAYMENT_SUCCESS,
        title="Payment Successful",
        message=(
            f"Your payment for {payment.booking.service.title} "
            f"was completed successfully."
        ),
        link="",
    )

    send_transactional_email(
        subject="Your Provia payment was successful",
        template_prefix="payments/payment_success",
        context=_payment_context(payment),
        to=customer.email,
    )


def notify_payment_failed(
    *,
    customer,
    payment,
):
    create_notification(
        recipient=customer,
        notification_type=Notification.NotificationType.PAYMENT_FAILED,
        title="Payment Failed",
        message=(
            f"Your payment for {payment.booking.service.title} "
            f"could not be completed."
        ),
        link="",
    )

    send_transactional_email(
        subject="Action needed: Provia payment failed",
        template_prefix="payments/payment_failed",
        context=_payment_context(payment),
        to=customer.email,
    )


def notify_review_received(
    *,
    provider,
    review,
):
    create_notification(
        recipient=provider.user,
        notification_type=Notification.NotificationType.REVIEW_RECEIVED,
        title="New Review Received",
        message=(f"You received a new review for " f"{review.service.title}."),
        link="",
    )


def _payment_context(payment):
    booking = payment.booking
    customer_name = booking.customer.get_full_name() or booking.customer.username
    return {
        "payment": payment,
        "booking": booking,
        "customer_name": customer_name,
        "service_title": booking.service.title,
        "provider_name": booking.provider.business_name,
        "status_display": payment.get_status_display(),
        "amount": payment.amount,
        "currency": payment.currency,
        "payment_reference": payment.payment_reference,
        "payment_date": payment.updated_at,
        "booking_link": build_absolute_url(
            "bookings:detail",
            args=[booking.pk],
        ),
        "payment_link": build_absolute_url(
            "payments:detail",
            args=[payment.pk],
        ),
        "checkout_link": build_absolute_url(
            "payments:checkout",
            args=[booking.pk],
        ),
    }


@transaction.atomic
def mark_notification_as_read(
    *,
    notification,
    user,
):
    if notification.recipient != user:
        raise ValidationError("You do not have permission to mark this notification as read.")

    if notification.is_read:
        return notification

    notification.is_read = True
    notification.read_at = timezone.now()
    notification.save(update_fields=["is_read", "read_at"])
    return notification
