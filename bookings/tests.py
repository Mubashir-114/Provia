from datetime import date, time, timedelta
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from accounts.models import User
from payments.models import Payment
from providers.models import ProviderProfile
from services.models import (
    ProviderAvailability,
    Service,
    ServiceCategory,
)

from .models import Booking
from .services import create_booking, get_available_slots


def future_date(days=7):
    return date.today() + timedelta(days=days)


class BookingModelTests(TestCase):

    def setUp(self):
        self.provider_user = User.objects.create_user(
            username="bookingprovider",
            email="provider@example.com",
            password="StrongPassword123!",
            role=User.Role.PROVIDER,
            is_verified=True,
        )

        self.customer = User.objects.create_user(
            username="bookingcustomer",
            email="customer@example.com",
            password="StrongPassword123!",
            role=User.Role.CUSTOMER,
            is_verified=True,
        )

        self.provider = ProviderProfile.objects.create(
            user=self.provider_user,
            business_name="Provia Services",
        )

        self.category = ServiceCategory.objects.create(
            name="Cleaning",
            slug="cleaning",
            is_active=True,
        )

        self.service = Service.objects.create(
            provider=self.provider,
            category=self.category,
            title="Home Cleaning",
            description="Professional home cleaning.",
            price=Decimal("1000.00"),
            duration_minutes=120,
            is_published=True,
        )

    def test_booking_can_be_created(self):
        booking = Booking.objects.create(
            customer=self.customer,
            service=self.service,
            provider=self.provider,
            booking_date=date(2026, 8, 20),
            start_time=time(10, 0),
            end_time=time(12, 0),
        )

        self.assertEqual(
            booking.customer,
            self.customer,
        )

        self.assertEqual(
            booking.service,
            self.service,
        )

        self.assertEqual(
            booking.provider,
            self.provider,
        )

        self.assertEqual(
            booking.status,
            Booking.Status.PENDING,
        )

    def test_booking_string_representation(self):
        booking = Booking.objects.create(
            customer=self.customer,
            service=self.service,
            provider=self.provider,
            booking_date=date(2026, 8, 20),
            start_time=time(10, 0),
            end_time=time(12, 0),
        )

        self.assertEqual(
            str(booking),
            "Home Cleaning - 2026-08-20 10:00",
        )

    def test_invalid_time_range_is_rejected(self):
        booking = Booking(
            customer=self.customer,
            service=self.service,
            provider=self.provider,
            booking_date=date(2026, 8, 20),
            start_time=time(14, 0),
            end_time=time(12, 0),
        )

        with self.assertRaises(ValidationError):
            booking.full_clean()

    def test_equal_start_and_end_time_is_rejected(self):
        booking = Booking(
            customer=self.customer,
            service=self.service,
            provider=self.provider,
            booking_date=date(2026, 8, 20),
            start_time=time(12, 0),
            end_time=time(12, 0),
        )

        with self.assertRaises(ValidationError):
            booking.full_clean()

    def test_booking_status_defaults_to_pending(self):
        booking = Booking.objects.create(
            customer=self.customer,
            service=self.service,
            provider=self.provider,
            booking_date=date(2026, 8, 20),
            start_time=time(10, 0),
            end_time=time(12, 0),
        )

        self.assertEqual(
            booking.status,
            Booking.Status.PENDING,
        )

    def test_booking_without_total_amount_uses_service_price(self):
        booking = Booking.objects.create(
            customer=self.customer,
            service=self.service,
            provider=self.provider,
            booking_date=date(2026, 8, 20),
            start_time=time(10, 0),
            end_time=time(12, 0),
        )

        self.assertEqual(
            booking.total_amount,
            self.service.price,
        )

    def test_explicit_total_amount_is_not_overwritten(self):
        booking = Booking.objects.create(
            customer=self.customer,
            service=self.service,
            provider=self.provider,
            booking_date=date(2026, 8, 20),
            start_time=time(10, 0),
            end_time=time(12, 0),
            total_amount=Decimal("750.00"),
        )

        self.assertEqual(
            booking.total_amount,
            Decimal("750.00"),
        )


class AvailableSlotTests(TestCase):

    def setUp(self):
        self.provider_user = User.objects.create_user(
            username="slotprovider",
            email="slotprovider@example.com",
            password="StrongPassword123!",
            role=User.Role.PROVIDER,
            is_verified=True,
        )

        self.customer = User.objects.create_user(
            username="slotcustomer",
            email="slotcustomer@example.com",
            password="StrongPassword123!",
            role=User.Role.CUSTOMER,
            is_verified=True,
        )

        self.provider = ProviderProfile.objects.create(
            user=self.provider_user,
            business_name="Slot Provider",
        )

        self.category = ServiceCategory.objects.create(
            name="Cleaning",
            slug="slot-cleaning",
            is_active=True,
        )

        self.service = Service.objects.create(
            provider=self.provider,
            category=self.category,
            title="One Hour Cleaning",
            description="One hour cleaning service.",
            price=Decimal("1000.00"),
            duration_minutes=60,
            is_published=True,
        )

        self.booking_date = future_date(7)

        ProviderAvailability.objects.create(
            provider=self.provider,
            weekday=self.booking_date.weekday(),
            start_time=time(9, 0),
            end_time=time(17, 0),
            is_active=True,
        )

    def test_service_duration_controls_slot_length(self):
        self.service.duration_minutes = 120
        self.service.save()

        slots = get_available_slots(
            self.service,
            self.booking_date,
        )

        self.assertEqual(
            len(slots),
            4,
        )

        self.assertEqual(
            slots[0]["start_time"],
            time(9, 0),
        )

        self.assertEqual(
            slots[0]["end_time"],
            time(11, 0),
        )

        self.assertEqual(
            slots[-1]["start_time"],
            time(15, 0),
        )

        self.assertEqual(
            slots[-1]["end_time"],
            time(17, 0),
        )

    def test_existing_booking_blocks_overlapping_slot(self):
        Booking.objects.create(
            customer=self.customer,
            service=self.service,
            provider=self.provider,
            booking_date=self.booking_date,
            start_time=time(13, 0),
            end_time=time(14, 0),
            status=Booking.Status.CONFIRMED,
        )

        slots = get_available_slots(
            self.service,
            self.booking_date,
        )

        self.assertNotIn(
            {
                "start_time": time(13, 0),
                "end_time": time(14, 0),
            },
            slots,
        )

        self.assertEqual(
            len(slots),
            7,
        )

    def test_pending_booking_blocks_slot(self):
        Booking.objects.create(
            customer=self.customer,
            service=self.service,
            provider=self.provider,
            booking_date=self.booking_date,
            start_time=time(10, 0),
            end_time=time(11, 0),
            status=Booking.Status.PENDING,
        )

        slots = get_available_slots(
            self.service,
            self.booking_date,
        )

        self.assertNotIn(
            {
                "start_time": time(10, 0),
                "end_time": time(11, 0),
            },
            slots,
        )

    def test_cancelled_booking_does_not_block_slot(self):
        Booking.objects.create(
            customer=self.customer,
            service=self.service,
            provider=self.provider,
            booking_date=self.booking_date,
            start_time=time(10, 0),
            end_time=time(11, 0),
            status=Booking.Status.CANCELLED,
        )

        slots = get_available_slots(
            self.service,
            self.booking_date,
        )

        self.assertIn(
            {
                "start_time": time(10, 0),
                "end_time": time(11, 0),
            },
            slots,
        )

    def test_completed_booking_does_not_block_slot(self):
        Booking.objects.create(
            customer=self.customer,
            service=self.service,
            provider=self.provider,
            booking_date=self.booking_date,
            start_time=time(10, 0),
            end_time=time(11, 0),
            status=Booking.Status.COMPLETED,
        )

        slots = get_available_slots(
            self.service,
            self.booking_date,
        )

        self.assertIn(
            {
                "start_time": time(10, 0),
                "end_time": time(11, 0),
            },
            slots,
        )

    def test_adjacent_booking_does_not_block_next_slot(self):
        Booking.objects.create(
            customer=self.customer,
            service=self.service,
            provider=self.provider,
            booking_date=self.booking_date,
            start_time=time(10, 0),
            end_time=time(11, 0),
            status=Booking.Status.CONFIRMED,
        )

        slots = get_available_slots(
            self.service,
            self.booking_date,
        )

        self.assertIn(
            {
                "start_time": time(11, 0),
                "end_time": time(12, 0),
            },
            slots,
        )

    def test_inactive_availability_returns_no_slots(self):
        availability = ProviderAvailability.objects.get(
            provider=self.provider,
            weekday=self.booking_date.weekday(),
        )

        availability.is_active = False
        availability.save()

        slots = get_available_slots(
            self.service,
            self.booking_date,
        )

        self.assertEqual(
            slots,
            [],
        )

    def test_different_weekday_returns_no_slots(self):
        different_weekday = self.booking_date + timedelta(days=1)

        slots = get_available_slots(
            self.service,
            different_weekday,
        )

        self.assertEqual(
            slots,
            [],
        )


