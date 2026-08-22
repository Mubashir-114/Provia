from django.contrib import admin

from .models import Booking


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = (
        "service",
        "customer",
        "provider",
        "booking_date",
        "start_time",
        "end_time",
        "status",
        "created_at",
    )

    list_filter = (
        "status",
        "booking_date",
    )

    search_fields = (
        "service__title",
        "customer__username",
        "customer__email",
        "provider__business_name",
    )

    autocomplete_fields = (
        "customer",
        "service",
        "provider",
    )

    readonly_fields = (
        "created_at",
        "updated_at",
    )
