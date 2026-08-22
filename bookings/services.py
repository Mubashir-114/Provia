from datetime import date, datetime, timedelta
from django.db import transaction
from django.core.exceptions import ValidationError
from django.db import transaction

from bookings.models import Booking
from services.models import ProviderAvailability
from notifications.services import (
    notify_booking_cancelled,
    notify_booking_completed,
    notify_booking_confirmed,
    notify_booking_created,
)


def get_available_slots(service, booking_date):
    """
    Return available booking slots for a service on a given date.

    A slot is available when:
    - the provider has active availability on that weekday
    - the slot fits completely inside the availability window
    - the slot does not overlap an existing pending/confirmed booking
    """

    weekday = booking_date.weekday()

    availability = ProviderAvailability.objects.filter(
        provider=service.provider,
        weekday=weekday,
        is_active=True,
    ).first()

    if availability is None:
        return []

    duration = timedelta(
        minutes=service.duration_minutes,
    )

    current = datetime.combine(
        booking_date,
        availability.start_time,
    )

    availability_end = datetime.combine(
        booking_date,
        availability.end_time,
    )

    bookings = Booking.objects.filter(
        provider=service.provider,
        booking_date=booking_date,
        status__in=[
            Booking.Status.PENDING,
            Booking.Status.CONFIRMED,
        ],
    )

    slots = []

    while current + duration <= availability_end:

        slot_start = current.time()
        slot_end = (current + duration).time()

        overlapping = bookings.filter(
            start_time__lt=slot_end,
            end_time__gt=slot_start,
        ).exists()

        if not overlapping:
            slots.append(
                {
                    "start_time": slot_start,
                    "end_time": slot_end,
                }
            )

        current += duration

    return slots


def create_booking(
    *,
    customer,
    service,
    booking_date,
    start_time,
    customer_notes="",
):
    """
    Validate and create a customer booking.

    The backend determines:
    - provider
    - end time
    - initial status (PENDING)
    """

    if booking_date <= date.today():
        raise ValidationError("Please select a future date.")

    if not service.is_published:
        raise ValidationError("This service is not currently available for booking.")

    if not service.category.is_active:
        raise ValidationError("This service category is not currently active.")

    if service.provider.user == customer:
        raise ValidationError("A provider cannot book their own service.")

    with transaction.atomic():
        # Lock provider's active bookings for this date to prevent concurrent double-bookings
        list(
            Booking.objects.filter(
                provider=service.provider,
                booking_date=booking_date,
                status__in=[
                    Booking.Status.PENDING,
                    Booking.Status.CONFIRMED,
                ],
            ).select_for_update()
        )

        slots = get_available_slots(
            service,
            booking_date,
        )

        selected_slot = next(
            (slot for slot in slots if slot["start_time"] == start_time),
            None,
        )

        if selected_slot is None:
            raise ValidationError(
                "The selected time slot is no longer available. Please choose another slot."
            )

        end_time = selected_slot["end_time"]

        booking = Booking(
            customer=customer,
            service=service,
            provider=service.provider,
            booking_date=booking_date,
            start_time=start_time,
            end_time=end_time,
            status=Booking.Status.PENDING,
            total_amount=service.price,
            customer_notes=customer_notes,
        )

        booking.full_clean()
        booking.save()
        transaction.on_commit(
            lambda: notify_booking_created(
                provider=booking.provider,
                booking=booking,
            )
        )

        return booking


def update_booking_status(
    *,
    booking,
    new_status,
    provider,
    provider_notes="",
):
    """
    Transition booking status according to the canonical state machine:
    - PENDING -> CONFIRMED
    - PENDING -> CANCELLED
    - CONFIRMED -> COMPLETED
    - CONFIRMED -> CANCELLED
    """

    if booking.provider != provider:
        raise ValidationError("You do not have permission to manage this booking.")

    allowed_transitions = {
        Booking.Status.PENDING: [
            Booking.Status.CONFIRMED,
            Booking.Status.CANCELLED,
        ],
        Booking.Status.CONFIRMED: [
            Booking.Status.COMPLETED,
            Booking.Status.CANCELLED,
        ],
    }

    current_allowed = allowed_transitions.get(booking.status, [])

    if new_status not in current_allowed:
        raise ValidationError(
            f"Cannot transition booking from {booking.get_status_display()} to {new_status}."
        )

    with transaction.atomic():
        booking.status = new_status

        if provider_notes:
            booking.provider_notes = provider_notes

        booking.full_clean()
        booking.save()

        if new_status == Booking.Status.CONFIRMED:
            transaction.on_commit(
                lambda: notify_booking_confirmed(
                    customer=booking.customer,
                    booking=booking,
                )
            )

        elif new_status == Booking.Status.CANCELLED:
            transaction.on_commit(
                lambda: notify_booking_cancelled(
                    recipient=booking.customer,
                    booking=booking,
                )
            )

        elif new_status == Booking.Status.COMPLETED:
            transaction.on_commit(
                lambda: notify_booking_completed(
                    customer=booking.customer,
                    booking=booking,
                )
            )
            from chat.services import create_system_message_for_booking_completion

            transaction.on_commit(
                lambda: create_system_message_for_booking_completion(
                    booking=booking,
                )
            )

        return booking

    if new_status == Booking.Status.CONFIRMED:
        transaction.on_commit(
            lambda: notify_booking_confirmed(
                customer=booking.customer,
                booking=booking,
            )
        )

    elif new_status == Booking.Status.CANCELLED:
        transaction.on_commit(
            lambda: notify_booking_cancelled(
                recipient=booking.customer,
                booking=booking,
            )
        )

    elif new_status == Booking.Status.COMPLETED:
        transaction.on_commit(
            lambda: notify_booking_completed(
                customer=booking.customer,
                booking=booking,
            )
        )

    return booking


def cancel_booking(
    *,
    booking,
    customer,
):
    """
    Allow a customer to cancel their own booking if status is PENDING or CONFIRMED.
    """

    if booking.customer != customer:
        raise ValidationError("You do not have permission to cancel this booking.")

    if booking.status not in [
        Booking.Status.PENDING,
        Booking.Status.CONFIRMED,
    ]:
        raise ValidationError(
            f"Bookings with status '{booking.get_status_display()}' cannot be cancelled."
        )

    with transaction.atomic():
        booking.status = Booking.Status.CANCELLED
        booking.full_clean()
        booking.save()

        transaction.on_commit(
            lambda: notify_booking_cancelled(
                recipient=booking.provider.user,
                booking=booking,
            )
        )

        return booking
