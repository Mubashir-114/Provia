from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from decimal import Decimal
from django.core.validators import MinValueValidator

class Booking(models.Model):

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        CONFIRMED = "confirmed", "Confirmed"
        CANCELLED = "cancelled", "Cancelled"
        COMPLETED = "completed", "Completed"

    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="bookings",
    )

    service = models.ForeignKey(
        "services.Service",
        on_delete=models.PROTECT,
        related_name="bookings",
    )

    provider = models.ForeignKey(
        "providers.ProviderProfile",
        on_delete=models.PROTECT,
        related_name="bookings",
    )

    booking_date = models.DateField()

    start_time = models.TimeField()

    end_time = models.TimeField()

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )

    total_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[
            MinValueValidator(Decimal("0.00")),
        ],
    )

    customer_notes = models.TextField(
        blank=True,
    )

    provider_notes = models.TextField(
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = [
            "-booking_date",
            "-start_time",
        ]

        indexes = [
            models.Index(
                fields=[
                    "provider",
                    "booking_date",
                    "status",
                ],
            ),
            models.Index(
                fields=[
                    "customer",
                    "booking_date",
                    "status",
                ],
            ),
            models.Index(
                fields=[
                    "service",
                    "booking_date",
                ],
            ),
        ]

    def clean(self):
        errors = {}

        if self.start_time and self.end_time and self.start_time >= self.end_time:
            errors["end_time"] = "End time must be later than start time."

        if (
            self.service_id
            and self.provider_id
            and self.service.provider_id != self.provider_id
        ):
            errors["provider"] = "Booking provider must match the service provider."

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        if self.total_amount is None and self.service_id:
            self.total_amount = self.service.price

        super().save(*args, **kwargs)

    def __str__(self):
        return (
            f"{self.service.title} - "
            f"{self.booking_date} "
            f"{self.start_time.strftime('%H:%M')}"
        )