class BookingCreationTests(TestCase):

    def setUp(self):
        self.provider_user = User.objects.create_user(
            username="creationprovider",
            email="creationprovider@example.com",
            password="StrongPassword123!",
            role=User.Role.PROVIDER,
            is_verified=True,
        )

        self.customer = User.objects.create_user(
            username="creationcustomer",
            email="creationcustomer@example.com",
            password="StrongPassword123!",
            role=User.Role.CUSTOMER,
            is_verified=True,
        )

        self.provider = ProviderProfile.objects.create(
            user=self.provider_user,
            business_name="Creation Services",
        )

        self.category = ServiceCategory.objects.create(
            name="Cleaning",
            slug="creation-cleaning",
            is_active=True,
        )

        self.service = Service.objects.create(
            provider=self.provider,
            category=self.category,
            title="Home Cleaning",
            description="Home cleaning service.",
            price=Decimal("1000.00"),
            duration_minutes=60,
            is_published=True,
        )

        self.booking_date = future_date(7)

        ProviderAvailability.objects.create(
            provider=self.provider,
            weekday=self.booking_date.weekday(),
            start_time=time(9, 0),
            end_time=time(17, 0),
            is_active=True,
        )

    def test_customer_can_create_booking(self):
        booking = create_booking(
            customer=self.customer,
            service=self.service,
            booking_date=self.booking_date,
            start_time=time(10, 0),
            customer_notes="Please call before arrival.",
        )

        self.assertEqual(
            booking.customer,
            self.customer,
        )

        self.assertEqual(
            booking.provider,
            self.provider,
        )

        self.assertEqual(
            booking.start_time,
            time(10, 0),
        )

        self.assertEqual(
            booking.end_time,
            time(11, 0),
        )

        self.assertEqual(
            booking.status,
            Booking.Status.PENDING,
        )

    def test_unpublished_service_cannot_be_booked(self):
        self.service.is_published = False
        self.service.save()

        with self.assertRaises(ValidationError):
            create_booking(
                customer=self.customer,
                service=self.service,
                booking_date=self.booking_date,
                start_time=time(10, 0),
            )

    def test_inactive_category_service_cannot_be_booked(self):
        self.category.is_active = False
        self.category.save()

        with self.assertRaises(ValidationError):
            create_booking(
                customer=self.customer,
                service=self.service,
                booking_date=self.booking_date,
                start_time=time(10, 0),
            )

    def test_provider_cannot_book_own_service(self):
        with self.assertRaises(ValidationError):
            create_booking(
                customer=self.provider_user,
                service=self.service,
                booking_date=self.booking_date,
                start_time=time(10, 0),
            )

    def test_unavailable_slot_cannot_be_booked(self):
        with self.assertRaises(ValidationError):
            create_booking(
                customer=self.customer,
                service=self.service,
                booking_date=self.booking_date,
                start_time=time(17, 0),
            )

    def test_already_booked_slot_cannot_be_booked(self):
        create_booking(
            customer=self.customer,
            service=self.service,
            booking_date=self.booking_date,
            start_time=time(10, 0),
        )

        another_customer = User.objects.create_user(
            username="anothercustomer",
            email="another@example.com",
            password="StrongPassword123!",
            role=User.Role.CUSTOMER,
            is_verified=True,
        )

        with self.assertRaises(ValidationError):
            create_booking(
                customer=another_customer,
                service=self.service,
                booking_date=self.booking_date,
                start_time=time(10, 0),
            )

    def test_past_date_booking_is_rejected(self):
        with self.assertRaises(ValidationError) as ctx:
            create_booking(
                customer=self.customer,
                service=self.service,
                booking_date=date(2020, 1, 1),
                start_time=time(10, 0),
            )
        self.assertIn("Please select a future date.", str(ctx.exception))


