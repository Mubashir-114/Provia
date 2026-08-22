from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from django.core.paginator import Paginator
from django.db.models import Q
from accounts.decorators import role_required
from accounts.models import User
from providers.models import ProviderProfile
from reviews.services import get_service_rating, get_provider_rating
from reviews.models import Review

from .forms import ServiceForm, ProviderAvailabilityForm
from .models import Service, ProviderAvailability, ServiceCategory


@login_required
@role_required(User.Role.PROVIDER)
def service_list(request):
    provider_profile = get_object_or_404(
        ProviderProfile,
        user=request.user,
    )

    services = Service.objects.filter(
        provider=provider_profile,
    ).select_related(
        "category",
    )

    return render(
        request,
        "services/service_list.html",
        {
            "services": services,
            "provider_profile": provider_profile,
        },
    )


@login_required
@role_required(User.Role.PROVIDER)
def service_create(request):
    provider_profile = get_object_or_404(
        ProviderProfile,
        user=request.user,
    )

    if request.method == "POST":
        form = ServiceForm(request.POST)

        if form.is_valid():
            service = form.save(commit=False)
            service.provider = provider_profile
            service.save()

            messages.success(
                request,
                "Service created successfully.",
            )

            return redirect("services:list")

    else:
        form = ServiceForm()

    return render(
        request,
        "services/service_form.html",
        {
            "form": form,
            "page_title": "Create Service",
            "submit_label": "Create Service",
        },
    )


@login_required
@role_required(User.Role.PROVIDER)
def service_update(request, pk):
    provider_profile = get_object_or_404(
        ProviderProfile,
        user=request.user,
    )

    service = get_object_or_404(
        Service,
        pk=pk,
        provider=provider_profile,
    )

    if request.method == "POST":
        form = ServiceForm(
            request.POST,
            instance=service,
        )

        if form.is_valid():
            form.save()

            messages.success(
                request,
                "Service updated successfully.",
            )

            return redirect("services:list")

    else:
        form = ServiceForm(
            instance=service,
        )

    return render(
        request,
        "services/service_form.html",
        {
            "form": form,
            "service": service,
            "page_title": "Edit Service",
            "submit_label": "Update Service",
        },
    )


@login_required
@role_required(User.Role.PROVIDER)
def service_delete(request, pk):
    provider_profile = get_object_or_404(
        ProviderProfile,
        user=request.user,
    )

    service = get_object_or_404(
        Service,
        pk=pk,
        provider=provider_profile,
    )

    if request.method == "POST":
        service.delete()

        messages.success(
            request,
            "Service deleted successfully.",
        )

        return redirect("services:list")

    return render(
        request,
        "services/service_confirm_delete.html",
        {
            "service": service,
        },
    )


@login_required
@role_required(User.Role.PROVIDER)
@require_POST
def service_publish(request, pk):
    provider_profile = get_object_or_404(
        ProviderProfile,
        user=request.user,
    )

    service = get_object_or_404(
        Service,
        pk=pk,
        provider=provider_profile,
    )

    service.is_published = True
    service.save()

    messages.success(
        request,
        "Service published successfully.",
    )

    return redirect("services:list")


@login_required
@role_required(User.Role.PROVIDER)
@require_POST
def service_unpublish(request, pk):
    provider_profile = get_object_or_404(
        ProviderProfile,
        user=request.user,
    )

    service = get_object_or_404(
        Service,
        pk=pk,
        provider=provider_profile,
    )

    service.is_published = False
    service.save()

    messages.success(
        request,
        "Service unpublished successfully.",
    )

    return redirect("services:list")


@login_required
@role_required(User.Role.PROVIDER)
def availability_list(request):
    provider_profile = get_object_or_404(
        ProviderProfile,
        user=request.user,
    )

    availabilities = ProviderAvailability.objects.filter(
        provider=provider_profile,
    )

    return render(
        request,
        "services/availability_list.html",
        {
            "availabilities": availabilities,
        },
    )


