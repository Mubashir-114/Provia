from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Avg, Count
from .models import Review
from notifications.services import notify_review_received


def _validate_completed_booking(booking, customer):
    if booking.customer_id != customer.id:
        raise ValidationError("You are not allowed to review this booking.")

    if booking.status != "completed":
        raise ValidationError("Only completed bookings can be reviewed.")


@transaction.atomic
def create_review(*, booking, customer, rating, comment):
    """
    Create a review for a completed booking.

    Rules:
    - Customer must own the booking.
    - Booking must be completed.
    - A booking can have only one review.
    - Review data is derived from the booking.
    """

    _validate_completed_booking(
        booking=booking,
        customer=customer,
    )

    if Review.objects.filter(booking=booking).exists():
        raise ValidationError("This booking has already been reviewed.")

    if not 1 <= rating <= 5:
        raise ValidationError("Rating must be between 1 and 5.")

    if not comment or not comment.strip():
        raise ValidationError("Review comment cannot be empty.")

    review = Review.objects.create(
        booking=booking,
        customer=booking.customer,
        service=booking.service,
        provider=booking.provider,
        rating=rating,
        comment=comment.strip(),
    )

    transaction.on_commit(
        lambda: notify_review_received(
            provider=review.provider,
            review=review,
        )
    )

    return review


@transaction.atomic
def update_review(*, review, customer, rating, comment):
    """
    Update an existing review.

    Only the customer who created the review
    can modify it.
    """

    if review.customer_id != customer.id:
        raise ValidationError("You are not allowed to update this review.")

    if not 1 <= rating <= 5:
        raise ValidationError("Rating must be between 1 and 5.")

    if not comment or not comment.strip():
        raise ValidationError("Review comment cannot be empty.")

    review.rating = rating
    review.comment = comment.strip()
    review.save(
        update_fields=[
            "rating",
            "comment",
            "updated_at",
        ]
    )

    return review


@transaction.atomic
def delete_review(*, review, customer):
    """
    Delete an existing review.

    Only the customer who created the review
    can delete it.
    """

    if review.customer_id != customer.id:
        raise ValidationError("You are not allowed to delete this review.")

    review.delete()


def get_review_for_booking(*, booking):
    """
    Return the review associated with a booking,
    or None if no review exists.
    """

    return Review.objects.filter(booking=booking).first()


def get_service_rating(*, service):
    """
    Return rating statistics for a service.

    Returns:
        {
            "average_rating": float | None,
            "review_count": int,
        }
    """

    stats = Review.objects.filter(
        service=service,
    ).aggregate(
        average_rating=Avg("rating"),
        review_count=Count("id"),
    )

    average_rating = stats["average_rating"]

    if average_rating is not None:
        average_rating = float(average_rating)

    return {
        "average_rating": average_rating,
        "review_count": stats["review_count"],
    }


def get_provider_rating(*, provider):
    """
    Return rating statistics for a provider.

    Returns:
        {
            "average_rating": float | None,
            "review_count": int,
        }
    """

    stats = Review.objects.filter(
        provider=provider,
    ).aggregate(
        average_rating=Avg("rating"),
        review_count=Count("id"),
    )

    average_rating = stats["average_rating"]

    if average_rating is not None:
        average_rating = float(average_rating)

    return {
        "average_rating": average_rating,
        "review_count": stats["review_count"],
    }