class AvailableSlotViewTests(TestCase):

    def setUp(self):
        self.provider_user = User.objects.create_user(
            username="endpointprovider",
            email="endpointprovider@example.com",
            password="StrongPassword123!",
            role=User.Role.PROVIDER,
            is_verified=True,
        )

        self.customer = User.objects.create_user(
            username="endpointcustomer",
            email="endpointcustomer@example.com",
            password="StrongPassword123!",
            role=User.Role.CUSTOMER,
            is_verified=True,
        )

        self.provider = ProviderProfile.objects.create(
            user=self.provider_user,
            business_name="Endpoint Provider",
        )

        self.category = ServiceCategory.objects.create(
            name="Cleaning",
            slug="endpoint-cleaning",
            is_active=True,
        )

        self.service = Service.objects.create(
            provider=self.provider,
            category=self.category,
            title="Endpoint Cleaning",
            description="Endpoint test service.",
            price=Decimal("1000.00"),
            duration_minutes=60,
            is_published=True,
        )

        self.booking_date = future_date(7)

        ProviderAvailability.objects.create(
            provider=self.provider,
            weekday=self.booking_date.weekday(),
            start_time=time(9, 0),
            end_time=time(12, 0),
            is_active=True,
        )

        self.url = reverse(
            "bookings:available_slots",
            kwargs={"service_id": self.service.pk},
        )

    def test_slot_endpoint_requires_authentication(self):
        response = self.client.get(f"{self.url}?date={self.booking_date.isoformat()}")
        self.assertIn(response.status_code, [401, 302])

    def test_customer_can_retrieve_slots(self):
        self.client.force_login(self.customer)
        response = self.client.get(f"{self.url}?date={self.booking_date.isoformat()}")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data), 3)
        self.assertEqual(data[0]["start_time"], "09:00")
        self.assertEqual(data[0]["end_time"], "10:00")

    def test_provider_cannot_use_customer_slot_endpoint(self):
        self.client.force_login(self.provider_user)
        response = self.client.get(f"{self.url}?date={self.booking_date.isoformat()}")
        self.assertEqual(response.status_code, 403)

    def test_draft_service_returns_404(self):
        self.service.is_published = False
        self.service.save()
        self.client.force_login(self.customer)
        response = self.client.get(f"{self.url}?date={self.booking_date.isoformat()}")
        self.assertEqual(response.status_code, 404)

    def test_inactive_category_returns_404(self):
        self.category.is_active = False
        self.category.save()
        self.client.force_login(self.customer)
        response = self.client.get(f"{self.url}?date={self.booking_date.isoformat()}")
        self.assertEqual(response.status_code, 404)

    def test_invalid_date_is_rejected(self):
        self.client.force_login(self.customer)
        response = self.client.get(f"{self.url}?date=invalid-date")
        self.assertEqual(response.status_code, 400)
        self.assertIn("error", response.json())

    def test_past_date_is_rejected(self):
        self.client.force_login(self.customer)
        response = self.client.get(f"{self.url}?date=2020-01-01")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.json().get("error"),
            "Please select a future date.",
        )

    def test_date_with_no_availability_returns_empty_slots(self):
        self.client.force_login(self.customer)
        response = self.client.get(
            f"{self.url}?date={(self.booking_date + timedelta(days=1)).isoformat()}"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [])

    def test_available_slots_match_provider_availability(self):
        self.client.force_login(self.customer)
        response = self.client.get(f"{self.url}?date={self.booking_date.isoformat()}")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        expected = [
            {"start_time": "09:00", "end_time": "10:00"},
            {"start_time": "10:00", "end_time": "11:00"},
            {"start_time": "11:00", "end_time": "12:00"},
        ]
        self.assertEqual(data, expected)

    def test_existing_bookings_remove_occupied_slots(self):
        Booking.objects.create(
            customer=self.customer,
            service=self.service,
            provider=self.provider,
            booking_date=self.booking_date,
            start_time=time(10, 0),
            end_time=time(11, 0),
            status=Booking.Status.PENDING,
        )
        self.client.force_login(self.customer)
        response = self.client.get(f"{self.url}?date={self.booking_date.isoformat()}")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data), 2)
        start_times = [s["start_time"] for s in data]
        self.assertNotIn("10:00", start_times)

    def test_cancelled_bookings_do_not_remove_slots(self):
        Booking.objects.create(
            customer=self.customer,
            service=self.service,
            provider=self.provider,
            booking_date=self.booking_date,
            start_time=time(10, 0),
            end_time=time(11, 0),
            status=Booking.Status.CANCELLED,
        )
        self.client.force_login(self.customer)
        response = self.client.get(f"{self.url}?date={self.booking_date.isoformat()}")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data), 3)
        start_times = [s["start_time"] for s in data]
        self.assertIn("10:00", start_times)


