from datetime import date, datetime

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from accounts.decorators import role_required
from accounts.models import User
from bookings.forms import BookingForm, BookingStatusUpdateForm
from bookings.models import Booking
from bookings.services import (
    cancel_booking,
    create_booking as create_booking_service,
    get_available_slots,
    update_booking_status,
)
from chat.services import get_or_create_conversation_for_booking
from payments.models import Payment
from providers.models import ProviderProfile
from services.models import Service


VALID_STATUSES = {choice[0] for choice in Booking.Status.choices}


def _paginate(request, queryset, per_page=10):
    paginator = Paginator(queryset, per_page)
    return paginator.get_page(request.GET.get("page"))


def _published_service_queryset():
    return Service.objects.filter(
        is_published=True,
        category__is_active=True,
    ).select_related(
        "provider",
        "category",
    )


@login_required
@role_required(User.Role.CUSTOMER)
def my_bookings(request):
    current_status = request.GET.get("status", "")

    bookings = Booking.objects.filter(
        customer=request.user,
    ).select_related(
        "service",
        "service__category",
        "provider",
    )

    if current_status in VALID_STATUSES:
        bookings = bookings.filter(
            status=current_status,
        )
    else:
        current_status = ""

    page_obj = _paginate(request, bookings)

    return render(
        request,
        "bookings/my_bookings.html",
        {
            "bookings": page_obj.object_list,
            "page_obj": page_obj,
            "current_status": current_status,
        },
    )


@login_required
@role_required(User.Role.CUSTOMER)
def booking_create(request, service_id):
    service = get_object_or_404(
        _published_service_queryset(),
        pk=service_id,
    )

    if request.method == "POST":
        form = BookingForm(request.POST)

        if form.is_valid():
            try:
                booking = create_booking_service(
                    customer=request.user,
                    service=service,
                    booking_date=form.cleaned_data["booking_date"],
                    start_time=form.cleaned_data["start_time"],
                    customer_notes=form.cleaned_data["customer_notes"],
                )
                return redirect(
                    "bookings:detail",
                    pk=booking.pk,
                )
            except ValidationError as exc:
                form.add_error(
                    None,
                    exc,
                )
    else:
        form = BookingForm()

    return render(
        request,
        "bookings/create.html",
        {
            "form": form,
            "service": service,
        },
    )


@login_required
@role_required(User.Role.CUSTOMER)
def available_slots(request, service_id):
    service = get_object_or_404(
        _published_service_queryset(),
        pk=service_id,
    )

    raw_date = request.GET.get("date", "")

    try:
        booking_date = datetime.strptime(
            raw_date,
            "%Y-%m-%d",
        ).date()
    except ValueError:
        return JsonResponse(
            {"error": "Invalid date."},
            status=400,
        )

    if booking_date <= date.today():
        return JsonResponse(
            {"error": "Please select a future date."},
            status=400,
        )

    slots = [
        {
            "start_time": slot["start_time"].strftime("%H:%M"),
            "end_time": slot["end_time"].strftime("%H:%M"),
        }
        for slot in get_available_slots(
            service,
            booking_date,
        )
    ]

    return JsonResponse(
        slots,
        safe=False,
    )


@login_required
@role_required(User.Role.CUSTOMER)
def booking_detail(request, pk):
    booking = get_object_or_404(
        Booking.objects.filter(
            customer=request.user,
        ).select_related(
            "service",
            "service__category",
            "provider",
            "provider__user",
        ),
        pk=pk,
    )

    payment = Payment.objects.filter(
        booking=booking,
    ).first()

    return render(
        request,
        "bookings/detail.html",
        {
            "booking": booking,
            "payment": payment,
        },
    )


@login_required
@role_required(User.Role.CUSTOMER)
@require_POST
def booking_cancel(request, pk):
    booking = get_object_or_404(
        Booking.objects.filter(
            customer=request.user,
        ),
        pk=pk,
    )

    try:
        cancel_booking(
            booking=booking,
            customer=request.user,
        )
    except ValidationError:
        pass

    return redirect(
        "bookings:detail",
        pk=booking.pk,
    )


@login_required
@role_required(User.Role.PROVIDER)
def provider_bookings(request):
    provider = get_object_or_404(
        ProviderProfile,
        user=request.user,
    )

    current_status = request.GET.get("status", "")
    bookings = Booking.objects.filter(
        provider=provider,
    ).select_related(
        "customer",
        "service",
        "service__category",
    )

    if current_status in VALID_STATUSES:
        bookings = bookings.filter(
            status=current_status,
        )
    else:
        current_status = ""

    page_obj = _paginate(request, bookings)

    return render(
        request,
        "bookings/provider_bookings.html",
        {
            "bookings": page_obj.object_list,
            "page_obj": page_obj,
            "current_status": current_status,
        },
    )


@login_required
@role_required(User.Role.PROVIDER)
def provider_booking_detail(request, pk):
    provider = get_object_or_404(
        ProviderProfile,
        user=request.user,
    )
    booking = get_object_or_404(
        Booking.objects.filter(
            provider=provider,
        ).select_related(
            "customer",
            "service",
            "service__category",
        ),
        pk=pk,
    )

    return render(
        request,
        "bookings/provider_detail.html",
        {
            "booking": booking,
            "form": BookingStatusUpdateForm(
                initial={
                    "status": booking.status,
                    "provider_notes": booking.provider_notes,
                }
            ),
        },
    )


@login_required
@role_required(User.Role.PROVIDER)
@require_POST
def provider_update_booking_status(request, pk):
    provider = get_object_or_404(
        ProviderProfile,
        user=request.user,
    )
    booking = get_object_or_404(
        Booking.objects.filter(
            provider=provider,
        ).select_related(
            "customer",
            "service",
            "service__category",
        ),
        pk=pk,
    )

    form = BookingStatusUpdateForm(request.POST)

    if form.is_valid():
        try:
            update_booking_status(
                booking=booking,
                new_status=form.cleaned_data["status"],
                provider=provider,
                provider_notes=form.cleaned_data["provider_notes"],
            )
            return redirect(
                "bookings:provider_detail",
                pk=booking.pk,
            )
        except ValidationError as exc:
            form.add_error(
                None,
                exc,
            )

    return render(
        request,
        "bookings/provider_detail.html",
        {
            "booking": booking,
            "form": form,
        },
    )


@login_required
@require_POST
def booking_chat(request, pk):
    booking = get_object_or_404(
        Booking.objects.select_related(
            "customer",
            "provider",
            "provider__user",
        ),
        pk=pk,
    )

    if request.user != booking.customer and request.user != booking.provider.user:
        raise PermissionDenied

    conversation = get_or_create_conversation_for_booking(
        booking=booking,
        user=request.user,
    )

    return redirect("chat:conversation", conversation_id=conversation.pk)