@login_required
@role_required(User.Role.PROVIDER)
def availability_create(request):
    provider_profile = get_object_or_404(
        ProviderProfile,
        user=request.user,
    )

    if request.method == "POST":
        form = ProviderAvailabilityForm(request.POST)

        if form.is_valid():
            availability = form.save(commit=False)
            availability.provider = provider_profile
            availability.save()

            messages.success(
                request,
                "Availability added successfully.",
            )

            return redirect("services:availability_list")

    else:
        form = ProviderAvailabilityForm()

    return render(
        request,
        "services/availability_form.html",
        {
            "form": form,
            "page_title": "Add Availability",
            "submit_label": "Save Availability",
        },
    )


@login_required
@role_required(User.Role.PROVIDER)
def availability_update(request, pk):
    provider_profile = get_object_or_404(
        ProviderProfile,
        user=request.user,
    )

    availability = get_object_or_404(
        ProviderAvailability,
        pk=pk,
        provider=provider_profile,
    )

    if request.method == "POST":
        form = ProviderAvailabilityForm(
            request.POST,
            instance=availability,
        )

        if form.is_valid():
            form.save()

            messages.success(
                request,
                "Availability updated successfully.",
            )

            return redirect("services:availability_list")

    else:
        form = ProviderAvailabilityForm(
            instance=availability,
        )

    return render(
        request,
        "services/availability_form.html",
        {
            "form": form,
            "page_title": "Edit Availability",
            "submit_label": "Update Availability",
        },
    )


@login_required
@role_required(User.Role.PROVIDER)
def availability_delete(request, pk):
    provider_profile = get_object_or_404(
        ProviderProfile,
        user=request.user,
    )

    availability = get_object_or_404(
        ProviderAvailability,
        pk=pk,
        provider=provider_profile,
    )

    if request.method == "POST":
        availability.delete()

        messages.success(
            request,
            "Availability deleted successfully.",
        )

        return redirect("services:availability_list")

    return render(
        request,
        "services/availability_confirm_delete.html",
        {
            "availability": availability,
        },
    )


def public_service_list(request):
    services = Service.objects.filter(
        is_published=True,
        category__is_active=True,
    ).select_related(
        "provider",
        "category",
        "location",
    )

    query = request.GET.get("q", "").strip()
    category_slug = request.GET.get("category", "").strip()
    city = request.GET.get("city", "").strip()

    if query:
        services = services.filter(
            Q(title__icontains=query)
            | Q(description__icontains=query)
            | Q(provider__business_name__icontains=query)
            | Q(category__name__icontains=query)
        )

    if category_slug:
        services = services.filter(
            category__slug=category_slug,
        )

    if city:
        services = services.filter(
            location__city__icontains=city,
        )

    services = services.order_by(
        "-created_at",
    )

    paginator = Paginator(
        services,
        9,
    )

    page_number = request.GET.get("page")

    page_obj = paginator.get_page(
        page_number,
    )

    categories = ServiceCategory.objects.filter(is_active=True).order_by("name")

    return render(
        request,
        "services/public_service_list.html",
        {
            "page_obj": page_obj,
            "services": page_obj.object_list,
            "categories": categories,
            "query": query,
            "selected_category": category_slug,
            "city": city,
        },
    )


def public_service_detail(request, pk):
    service = get_object_or_404(
        Service.objects.select_related(
            "provider",
            "category",
            "location",
        ),
        pk=pk,
        is_published=True,
        category__is_active=True,
    )

    availability = ProviderAvailability.objects.filter(
        provider=service.provider,
        is_active=True,
    ).order_by(
        "weekday",
        "start_time",
    )

    rating = get_service_rating(service=service)
    provider_rating = get_provider_rating(provider=service.provider)

    reviews = Review.objects.filter(
        service=service,
    ).select_related(
        "customer",
        "booking",
        "provider",
    ).order_by(
        "-created_at",
    )

    return render(
        request,
        "services/public_service_detail.html",
        {
            "service": service,
            "availability": availability,
            "rating": rating,
            "provider_rating": provider_rating,
            "reviews": reviews,
        },
    )