class BookingViewSubmitTests(TestCase):

    def setUp(self):
        self.provider_user = User.objects.create_user(
            username="submitprovider",
            email="submitprovider@example.com",
            password="StrongPassword123!",
            role=User.Role.PROVIDER,
            is_verified=True,
        )

        self.customer = User.objects.create_user(
            username="submitcustomer",
            email="submitcustomer@example.com",
            password="StrongPassword123!",
            role=User.Role.CUSTOMER,
            is_verified=True,
        )

        self.provider = ProviderProfile.objects.create(
            user=self.provider_user,
            business_name="Submit Provider",
        )

        self.category = ServiceCategory.objects.create(
            name="Cleaning",
            slug="submit-cleaning",
            is_active=True,
        )

        self.service = Service.objects.create(
            provider=self.provider,
            category=self.category,
            title="Submit Cleaning Service",
            description="Submit test service.",
            price=Decimal("1500.00"),
            duration_minutes=90,
            is_published=True,
        )

        self.booking_date = future_date(7)

        ProviderAvailability.objects.create(
            provider=self.provider,
            weekday=self.booking_date.weekday(),
            start_time=time(9, 0),
            end_time=time(17, 0),
            is_active=True,
        )

        self.create_url = reverse(
            "bookings:create",
            kwargs={"service_id": self.service.pk},
        )

    def test_customer_can_select_valid_slot_and_create_booking(self):
        self.client.force_login(self.customer)
        response = self.client.post(
            self.create_url,
            {
                "booking_date": self.booking_date.isoformat(),
                "start_time": "09:00",
                "customer_notes": "Call on arrival",
            },
        )
        self.assertEqual(response.status_code, 302)
        booking = Booking.objects.get(
            customer=self.customer,
            service=self.service,
        )
        self.assertEqual(booking.booking_date, self.booking_date)
        self.assertEqual(booking.start_time, time(9, 0))
        self.assertEqual(booking.end_time, time(10, 30))
        self.assertEqual(booking.status, Booking.Status.PENDING)

    def test_invalid_manually_supplied_start_time_is_rejected(self):
        self.client.force_login(self.customer)
        response = self.client.post(
            self.create_url,
            {
                "booking_date": self.booking_date.isoformat(),
                "start_time": "09:15",
                "customer_notes": "",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            "The selected time slot is no longer available.",
        )

    def test_slot_becoming_unavailable_before_submission_is_rejected(self):
        self.client.force_login(self.customer)
        Booking.objects.create(
            customer=self.customer,
            service=self.service,
            provider=self.provider,
            booking_date=self.booking_date,
            start_time=time(9, 0),
            end_time=time(10, 30),
            status=Booking.Status.PENDING,
        )
        response = self.client.post(
            self.create_url,
            {
                "booking_date": self.booking_date.isoformat(),
                "start_time": "09:00",
                "customer_notes": "",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            "The selected time slot is no longer available. Please choose another slot.",
        )

    def test_end_time_is_calculated_from_service_duration(self):
        self.client.force_login(self.customer)
        self.client.post(
            self.create_url,
            {
                "booking_date": self.booking_date.isoformat(),
                "start_time": "10:30",
                "customer_notes": "",
            },
        )
        booking = Booking.objects.get(start_time=time(10, 30))
        self.assertEqual(booking.end_time, time(12, 0))

    def test_booking_status_remains_pending(self):
        self.client.force_login(self.customer)
        self.client.post(
            self.create_url,
            {
                "booking_date": self.booking_date.isoformat(),
                "start_time": "12:00",
                "customer_notes": "",
            },
        )
        booking = Booking.objects.get(start_time=time(12, 0))
        self.assertEqual(booking.status, Booking.Status.PENDING)


class CustomerMyBookingsViewTests(TestCase):

    def setUp(self):
        self.provider_user = User.objects.create_user(
            username="mb_provider",
            email="mb_provider@example.com",
            password="StrongPassword123!",
            role=User.Role.PROVIDER,
            is_verified=True,
        )

        self.customer_a = User.objects.create_user(
            username="customer_a",
            email="customer_a@example.com",
            password="StrongPassword123!",
            role=User.Role.CUSTOMER,
            is_verified=True,
        )

        self.customer_b = User.objects.create_user(
            username="customer_b",
            email="customer_b@example.com",
            password="StrongPassword123!",
            role=User.Role.CUSTOMER,
            is_verified=True,
        )

        self.provider = ProviderProfile.objects.create(
            user=self.provider_user,
            business_name="Provia Home Care",
            phone="9876543210",
            email="care@provia.com",
            city="Calicut",
            state="Kerala",
        )

        self.category = ServiceCategory.objects.create(
            name="Cleaning",
            slug="cleaning-care",
            is_active=True,
        )

        self.service = Service.objects.create(
            provider=self.provider,
            category=self.category,
            title="Premium Cleaning",
            description="Deep cleaning service for homes.",
            price=Decimal("1500.00"),
            duration_minutes=60,
            is_published=True,
        )

        self.url = reverse("bookings:my_bookings")

    def test_unauthenticated_user_cannot_access_my_bookings(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("accounts:login"), response.url)

    def test_provider_cannot_access_customer_my_bookings(self):
        self.client.force_login(self.provider_user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 403)

    def test_customer_can_access_my_bookings(self):
        self.client.force_login(self.customer_a)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "bookings/my_bookings.html")

    def test_customer_only_sees_their_own_bookings(self):
        booking_a = Booking.objects.create(
            customer=self.customer_a,
            service=self.service,
            provider=self.provider,
            booking_date=date(2026, 8, 20),
            start_time=time(10, 0),
            end_time=time(11, 0),
            status=Booking.Status.PENDING,
        )
        booking_b = Booking.objects.create(
            customer=self.customer_b,
            service=self.service,
            provider=self.provider,
            booking_date=date(2026, 8, 21),
            start_time=time(14, 0),
            end_time=time(15, 0),
            status=Booking.Status.PENDING,
        )

        self.client.force_login(self.customer_a)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

        bookings = list(response.context["bookings"])
        self.assertIn(booking_a, bookings)
        self.assertNotIn(booking_b, bookings)

    def test_pending_filter_works(self):
        pending_b = Booking.objects.create(
            customer=self.customer_a,
            service=self.service,
            provider=self.provider,
            booking_date=date(2026, 8, 20),
            start_time=time(10, 0),
            end_time=time(11, 0),
            status=Booking.Status.PENDING,
        )
        confirmed_b = Booking.objects.create(
            customer=self.customer_a,
            service=self.service,
            provider=self.provider,
            booking_date=date(2026, 8, 21),
            start_time=time(11, 0),
            end_time=time(12, 0),
            status=Booking.Status.CONFIRMED,
        )

        self.client.force_login(self.customer_a)
        response = self.client.get(f"{self.url}?status=pending")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["current_status"], "pending")
        bookings = list(response.context["bookings"])
        self.assertIn(pending_b, bookings)
        self.assertNotIn(confirmed_b, bookings)

    def test_confirmed_filter_works(self):
        pending_b = Booking.objects.create(
            customer=self.customer_a,
            service=self.service,
            provider=self.provider,
            booking_date=date(2026, 8, 20),
            start_time=time(10, 0),
            end_time=time(11, 0),
            status=Booking.Status.PENDING,
        )
        confirmed_b = Booking.objects.create(
            customer=self.customer_a,
            service=self.service,
            provider=self.provider,
            booking_date=date(2026, 8, 21),
            start_time=time(11, 0),
            end_time=time(12, 0),
            status=Booking.Status.CONFIRMED,
        )

        self.client.force_login(self.customer_a)
        response = self.client.get(f"{self.url}?status=confirmed")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["current_status"], "confirmed")
        bookings = list(response.context["bookings"])
        self.assertIn(confirmed_b, bookings)
        self.assertNotIn(pending_b, bookings)

    def test_completed_filter_works(self):
        completed_b = Booking.objects.create(
            customer=self.customer_a,
            service=self.service,
            provider=self.provider,
            booking_date=date(2026, 8, 20),
            start_time=time(10, 0),
            end_time=time(11, 0),
            status=Booking.Status.COMPLETED,
        )
        cancelled_b = Booking.objects.create(
            customer=self.customer_a,
            service=self.service,
            provider=self.provider,
            booking_date=date(2026, 8, 21),
            start_time=time(11, 0),
            end_time=time(12, 0),
            status=Booking.Status.CANCELLED,
        )

        self.client.force_login(self.customer_a)
        response = self.client.get(f"{self.url}?status=completed")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["current_status"], "completed")
        bookings = list(response.context["bookings"])
        self.assertIn(completed_b, bookings)
        self.assertNotIn(cancelled_b, bookings)

    def test_cancelled_filter_works(self):
        completed_b = Booking.objects.create(
            customer=self.customer_a,
            service=self.service,
            provider=self.provider,
            booking_date=date(2026, 8, 20),
            start_time=time(10, 0),
            end_time=time(11, 0),
            status=Booking.Status.COMPLETED,
        )
        cancelled_b = Booking.objects.create(
            customer=self.customer_a,
            service=self.service,
            provider=self.provider,
            booking_date=date(2026, 8, 21),
            start_time=time(11, 0),
            end_time=time(12, 0),
            status=Booking.Status.CANCELLED,
        )

        self.client.force_login(self.customer_a)
        response = self.client.get(f"{self.url}?status=cancelled")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["current_status"], "cancelled")
        bookings = list(response.context["bookings"])
        self.assertIn(cancelled_b, bookings)
        self.assertNotIn(completed_b, bookings)

    def test_invalid_status_filter_does_not_crash(self):
        booking = Booking.objects.create(
            customer=self.customer_a,
            service=self.service,
            provider=self.provider,
            booking_date=date(2026, 8, 20),
            start_time=time(10, 0),
            end_time=time(11, 0),
            status=Booking.Status.PENDING,
        )

        self.client.force_login(self.customer_a)
        response = self.client.get(f"{self.url}?status=nonexistent_status_123")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["current_status"], "")
        self.assertIn(booking, list(response.context["bookings"]))

    def test_pagination_works(self):
        for i in range(15):
            Booking.objects.create(
                customer=self.customer_a,
                service=self.service,
                provider=self.provider,
                booking_date=date(2026, 8, 20),
                start_time=time(9 + (i % 8), 0),
                end_time=time(10 + (i % 8), 0),
                status=Booking.Status.PENDING,
            )

        self.client.force_login(self.customer_a)
        response_p1 = self.client.get(self.url)
        self.assertEqual(response_p1.status_code, 200)
        self.assertEqual(len(response_p1.context["bookings"]), 10)
        self.assertTrue(response_p1.context["page_obj"].has_next())

        response_p2 = self.client.get(f"{self.url}?page=2")
        self.assertEqual(response_p2.status_code, 200)
        self.assertEqual(len(response_p2.context["bookings"]), 5)
        self.assertTrue(response_p2.context["page_obj"].has_previous())

    def test_service_and_provider_information_displayed_on_list(self):
        Booking.objects.create(
            customer=self.customer_a,
            service=self.service,
            provider=self.provider,
            booking_date=date(2026, 8, 20),
            start_time=time(10, 0),
            end_time=time(11, 0),
            status=Booking.Status.PENDING,
        )

        self.client.force_login(self.customer_a)
        response = self.client.get(self.url)
        self.assertContains(response, "Premium Cleaning")
        self.assertContains(response, "Provia Home Care")
        self.assertContains(response, "1500.00")
        self.assertContains(response, "20 Aug 2026")
        self.assertContains(response, "10:00")
        self.assertContains(response, "11:00")

    def test_empty_states_work(self):
        self.client.force_login(self.customer_a)
        response_all = self.client.get(self.url)
        self.assertContains(response_all, "You haven't booked any services yet.")

        response_pending = self.client.get(f"{self.url}?status=pending")
        self.assertContains(response_pending, "You have no pending bookings.")

        response_confirmed = self.client.get(f"{self.url}?status=confirmed")
        self.assertContains(response_confirmed, "You have no confirmed bookings.")

        response_completed = self.client.get(f"{self.url}?status=completed")
        self.assertContains(response_completed, "You have no completed bookings.")

        response_cancelled = self.client.get(f"{self.url}?status=cancelled")
        self.assertContains(response_cancelled, "You have no cancelled bookings.")


