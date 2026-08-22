import os

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from providers.models import ProviderProfile


class Command(BaseCommand):
    help = "Create or reset the local Provia manual-test users."

    customer_username = "Mubashir"
    provider_username = "MehnaA"
    default_customer_password = "ProviaCustomerDev2026!"
    default_provider_password = "ProviaProviderDev2026!"

    def add_arguments(self, parser):
        parser.add_argument(
            "--customer-password",
            default=os.environ.get(
                "PROVIA_DEV_CUSTOMER_PASSWORD",
                self.default_customer_password,
            ),
            help="Password for the local customer account.",
        )
        parser.add_argument(
            "--provider-password",
            default=os.environ.get(
                "PROVIA_DEV_PROVIDER_PASSWORD",
                self.default_provider_password,
            ),
            help="Password for the local provider account.",
        )

    def handle(self, *args, **options):
        if not settings.DEBUG:
            raise CommandError(
                "setup_dev_users is disabled when DEBUG is False."
            )

        User = get_user_model()
        customer, customer_created = User.objects.get_or_create(
            username=self.customer_username,
            defaults={
                "email": "mubashir@example.com",
                "role": User.Role.CUSTOMER,
                "is_active": True,
                "is_verified": True,
            },
        )
        customer.role = User.Role.CUSTOMER
        customer.is_active = True
        customer.is_verified = True
        customer.set_password(options["customer_password"])
        customer.save(update_fields=["role", "is_active", "is_verified", "password"])

        provider, provider_created = User.objects.get_or_create(
            username=self.provider_username,
            defaults={
                "email": "mehnaa@example.com",
                "role": User.Role.PROVIDER,
                "is_active": True,
                "is_verified": True,
            },
        )
        provider.role = User.Role.PROVIDER
        provider.is_active = True
        provider.is_verified = True
        provider.set_password(options["provider_password"])
        provider.save(update_fields=["role", "is_active", "is_verified", "password"])

        profile, profile_created = ProviderProfile.objects.get_or_create(
            user=provider,
            defaults={
                "business_name": "MehnaA Plumbing & Leak Repair",
                "email": provider.email,
            },
        )

        customer_state = "created" if customer_created else "updated"
        provider_state = "created" if provider_created else "updated"
        profile_state = "created" if profile_created else "existing"
        self.stdout.write(
            self.style.SUCCESS(
                "Development users ready: "
                f"{customer.username} ({customer_state}), "
                f"{provider.username} ({provider_state}); "
                f"provider profile ({profile_state})."
            )
        )
