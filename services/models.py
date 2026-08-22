from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models

from providers.models import ProviderProfile


class ServiceCategory(models.Model):
    name = models.CharField(
        max_length=100,
        unique=True,
    )

    slug = models.SlugField(
        max_length=120,
        unique=True,
    )

    description = models.TextField(
        blank=True,
    )

    is_active = models.BooleanField(
        default=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = ["name"]
        verbose_name = "Service Category"
        verbose_name_plural = "Service Categories"

    def __str__(self):
        return self.name


class Service(models.Model):
    provider = models.ForeignKey(
        ProviderProfile,
        on_delete=models.CASCADE,
        related_name="services",
    )

    category = models.ForeignKey(
        ServiceCategory,
        on_delete=models.PROTECT,
        related_name="services",
    )

    title = models.CharField(
        max_length=150,
    )

    description = models.TextField()

    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[
            MinValueValidator(0),
        ],
    )

    duration_minutes = models.PositiveIntegerField(
        validators=[
            MinValueValidator(1),
        ],
    )

    is_published = models.BooleanField(
        default=False,
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
                fields=["provider", "is_published"],
            ),
            models.Index(
                fields=["category", "is_published"],
            ),
        ]

    def __str__(self):
        return self.title


class ServiceLocation(models.Model):
    service = models.OneToOneField(
        Service,
        on_delete=models.CASCADE,
        related_name="location",
    )

    address = models.TextField(
        blank=True,
    )

    city = models.CharField(
        max_length=100,
    )

    state = models.CharField(
        max_length=100,
    )

    postal_code = models.CharField(
        max_length=20,
        blank=True,
    )

    service_radius_km = models.PositiveIntegerField(
        default=0,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        indexes = [
            models.Index(
                fields=["city", "state"],
            ),
            models.Index(
                fields=["postal_code"],
            ),
        ]

    def __str__(self):
        return f"{self.service.title} - {self.city}"


class ProviderAvailability(models.Model):
    class Weekday(models.IntegerChoices):
        MONDAY = 0, "Monday"
        TUESDAY = 1, "Tuesday"
        WEDNESDAY = 2, "Wednesday"
        THURSDAY = 3, "Thursday"
        FRIDAY = 4, "Friday"
        SATURDAY = 5, "Saturday"
        SUNDAY = 6, "Sunday"

    provider = models.ForeignKey(
        ProviderProfile,
        on_delete=models.CASCADE,
        related_name="availabilities",
    )

    weekday = models.PositiveSmallIntegerField(
        choices=Weekday.choices,
    )

    start_time = models.TimeField()

    end_time = models.TimeField()

    is_active = models.BooleanField(
        default=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = [
            "weekday",
            "start_time",
        ]

        constraints = [
            models.UniqueConstraint(
                fields=[
                    "provider",
                    "weekday",
                ],
                name="unique_provider_weekday_availability",
            ),
        ]

        indexes = [
            models.Index(
                fields=[
                    "provider",
                    "weekday",
                    "is_active",
                ],
            ),
        ]

    def clean(self):
        if self.start_time >= self.end_time:
            raise ValidationError("End time must be later than start time.")

    def __str__(self):
        return f"{self.provider.business_name} - " f"{self.get_weekday_display()}"