class CustomerBookingDetailViewTests(TestCase):

    def setUp(self):
        self.provider_user = User.objects.create_user(
            username="det_provider",
            email="det_provider@example.com",
            password="StrongPassword123!",
            role=User.Role.PROVIDER,
            is_verified=True,
        )

        self.customer_a = User.objects.create_user(
            username="det_customer_a",
            email="det_customer_a@example.com",
            password="StrongPassword123!",
            role=User.Role.CUSTOMER,
            is_verified=True,
        )

        self.customer_b = User.objects.create_user(
            username="det_customer_b",
            email="det_customer_b@example.com",
            password="StrongPassword123!",
            role=User.Role.CUSTOMER,
            is_verified=True,
        )

        self.provider = ProviderProfile.objects.create(
            user=self.provider_user,
            business_name="Provia Care Pro",
            phone="9123456780",
            email="provider@carepro.com",
            city="Kochi",
            state="Kerala",
        )

        self.category = ServiceCategory.objects.create(
            name="Plumbing",
            slug="plumbing-pro",
            is_active=True,
        )

        self.service = Service.objects.create(
            provider=self.provider,
            category=self.category,
            title="Leak Repair",
            description="Pipe leak fix.",
            price=Decimal("800.00"),
            duration_minutes=45,
            is_published=True,
        )

        self.booking_a = Booking.objects.create(
            customer=self.customer_a,
            service=self.service,
            provider=self.provider,
            booking_date=date(2026, 8, 25),
            start_time=time(11, 0),
            end_time=time(11, 45),
            status=Booking.Status.PENDING,
            customer_notes="Please ring bell twice.",
        )

        self.booking_b = Booking.objects.create(
            customer=self.customer_b,
            service=self.service,
            provider=self.provider,
            booking_date=date(2026, 8, 26),
            start_time=time(15, 0),
            end_time=time(15, 45),
            status=Booking.Status.CONFIRMED,
        )

    def test_unauthenticated_cannot_access_booking_detail(self):
        url = reverse("bookings:detail", kwargs={"pk": self.booking_a.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("accounts:login"), response.url)

    def test_provider_cannot_access_customer_booking_detail(self):
        self.client.force_login(self.provider_user)
        url = reverse("bookings:detail", kwargs={"pk": self.booking_a.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)

    def test_customer_can_view_their_own_booking_detail(self):
        self.client.force_login(self.customer_a)
        url = reverse("bookings:detail", kwargs={"pk": self.booking_a.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "bookings/detail.html")
        self.assertEqual(response.context["booking"], self.booking_a)
        self.assertContains(response, "Leak Repair")
        self.assertContains(response, "Provia Care Pro")
        self.assertContains(response, "9123456780")
        self.assertContains(response, "provider@carepro.com")
        self.assertContains(response, "800.00")
        self.assertContains(response, "Please ring bell twice.")
        self.assertContains(response, "Pending")
        self.assertContains(
            response,
            reverse("payments:checkout", kwargs={"booking_id": self.booking_a.pk}),
        )

    def test_customer_cannot_view_another_customers_booking_detail(self):
        self.client.force_login(self.customer_a)
        url = reverse("bookings:detail", kwargs={"pk": self.booking_b.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_draft_or_unpublished_service_does_not_break_booking_detail(self):
        self.service.is_published = False
        self.service.save()

        self.client.force_login(self.customer_a)
        url = reverse("bookings:detail", kwargs={"pk": self.booking_a.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Leak Repair")

    def test_booking_detail_shows_successful_payment_action(self):
        payment = Payment.objects.create(
            booking=self.booking_a,
            amount=self.booking_a.total_amount,
            currency="INR",
            status=Payment.Status.SUCCESS,
            payment_reference="PRV-SUCCESS-TEST",
        )

        self.booking_a.status = Booking.Status.CONFIRMED
        self.booking_a.save(update_fields=["status"])

        self.client.force_login(self.customer_a)
        url = reverse("bookings:detail", kwargs={"pk": self.booking_a.pk})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            reverse("payments:detail", kwargs={"payment_id": payment.pk}),
        )
        self.assertContains(response, "View Payment")

    def test_booking_detail_shows_initiated_payment_action(self):
        Payment.objects.create(
            booking=self.booking_a,
            amount=self.booking_a.total_amount,
            currency="INR",
            status=Payment.Status.INITIATED,
            payment_reference="PRV-INITIATED-TEST",
        )

        self.client.force_login(self.customer_a)
        url = reverse("bookings:detail", kwargs={"pk": self.booking_a.pk})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Continue Payment")
        self.assertContains(
            response,
            reverse("payments:checkout", kwargs={"booking_id": self.booking_a.pk}),
        )

    def test_booking_detail_does_not_show_pay_now_for_failed_payment(self):
        Payment.objects.create(
            booking=self.booking_a,
            amount=self.booking_a.total_amount,
            currency="INR",
            status=Payment.Status.FAILED,
            payment_reference="PRV-FAILED-TEST",
        )

        self.client.force_login(self.customer_a)
        url = reverse("bookings:detail", kwargs={"pk": self.booking_a.pk})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Pay Now")


class ProviderBookingManagementTests(TestCase):

    def setUp(self):
        self.provider_user_1 = User.objects.create_user(
            username="provider1",
            email="p1@example.com",
            password="StrongPassword123!",
            role=User.Role.PROVIDER,
            is_verified=True,
        )

        self.provider_user_2 = User.objects.create_user(
            username="provider2",
            email="p2@example.com",
            password="StrongPassword123!",
            role=User.Role.PROVIDER,
            is_verified=True,
        )

        self.customer = User.objects.create_user(
            username="customer_pbm",
            email="cust_pbm@example.com",
            password="StrongPassword123!",
            role=User.Role.CUSTOMER,
            is_verified=True,
        )

        self.provider_1 = ProviderProfile.objects.create(
            user=self.provider_user_1,
            business_name="Provider One Services",
        )

        self.provider_2 = ProviderProfile.objects.create(
            user=self.provider_user_2,
            business_name="Provider Two Services",
        )

        self.category = ServiceCategory.objects.create(
            name="Electrical",
            slug="electrical",
            is_active=True,
        )

        self.service_1 = Service.objects.create(
            provider=self.provider_1,
            category=self.category,
            title="Wiring Check",
            description="Electrical inspection",
            price=Decimal("1200.00"),
            duration_minutes=60,
            is_published=True,
        )

        self.service_2 = Service.objects.create(
            provider=self.provider_2,
            category=self.category,
            title="Appliance Fix",
            description="Fix appliances",
            price=Decimal("1500.00"),
            duration_minutes=60,
            is_published=True,
        )

        self.booking_1 = Booking.objects.create(
            customer=self.customer,
            service=self.service_1,
            provider=self.provider_1,
            booking_date=date(2026, 8, 28),
            start_time=time(10, 0),
            end_time=time(11, 0),
            status=Booking.Status.PENDING,
        )

        self.booking_2 = Booking.objects.create(
            customer=self.customer,
            service=self.service_2,
            provider=self.provider_2,
            booking_date=date(2026, 8, 28),
            start_time=time(14, 0),
            end_time=time(15, 0),
            status=Booking.Status.PENDING,
        )

    def test_provider_sees_own_bookings(self):
        self.client.force_login(self.provider_user_1)
        url = reverse("bookings:provider_bookings")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Wiring Check")
        self.assertNotIn("Appliance Fix", response.content.decode())

    def test_provider_cannot_see_another_providers_bookings(self):
        self.client.force_login(self.provider_user_1)
        url = reverse("bookings:provider_bookings")
        response = self.client.get(url)
        bookings = list(response.context["bookings"])
        self.assertIn(self.booking_1, bookings)
        self.assertNotIn(self.booking_2, bookings)

    def test_provider_can_view_own_booking_detail(self):
        self.client.force_login(self.provider_user_1)
        url = reverse("bookings:provider_detail", kwargs={"pk": self.booking_1.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Wiring Check")

    def test_provider_cannot_view_another_providers_booking_detail(self):
        self.client.force_login(self.provider_user_1)
        url = reverse("bookings:provider_detail", kwargs={"pk": self.booking_2.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_provider_bookings_status_filter_and_pagination(self):
        self.client.force_login(self.provider_user_1)
        url = reverse("bookings:provider_bookings")
        response = self.client.get(f"{url}?status=pending")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["current_status"], "pending")


class ProviderStatusTransitionTests(TestCase):

    def setUp(self):
        self.provider_user = User.objects.create_user(
            username="status_provider",
            email="sp@example.com",
            password="StrongPassword123!",
            role=User.Role.PROVIDER,
            is_verified=True,
        )

        self.customer = User.objects.create_user(
            username="status_customer",
            email="sc@example.com",
            password="StrongPassword123!",
            role=User.Role.CUSTOMER,
            is_verified=True,
        )

        self.provider = ProviderProfile.objects.create(
            user=self.provider_user,
            business_name="Status Test Care",
        )

        self.category = ServiceCategory.objects.create(
            name="Carpentry",
            slug="carpentry-status",
            is_active=True,
        )

        self.service = Service.objects.create(
            provider=self.provider,
            category=self.category,
            title="Wood Polish",
            description="Polishing service",
            price=Decimal("2000.00"),
            duration_minutes=120,
            is_published=True,
        )

        self.booking = Booking.objects.create(
            customer=self.customer,
            service=self.service,
            provider=self.provider,
            booking_date=future_date(11),
            start_time=time(10, 0),
            end_time=time(12, 0),
            status=Booking.Status.PENDING,
        )

    def test_pending_to_confirmed_works(self):
        self.client.force_login(self.provider_user)
        url = reverse("bookings:update_status", kwargs={"pk": self.booking.pk})
        response = self.client.post(
            url, {"status": "confirmed", "provider_notes": "Confirmed schedule."}
        )
        self.assertRedirects(
            response,
            reverse("bookings:provider_detail", kwargs={"pk": self.booking.pk}),
        )
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.status, Booking.Status.CONFIRMED)
        self.assertEqual(self.booking.provider_notes, "Confirmed schedule.")

    def test_pending_to_cancelled_works(self):
        self.client.force_login(self.provider_user)
        url = reverse("bookings:update_status", kwargs={"pk": self.booking.pk})
        response = self.client.post(
            url, {"status": "cancelled", "provider_notes": "Unavailable on this day."}
        )
        self.assertRedirects(
            response,
            reverse("bookings:provider_detail", kwargs={"pk": self.booking.pk}),
        )
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.status, Booking.Status.CANCELLED)

    def test_confirmed_to_completed_works(self):
        self.booking.status = Booking.Status.CONFIRMED
        self.booking.save()

        self.client.force_login(self.provider_user)
        url = reverse("bookings:update_status", kwargs={"pk": self.booking.pk})
        response = self.client.post(
            url, {"status": "completed", "provider_notes": "Work done."}
        )
        self.assertRedirects(
            response,
            reverse("bookings:provider_detail", kwargs={"pk": self.booking.pk}),
        )
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.status, Booking.Status.COMPLETED)

    def test_confirmed_to_cancelled_works(self):
        self.booking.status = Booking.Status.CONFIRMED
        self.booking.save()

        self.client.force_login(self.provider_user)
        url = reverse("bookings:update_status", kwargs={"pk": self.booking.pk})
        response = self.client.post(
            url, {"status": "cancelled", "provider_notes": "Emergency cancel."}
        )
        self.assertRedirects(
            response,
            reverse("bookings:provider_detail", kwargs={"pk": self.booking.pk}),
        )
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.status, Booking.Status.CANCELLED)

    def test_invalid_status_transitions_rejected(self):
        # COMPLETED -> CONFIRMED ❌
        self.booking.status = Booking.Status.COMPLETED
        self.booking.save()

        self.client.force_login(self.provider_user)
        url = reverse("bookings:update_status", kwargs={"pk": self.booking.pk})
        response = self.client.post(url, {"status": "confirmed"})
        self.assertEqual(response.status_code, 200)
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.status, Booking.Status.COMPLETED)

        # CANCELLED -> CONFIRMED ❌
        self.booking.status = Booking.Status.CANCELLED
        self.booking.save()

        response = self.client.post(url, {"status": "confirmed"})
        self.assertEqual(response.status_code, 200)
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.status, Booking.Status.CANCELLED)

        # COMPLETED -> CANCELLED ❌
        self.booking.status = Booking.Status.COMPLETED
        self.booking.save()

        response = self.client.post(url, {"status": "cancelled"})
        self.assertEqual(response.status_code, 200)
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.status, Booking.Status.COMPLETED)


class CustomerCancellationTests(TestCase):

    def setUp(self):
        self.provider_user = User.objects.create_user(
            username="cancel_provider",
            email="cp@example.com",
            password="StrongPassword123!",
            role=User.Role.PROVIDER,
            is_verified=True,
        )

        self.customer_1 = User.objects.create_user(
            username="canceller_1",
            email="c1@example.com",
            password="StrongPassword123!",
            role=User.Role.CUSTOMER,
            is_verified=True,
        )

        self.customer_2 = User.objects.create_user(
            username="canceller_2",
            email="c2@example.com",
            password="StrongPassword123!",
            role=User.Role.CUSTOMER,
            is_verified=True,
        )

        self.provider = ProviderProfile.objects.create(
            user=self.provider_user,
            business_name="Cancellation Test Pro",
        )

        self.category = ServiceCategory.objects.create(
            name="Gardening",
            slug="gardening-cancel",
            is_active=True,
        )

        self.service = Service.objects.create(
            provider=self.provider,
            category=self.category,
            title="Lawn Mowing",
            description="Lawn care",
            price=Decimal("500.00"),
            duration_minutes=60,
            is_published=True,
        )

        # Provider availability on Thursday (weekday 3)
        self.booking_date = date(2026, 8, 27)

        ProviderAvailability.objects.create(
            provider=self.provider,
            weekday=self.booking_date.weekday(),
            start_time=time(9, 0),
            end_time=time(17, 0),
            is_active=True,
        )

        self.booking = Booking.objects.create(
            customer=self.customer_1,
            service=self.service,
            provider=self.provider,
            booking_date=self.booking_date,
            start_time=time(10, 0),
            end_time=time(11, 0),
            status=Booking.Status.PENDING,
        )

    def test_customer_can_cancel_own_pending_booking(self):
        self.client.force_login(self.customer_1)
        url = reverse("bookings:cancel", kwargs={"pk": self.booking.pk})
        response = self.client.post(url)
        self.assertRedirects(
            response, reverse("bookings:detail", kwargs={"pk": self.booking.pk})
        )
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.status, Booking.Status.CANCELLED)

    def test_customer_can_cancel_own_confirmed_booking(self):
        self.booking.status = Booking.Status.CONFIRMED
        self.booking.save()

        self.client.force_login(self.customer_1)
        url = reverse("bookings:cancel", kwargs={"pk": self.booking.pk})
        response = self.client.post(url)
        self.assertRedirects(
            response, reverse("bookings:detail", kwargs={"pk": self.booking.pk})
        )
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.status, Booking.Status.CANCELLED)

    def test_customer_cannot_cancel_another_customers_booking(self):
        self.client.force_login(self.customer_2)
        url = reverse("bookings:cancel", kwargs={"pk": self.booking.pk})
        response = self.client.post(url)
        self.assertEqual(response.status_code, 404)
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.status, Booking.Status.PENDING)

    def test_completed_booking_cannot_be_cancelled(self):
        self.booking.status = Booking.Status.COMPLETED
        self.booking.save()

        self.client.force_login(self.customer_1)
        url = reverse("bookings:cancel", kwargs={"pk": self.booking.pk})
        response = self.client.post(url)
        self.assertRedirects(
            response, reverse("bookings:detail", kwargs={"pk": self.booking.pk})
        )
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.status, Booking.Status.COMPLETED)

    def test_cancelled_booking_cannot_be_cancelled_again(self):
        self.booking.status = Booking.Status.CANCELLED
        self.booking.save()

        self.client.force_login(self.customer_1)
        url = reverse("bookings:cancel", kwargs={"pk": self.booking.pk})
        response = self.client.post(url)
        self.assertRedirects(
            response, reverse("bookings:detail", kwargs={"pk": self.booking.pk})
        )
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.status, Booking.Status.CANCELLED)

    def test_cancelled_slot_becomes_available(self):
        # Before cancellation, 10:00 slot is occupied
        slots_before = get_available_slots(self.service, date(2026, 8, 27))
        self.assertNotIn(time(10, 0), [s["start_time"] for s in slots_before])

        # Cancel booking
        self.client.force_login(self.customer_1)
        url = reverse("bookings:cancel", kwargs={"pk": self.booking.pk})
        self.client.post(url)

        # After cancellation, 10:00 slot becomes available again
        slots_after = get_available_slots(self.service, date(2026, 8, 27))
        self.assertIn(time(10, 0), [s["start_time"] for s in slots_after])


