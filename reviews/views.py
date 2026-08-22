from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect, render
from bookings.models import Booking

from .forms import ReviewForm
from .models import Review
from .services import create_review, delete_review, update_review


@login_required
def create_review_view(request, booking_id):
    booking = get_object_or_404(
        Booking.objects.select_related(
            "customer",
            "service",
            "provider",
        ),
        pk=booking_id,
    )

    if booking.customer_id != request.user.id:
        messages.error(
            request,
            "You are not allowed to review this booking.",
        )
        return redirect("bookings:detail", pk=booking.pk)

    if booking.status != Booking.Status.COMPLETED:
        messages.error(
            request,
            "Only completed bookings can be reviewed.",
        )
        return redirect("bookings:detail", pk=booking.pk)

    if Review.objects.filter(booking=booking).exists():
        messages.info(
            request,
            "This booking has already been reviewed.",
        )
        return redirect("reviews:detail", booking_id=booking.pk)

    if request.method == "POST":
        form = ReviewForm(request.POST)

        if form.is_valid():
            try:
                create_review(
                    booking=booking,
                    customer=request.user,
                    rating=form.cleaned_data["rating"],
                    comment=form.cleaned_data["comment"],
                )
            except ValidationError as exc:
                form.add_error(None, exc.message)
            else:
                messages.success(
                    request,
                    "Your review has been submitted successfully.",
                )
                return redirect(
                    "reviews:detail",
                    booking_id=booking.pk,
                )
    else:
        form = ReviewForm()

    return render(
        request,
        "reviews/create.html",
        {
            "form": form,
            "booking": booking,
        },
    )


@login_required
def review_detail_view(request, booking_id):
    booking = get_object_or_404(
        Booking.objects.select_related(
            "customer",
            "service",
            "provider",
        ),
        pk=booking_id,
    )

    if booking.customer_id != request.user.id:
        messages.error(
            request,
            "You are not allowed to view this review.",
        )
        return redirect("bookings:detail", pk=booking.pk)

    review = get_object_or_404(
        Review.objects.select_related(
            "booking",
            "customer",
            "service",
            "provider",
        ),
        booking=booking,
    )

    return render(
        request,
        "reviews/detail.html",
        {
            "review": review,
            "booking": booking,
        },
    )


@login_required
def update_review_view(request, booking_id):
    review = get_object_or_404(
        Review.objects.select_related(
            "booking",
            "customer",
            "service",
            "provider",
        ),
        booking_id=booking_id,
    )

    if review.customer_id != request.user.id:
        messages.error(
            request,
            "You are not allowed to edit this review.",
        )
        return redirect(
            "bookings:detail",
            pk=review.booking_id,
        )

    if request.method == "POST":
        form = ReviewForm(request.POST, instance=review)

        if form.is_valid():
            try:
                update_review(
                    review=review,
                    customer=request.user,
                    rating=form.cleaned_data["rating"],
                    comment=form.cleaned_data["comment"],
                )
            except ValidationError as exc:
                form.add_error(None, exc.message)
            else:
                messages.success(
                    request,
                    "Your review has been updated successfully.",
                )
                return redirect(
                    "reviews:detail",
                    booking_id=review.booking_id,
                )
    else:
        form = ReviewForm(instance=review)

    return render(
        request,
        "reviews/edit.html",
        {
            "form": form,
            "review": review,
            "booking": review.booking,
        },
    )


@login_required
def delete_review_view(request, booking_id):
    review = get_object_or_404(
        Review.objects.select_related(
            "booking",
            "customer",
        ),
        booking_id=booking_id,
    )

    if review.customer_id != request.user.id:
        messages.error(
            request,
            "You are not allowed to delete this review.",
        )
        return redirect(
            "bookings:detail",
            pk=review.booking_id,
        )

    if request.method != "POST":
        messages.error(
            request,
            "Invalid request method.",
        )
        return redirect(
            "reviews:detail",
            booking_id=review.booking_id,
        )

    booking_id = review.booking_id

    delete_review(
        review=review,
        customer=request.user,
    )

    messages.success(
        request,
        "Your review has been deleted successfully.",
    )

    return redirect(
        "bookings:detail",
        pk=booking_id,
    )
