from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    fieldsets = (
        *UserAdmin.fieldsets,
        (
            "Provia Information",
            {
                "fields": (
                    "role",
                    "phone",
                    "is_verified",
                ),
            },
        ),
    )

    add_fieldsets = (
        *UserAdmin.add_fieldsets,
        (
            "Provia Information",
            {
                "fields": (
                    "role",
                    "phone",
                    "is_verified",
                ),
            },
        ),
    )

    list_display = (
        "username",
        "email",
        "first_name",
        "last_name",
        "role",
        "is_verified",
        "is_active",
    )

    list_filter = (
        "role",
        "is_verified",
        "is_active",
        "is_staff",
    )

    search_fields = (
        "username",
        "email",
        "first_name",
        "last_name",
        "phone",
    )