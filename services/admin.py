from django.contrib import admin

from providers.models import ProviderProfile

from .models import (
    ProviderAvailability,
    Service,
    ServiceCategory,
    ServiceLocation,
)


@admin.register(ProviderProfile)
class ProviderProfileAdmin(admin.ModelAdmin):
    list_display = (
        "business_name",
        "user",
        "city",
        "state",
        "created_at",
    )

    search_fields = (
        "business_name",
        "user__username",
        "user__email",
        "city",
        "state",
    )

    list_filter = (
        "state",
        "city",
    )

    readonly_fields = (
        "created_at",
        "updated_at",
    )


@admin.register(ServiceLocation)
class ServiceLocationAdmin(admin.ModelAdmin):
    list_display = (
        "service",
        "city",
        "state",
        "postal_code",
        "service_radius_km",
    )

    list_filter = (
        "city",
        "state",
    )

    search_fields = (
        "service__title",
        "city",
        "state",
        "postal_code",
    )

    readonly_fields = (
        "created_at",
        "updated_at",
    )


@admin.register(ProviderAvailability)
class ProviderAvailabilityAdmin(admin.ModelAdmin):
    list_display = (
        "provider",
        "weekday",
        "start_time",
        "end_time",
        "is_active",
    )

    list_filter = (
        "weekday",
        "is_active",
    )

    search_fields = (
        "provider__business_name",
        "provider__user__username",
    )

    autocomplete_fields = ("provider",)

    readonly_fields = (
        "created_at",
        "updated_at",
    )


@admin.register(ServiceCategory)
class ServiceCategoryAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "slug",
        "is_active",
        "created_at",
    )

    list_filter = ("is_active",)

    search_fields = (
        "name",
        "slug",
        "description",
    )

    prepopulated_fields = {"slug": ("name",)}

    readonly_fields = (
        "created_at",
        "updated_at",
    )


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "provider",
        "category",
        "price",
        "duration_minutes",
        "is_published",
        "created_at",
    )

    list_filter = (
        "is_published",
        "category",
    )

    search_fields = (
        "title",
        "description",
        "provider__business_name",
    )

    readonly_fields = (
        "created_at",
        "updated_at",
    )
