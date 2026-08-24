from django.contrib.auth.models import AbstractUser
from django.db import models

from cloudinary.models import CloudinaryField


class User(AbstractUser):
    class Role(models.TextChoices):
        CUSTOMER = "customer", "Customer"
        PROVIDER = "provider", "Provider"
        ADMIN = "admin", "Admin"

    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.CUSTOMER,
    )
    phone = models.CharField(
        max_length=20,
        blank=True,
    )
    is_verified = models.BooleanField(default=False)

    profile_picture = CloudinaryField(
        "profile picture",
        folder="provia/customers",
        blank=True,
        null=True,
    )

    def __str__(self):
        return self.username