class ConcurrencyAndSecurityTests(TestCase):

    def setUp(self):
        self.provider_user = User.objects.create_user(
            username="sec_provider",
            email="secp@example.com",
            password="StrongPassword123!",
            role=User.Role.PROVIDER,
            is_verified=True,
        )

        self.customer_1 = User.objects.create_user(
            username="sec_customer1",
            email="secc1@example.com",
            password="StrongPassword123!",
            role=User.Role.CUSTOMER,
            is_verified=True,
        )

        self.customer_2 = User.objects.create_user(
            username="sec_customer2",
            email="secc2@example.com",
            password="StrongPassword123!",
            role=User.Role.CUSTOMER,
            is_verified=True,
        )

        self.provider = ProviderProfile.objects.create(
            user=self.provider_user,
            business_name="Security Pro Services",
        )

        self.category = ServiceCategory.objects.create(
            name="Security",
            slug="security-test",
            is_active=True,
        )

        self.service = Service.objects.create(
            provider=self.provider,
            category=self.category,
            title="CCTV Setup",
            description="CCTV installation",
            price=Decimal("3000.00"),
            duration_minutes=60,
            is_published=True,
        )

        ProviderAvailability.objects.create(
            provider=self.provider,
            weekday=3,  # Thursday
            start_time=time(9, 0),
            end_time=time(17, 0),
            is_active=True,
        )

    def test_duplicate_active_booking_rejected(self):
        b1 = create_booking(
            customer=self.customer_1,
            service=self.service,
            booking_date=date(2026, 8, 27),
            start_time=time(10, 0),
        )
        self.assertIsNotNone(b1)

        with self.assertRaises(ValidationError):
            create_booking(
                customer=self.customer_2,
                service=self.service,
                booking_date=date(2026, 8, 27),
                start_time=time(10, 0),
            )

    def test_slot_revalidated_before_save(self):
        # Attempting to book a slot that overlaps with an existing booking raises ValidationError
        Booking.objects.create(
            customer=self.customer_1,
            service=self.service,
            provider=self.provider,
            booking_date=date(2026, 8, 27),
            start_time=time(10, 0),
            end_time=time(11, 0),
            status=Booking.Status.CONFIRMED,
        )

        with self.assertRaises(ValidationError):
            create_booking(
                customer=self.customer_2,
                service=self.service,
                booking_date=date(2026, 8, 27),
                start_time=time(10, 0),
            )

    def test_customer_cannot_modify_provider_or_status_via_booking_create(self):
        self.client.force_login(self.customer_1)
        url = reverse("bookings:create", kwargs={"service_id": self.service.id})
        post_data = {
            "booking_date": "2026-08-27",
            "start_time": "11:00",
            "customer_notes": "Note",
            "status": "confirmed",  # Tamper attempt
            "provider": 9999,  # Tamper attempt
            "end_time": "15:00",  # Tamper attempt
        }
        response = self.client.post(url, post_data)
        self.assertEqual(response.status_code, 302)
        booking = Booking.objects.get(
            customer=self.customer_1, booking_date=date(2026, 8, 27)
        )
        self.assertEqual(booking.status, Booking.Status.PENDING)
        self.assertEqual(booking.provider, self.provider)
        self.assertEqual(booking.end_time, time(12, 0))

    def test_provider_cannot_modify_customer_or_service(self):
        booking = Booking.objects.create(
            customer=self.customer_1,
            service=self.service,
            provider=self.provider,
            booking_date=date(2026, 8, 27),
            start_time=time(12, 0),
            end_time=time(13, 0),
            status=Booking.Status.PENDING,
        )

        self.client.force_login(self.provider_user)
        url = reverse("bookings:update_status", kwargs={"pk": booking.pk})
        post_data = {
            "status": "confirmed",
            "customer": self.customer_2.id,  # Tamper attempt
            "service": 999,  # Tamper attempt
        }
        self.client.post(url, post_data)
        booking.refresh_from_db()
        self.assertEqual(booking.status, Booking.Status.CONFIRMED)
        self.assertEqual(booking.customer, self.customer_1)
        self.assertEqual(booking.service, self.service)


