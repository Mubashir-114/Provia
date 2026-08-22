from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from bookings.models import Booking

from .models import Payment
from .services import (
    cancel_payment,
    create_payment,
    initiate_payment,
    mark_payment_failed,
    mark_payment_success,
)


@login_required
def checkout(request, booking_id):
    """
    Display the payment checkout page for the authenticated customer's booking.
    """

    booking = get_object_or_404(
        Booking.objects.select_related(
            "service",
            "service__category",
            "provider",
        ),
        pk=booking_id,
        customer=request.user,
    )

    try:
        payment = create_payment(
            booking=booking,
            customer=request.user,
        )
    except ValidationError as exc:
        messages.error(request, exc.messages[0])
        return redirect("bookings:detail", pk=booking.pk)

    return render(
        request,
        "payments/checkout.html",
        {
            "booking": booking,
            "payment": payment,
        },
    )


@login_required
@require_POST
def initiate(request, payment_id):
    """
    Initiate a customer's payment.
    """

    payment = get_object_or_404(
        Payment.objects.select_related("booking"),
        pk=payment_id,
        booking__customer=request.user,
    )

    try:
        payment = initiate_payment(
            payment=payment,
            customer=request.user,
        )
    except ValidationError as exc:
        messages.error(request, exc.messages[0])
        return redirect(
            "payments:checkout",
            booking_id=payment.booking_id,
        )

    return render(
        request,
        "payments/mock_payment.html",
        {
            "payment": payment,
            "booking": payment.booking,
        },
    )


@login_required
@require_POST
def mock_success(request, payment_id):
    """
    Simulate a successful payment for development/testing.
    """

    payment = get_object_or_404(
        Payment.objects.select_related("booking"),
        pk=payment_id,
        booking__customer=request.user,
    )

    try:
        payment = mark_payment_success(
            payment=payment,
            customer=request.user,
        )
    except ValidationError as exc:
        messages.error(request, exc.messages[0])
        return redirect(
            "payments:checkout",
            booking_id=payment.booking_id,
        )

    messages.success(
        request,
        "Payment completed successfully.",
    )

    return redirect(
        "payments:detail",
        payment_id=payment.pk,
    )


@login_required
@require_POST
def mock_failure(request, payment_id):
    """
    Simulate a failed payment for development/testing.
    """

    payment = get_object_or_404(
        Payment.objects.select_related("booking"),
        pk=payment_id,
        booking__customer=request.user,
    )

    try:
        payment = mark_payment_failed(
            payment=payment,
            customer=request.user,
        )
    except ValidationError as exc:
        messages.error(request, exc.messages[0])
        return redirect(
            "payments:checkout",
            booking_id=payment.booking_id,
        )

    messages.error(
        request,
        "Payment failed. Your booking remains pending.",
    )

    return redirect(
        "payments:detail",
        payment_id=payment.pk,
    )


@login_required
def detail(request, payment_id):
    """
    Display payment information for the authenticated customer's payment.
    """

    payment = get_object_or_404(
        Payment.objects.select_related(
            "booking",
            "booking__service",
            "booking__service__category",
        ),
        pk=payment_id,
        booking__customer=request.user,
    )

    return render(
        request,
        "payments/detail.html",
        {
            "payment": payment,
            "booking": payment.booking,
        },
    )


@login_required
@require_POST
def cancel(request, payment_id):
    """
    Cancel a pending or initiated payment.
    """

    payment = get_object_or_404(
        Payment.objects.select_related("booking"),
        pk=payment_id,
        booking__customer=request.user,
    )

    try:
        cancel_payment(
            payment=payment,
            customer=request.user,
        )
    except ValidationError as exc:
        messages.error(request, exc.messages[0])
        return redirect(
            "payments:detail",
            payment_id=payment.pk,
        )

    messages.success(
        request,
        "Payment cancelled.",
    )

    return redirect(
        "bookings:detail",
        pk=payment.booking_id,
    )


def experience_v2(request):
    """
    Renders the complete Provia Payment Experience V2 showcasing all 10 screens
    in sequence with desktop/mobile viewport toggles and live interactive states.
    """
    return render(request, "payments/experience_v2.html")

