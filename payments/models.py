from decimal import Decimal

from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models

from bookings.models import Booking


class Payment(models.Model):

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        INITIATED = "initiated", "Initiated"
        SUCCESS = "success", "Success"
        FAILED = "failed", "Failed"
        CANCELLED = "cancelled", "Cancelled"

    booking = models.OneToOneField(
        Booking,
        on_delete=models.PROTECT,
        related_name="payment",
    )

    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[
            MinValueValidator(Decimal("0.00")),
        ],
    )

    currency = models.CharField(
        max_length=3,
        default="INR",
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )

    payment_reference = models.CharField(
        max_length=100,
        unique=True,
        blank=True,
        null=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = ["-created_at"]

        indexes = [
            models.Index(
                fields=["status"],
            ),
            models.Index(
                fields=["created_at"],
            ),
        ]

    def clean(self):
        errors = {}

        if self.booking_id:
            if self.amount != self.booking.total_amount:
                errors["amount"] = "Payment amount must match the booking total amount."

            if self.booking.status == Booking.Status.CANCELLED:
                errors["booking"] = "A cancelled booking cannot have a payment."

        if errors:
            raise ValidationError(errors)

    def __str__(self):
        return (
            f"Payment #{self.pk} - "
            f"Booking #{self.booking_id} - "
            f"{self.amount} {self.currency}"
        )