class BookingChatEntryTests(TestCase):

    def setUp(self):
        self.provider_user = User.objects.create_user(
            username="chatprovider",
            email="chatprovider@example.com",
            password="StrongPassword123!",
            role=User.Role.PROVIDER,
            is_verified=True,
        )

        self.other_provider_user = User.objects.create_user(
            username="otherprovider",
            email="otherprovider@example.com",
            password="StrongPassword123!",
            role=User.Role.PROVIDER,
            is_verified=True,
        )

        self.customer = User.objects.create_user(
            username="chatcustomer",
            email="chatcustomer@example.com",
            password="StrongPassword123!",
            role=User.Role.CUSTOMER,
            is_verified=True,
        )

        self.other_customer = User.objects.create_user(
            username="othercustomer",
            email="othercustomer@example.com",
            password="StrongPassword123!",
            role=User.Role.CUSTOMER,
            is_verified=True,
        )

        self.provider = ProviderProfile.objects.create(
            user=self.provider_user,
            business_name="Chat Provider",
        )

        self.other_provider = ProviderProfile.objects.create(
            user=self.other_provider_user,
            business_name="Other Provider",
        )

        self.category = ServiceCategory.objects.create(
            name="Plumbing",
            slug="chat-plumbing",
            is_active=True,
        )

        self.service = Service.objects.create(
            provider=self.provider,
            category=self.category,
            title="Pipe Repair",
            description="Fix leaky pipes.",
            price=Decimal("1500.00"),
            duration_minutes=60,
            is_published=True,
        )

        self.booking = Booking.objects.create(
            customer=self.customer,
            service=self.service,
            provider=self.provider,
            booking_date=date(2026, 9, 1),
            start_time=time(10, 0),
            end_time=time(11, 0),
            status=Booking.Status.CONFIRMED,
        )

        self.url = reverse(
            "bookings:chat",
            kwargs={"pk": self.booking.pk},
        )

    def test_customer_can_open_chat_for_their_booking(self):
        self.client.force_login(self.customer)
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, 302)

        from chat.models import Conversation
        conversation = Conversation.objects.get(booking=self.booking)
        self.assertEqual(conversation.customer, self.customer)
        self.assertEqual(conversation.provider, self.provider)
        expected_redirect = reverse(
            "chat:conversation",
            kwargs={"conversation_id": conversation.pk},
        )
        self.assertRedirects(response, expected_redirect)

    def test_provider_can_open_chat_for_their_booking(self):
        self.client.force_login(self.provider_user)
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, 302)

        from chat.models import Conversation
        conversation = Conversation.objects.get(booking=self.booking)
        expected_redirect = reverse(
            "chat:conversation",
            kwargs={"conversation_id": conversation.pk},
        )
        self.assertRedirects(response, expected_redirect)

    def test_customer_and_provider_resolve_to_same_conversation(self):
        self.client.force_login(self.customer)
        resp1 = self.client.post(self.url)
        from chat.models import Conversation
        conv1 = Conversation.objects.get(booking=self.booking)

        self.client.force_login(self.provider_user)
        resp2 = self.client.post(self.url)
        conv2 = Conversation.objects.get(booking=self.booking)

        self.assertEqual(conv1.pk, conv2.pk)
        self.assertEqual(Conversation.objects.filter(booking=self.booking).count(), 1)
        expected_redirect = reverse(
            "chat:conversation",
            kwargs={"conversation_id": conv1.pk},
        )
        self.assertRedirects(resp1, expected_redirect)
        self.assertRedirects(resp2, expected_redirect)

    def test_unauthenticated_user_cannot_access_booking_chat(self):
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response.url)
        from chat.models import Conversation
        self.assertFalse(Conversation.objects.filter(booking=self.booking).exists())

    def test_customer_cannot_open_another_customers_booking_chat(self):
        self.client.force_login(self.other_customer)
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, 403)
        from chat.models import Conversation
        self.assertFalse(Conversation.objects.filter(booking=self.booking).exists())

    def test_provider_cannot_open_another_providers_booking_chat(self):
        self.client.force_login(self.other_provider_user)
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, 403)
        from chat.models import Conversation
        self.assertFalse(Conversation.objects.filter(booking=self.booking).exists())

    def test_get_method_not_accepted_for_booking_chat(self):
        self.client.force_login(self.customer)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 405)
        from chat.models import Conversation
        self.assertFalse(Conversation.objects.filter(booking=self.booking).exists())

    def test_csrf_behavior_remains_correct(self):
        from django.test import Client
        csrf_client = Client(enforce_csrf_checks=True)
        csrf_client.force_login(self.customer)
        response = csrf_client.post(self.url)
        self.assertEqual(response.status_code, 403)

    def test_calling_endpoint_twice_does_not_create_second_conversation(self):
        self.client.force_login(self.customer)
        resp1 = self.client.post(self.url)
        from chat.models import Conversation
        conv1 = Conversation.objects.get(booking=self.booking)

        resp2 = self.client.post(self.url)
        conv2 = Conversation.objects.get(booking=self.booking)

        self.assertEqual(conv1.pk, conv2.pk)
        self.assertEqual(Conversation.objects.filter(booking=self.booking).count(), 1)


