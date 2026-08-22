from uuid import uuid4

from django.core.exceptions import ValidationError
from django.db import transaction

from bookings.models import Booking
from bookings.services import update_booking_status

from .models import Payment
from notifications.services import (
    notify_payment_failed,
    notify_payment_success,
)


def get_payment_for_booking(*, booking):
    """
    Return the payment associated with a booking.

    Raises Payment.DoesNotExist when no payment exists.
    """
    return Payment.objects.get(booking=booking)


def create_payment(*, booking, customer):
    """
    Create a pending payment for a customer's own eligible booking.

    The payment amount is always taken from booking.total_amount.
    The client never supplies the payment amount.
    """

    with transaction.atomic():
        locked_booking = (
            Booking.objects.select_for_update()
            .select_related("service", "provider")
            .get(pk=booking.pk)
        )

        if locked_booking.customer_id != customer.id:
            raise ValidationError(
                "You do not have permission to create a payment for this booking."
            )

        if locked_booking.status == Booking.Status.CANCELLED:
            raise ValidationError("A cancelled booking cannot be paid for.")

        if locked_booking.status != Booking.Status.PENDING:
            raise ValidationError("Only pending bookings are eligible for payment.")

        try:
            payment = Payment.objects.select_for_update().get(booking=locked_booking)
        except Payment.DoesNotExist:
            payment = Payment(
                booking=locked_booking,
                amount=locked_booking.total_amount,
                currency="INR",
                status=Payment.Status.PENDING,
            )

            payment.full_clean()
            payment.save()

        else:
            if payment.status == Payment.Status.SUCCESS:
                raise ValidationError("This booking has already been paid.")

            if payment.status == Payment.Status.INITIATED:
                return payment

            if payment.status == Payment.Status.CANCELLED:
                raise ValidationError("This payment has been cancelled.")

            if payment.amount != locked_booking.total_amount:
                raise ValidationError(
                    "Payment amount does not match the booking amount."
                )

        return payment


def initiate_payment(*, payment, customer):
    """
    Move a customer's payment from PENDING to INITIATED.

    A unique payment reference is generated server-side.
    """

    with transaction.atomic():
        locked_payment = (
            Payment.objects.select_for_update()
            .select_related("booking")
            .get(pk=payment.pk)
        )

        booking = Booking.objects.select_for_update().get(pk=locked_payment.booking_id)

        if booking.customer_id != customer.id:
            raise ValidationError(
                "You do not have permission to initiate this payment."
            )

        if booking.status == Booking.Status.CANCELLED:
            raise ValidationError("A cancelled booking cannot be paid for.")

        if locked_payment.status == Payment.Status.SUCCESS:
            return locked_payment

        if locked_payment.status == Payment.Status.INITIATED:
            return locked_payment

        if locked_payment.status not in [
            Payment.Status.PENDING,
            Payment.Status.FAILED,
        ]:
            raise ValidationError(
                f"Payment cannot be initiated from "
                f"{locked_payment.get_status_display()} status."
            )

        if locked_payment.amount != booking.total_amount:
            raise ValidationError("Payment amount does not match the booking amount.")

        locked_payment.status = Payment.Status.INITIATED
        locked_payment.payment_reference = f"PRV-{uuid4().hex.upper()}"

        locked_payment.full_clean()
        locked_payment.save(
            update_fields=[
                "status",
                "payment_reference",
                "updated_at",
            ]
        )

        return locked_payment


def mark_payment_success(*, payment, customer):
    """
    Mark a payment as successful and confirm its booking.

    The booking is confirmed through the canonical booking service.
    """

    with transaction.atomic():
        locked_payment = (
            Payment.objects.select_for_update()
            .select_related("booking", "booking__provider")
            .get(pk=payment.pk)
        )

        booking = Booking.objects.select_for_update().get(pk=locked_payment.booking_id)

        if booking.customer_id != customer.id:
            raise ValidationError(
                "You do not have permission to complete this payment."
            )

        if locked_payment.status == Payment.Status.SUCCESS:
            return locked_payment

        if locked_payment.status != Payment.Status.INITIATED:
            raise ValidationError(
                "Only initiated payments can be marked as successful."
            )

        if booking.status != Booking.Status.PENDING:
            raise ValidationError(
                "The booking is no longer eligible for payment confirmation."
            )

        if locked_payment.amount != booking.total_amount:
            raise ValidationError("Payment amount does not match the booking amount.")

        locked_payment.status = Payment.Status.SUCCESS

        locked_payment.full_clean()
        locked_payment.save(
            update_fields=[
                "status",
                "updated_at",
            ]
        )

        update_booking_status(
            booking=booking,
            new_status=Booking.Status.CONFIRMED,
            provider=booking.provider,
        )

        transaction.on_commit(
            lambda: notify_payment_success(
                customer=booking.customer,
                payment=locked_payment,
            )
        )

        return locked_payment


def mark_payment_failed(*, payment, customer):
    """
    Mark an initiated payment as failed.
    """

    with transaction.atomic():
        locked_payment = (
            Payment.objects.select_for_update()
            .select_related("booking")
            .get(pk=payment.pk)
        )

        booking = Booking.objects.select_for_update().get(pk=locked_payment.booking_id)

        if booking.customer_id != customer.id:
            raise ValidationError("You do not have permission to update this payment.")

        if locked_payment.status == Payment.Status.FAILED:
            return locked_payment

        if locked_payment.status != Payment.Status.INITIATED:
            raise ValidationError("Only initiated payments can be marked as failed.")

        locked_payment.status = Payment.Status.FAILED

        locked_payment.full_clean()
        locked_payment.save(
            update_fields=[
                "status",
                "updated_at",
            ]
        )

        transaction.on_commit(
            lambda: notify_payment_failed(
                customer=booking.customer,
                payment=locked_payment,
            )
        )

        return locked_payment


def cancel_payment(*, payment, customer):
    """
    Cancel a pending or initiated payment.

    A successful payment can never be cancelled through this service.
    """

    with transaction.atomic():
        locked_payment = (
            Payment.objects.select_for_update()
            .select_related("booking")
            .get(pk=payment.pk)
        )

        booking = Booking.objects.select_for_update().get(pk=locked_payment.booking_id)

        if booking.customer_id != customer.id:
            raise ValidationError("You do not have permission to cancel this payment.")

        if locked_payment.status == Payment.Status.CANCELLED:
            return locked_payment

        if locked_payment.status == Payment.Status.SUCCESS:
            raise ValidationError("A successful payment cannot be cancelled.")

        if locked_payment.status not in [
            Payment.Status.PENDING,
            Payment.Status.INITIATED,
        ]:
            raise ValidationError(
                f"Payment cannot be cancelled from "
                f"{locked_payment.get_status_display()} status."
            )

        locked_payment.status = Payment.Status.CANCELLED

        locked_payment.full_clean()
        locked_payment.save(
            update_fields=[
                "status",
                "updated_at",
            ]
        )

        return locked_payment
