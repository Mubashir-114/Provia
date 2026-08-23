import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = (
        "Create/ensure a Django superuser from RENDER_ADMIN_USERNAME, "
        "RENDER_ADMIN_EMAIL and RENDER_ADMIN_PASSWORD. Safe no-op if unset "
        "and never fails the deployment pipeline."
    )

    def handle(self, *args, **options):
        User = get_user_model()

        username = os.getenv("RENDER_ADMIN_USERNAME")
        email = os.getenv("RENDER_ADMIN_EMAIL")
        password = os.getenv("RENDER_ADMIN_PASSWORD")

        if not (username and email and password):
            self.stdout.write(
                self.style.WARNING(
                    "RENDER_ADMIN_USERNAME/EMAIL/PASSWORD not all set; "
                    "skipping superuser creation."
                )
            )
            return

        try:
            if User.objects.filter(username=username).exists():
                user = User.objects.get(username=username)
                changed = False
                for attr, value in (("is_staff", True), ("is_superuser", True)):
                    if getattr(user, attr, None) != value:
                        setattr(user, attr, value)
                        changed = True

                if changed:
                    user.save(update_fields=["is_staff", "is_superuser"])
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"Ensured existing user '{username}' is a superuser."
                        )
                    )
                else:
                    self.stdout.write(
                        f"Superuser '{username}' already configured; "
                        "password left unchanged."
                    )
                return

            user = User.objects.create_superuser(
                username=username,
                email=email,
                password=password,
            )
            user.is_active = True
            user.save(update_fields=["is_active"])
            self.stdout.write(
                self.style.SUCCESS(f"Created superuser '{username}'.")
            )
        except Exception as exc:
            self.stderr.write(
                self.style.WARNING(
                    "Could not create/ensure superuser (the database may not "
                    f"be migrated yet): {exc}"
                )
            )
            return
