from datetime import date, datetime, time, timedelta
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import User
from bookings.models import Booking
from notifications.models import Notification
from payments.models import Payment
from providers.models import ProviderProfile
from reviews.models import Review
from services.models import Service, ServiceCategory


class CustomerDashboardTests(TestCase):

    def setUp(self):
        self.customer = User.objects.create_user(
            username="dash_customer",
            email="dash_customer@example.com",
            password="StrongPassword123!",
            role=User.Role.CUSTOMER,
            is_verified=True,
        )

        self.other_customer = User.objects.create_user(
            username="other_customer",
            email="other_customer@example.com",
            password="StrongPassword123!",
            role=User.Role.CUSTOMER,
            is_verified=True,
        )

        self.provider_user = User.objects.create_user(
            username="dash_provider",
            email="dash_provider@example.com",
            password="StrongPassword123!",
            role=User.Role.PROVIDER,
            is_verified=True,
        )

        self.other_provider_user = User.objects.create_user(
            username="other_provider",
            email="other_provider@example.com",
            password="StrongPassword123!",
            role=User.Role.PROVIDER,
            is_verified=True,
        )

        self.provider = ProviderProfile.objects.create(
            user=self.provider_user,
            business_name="Dashboard Services",
            email="provider@example.com",
        )

        self.other_provider = ProviderProfile.objects.create(
            user=self.other_provider_user,
            business_name="Other Services",
            email="other_provider@example.com",
        )

        self.category = ServiceCategory.objects.create(
            name="Home Services",
            slug="home-services",
        )

        self.service = Service.objects.create(
            provider=self.provider,
            category=self.category,
            title="Home Cleaning",
            description="Professional home cleaning service.",
            price=Decimal("1500.00"),
            duration_minutes=120,
            is_published=True,
        )

        self.other_service = Service.objects.create(
            provider=self.other_provider,
            category=self.category,
            title="Other Cleaning",
            description="Another cleaning service.",
            price=Decimal("2000.00"),
            duration_minutes=90,
            is_published=True,
        )

    def create_booking(
        self,
        *,
        customer=None,
        service=None,
        booking_date=None,
        start_time_value=time(10, 0),
        status=Booking.Status.PENDING,
        total_amount=None,
    ):
        customer = customer or self.customer
        service = service or self.service
        booking_date = booking_date or timezone.localdate()
        end_time_value = (
            datetime.combine(
                booking_date,
                start_time_value,
            )
            + timedelta(hours=1)
        ).time()

        return Booking.objects.create(
            customer=customer,
            service=service,
            provider=service.provider,
            booking_date=booking_date,
            start_time=start_time_value,
            end_time=end_time_value,
            status=status,
            total_amount=(total_amount if total_amount is not None else service.price),
        )

    def create_payment(
        self,
        booking,
        *,
        status=Payment.Status.SUCCESS,
        amount=None,
        payment_reference=None,
    ):
        return Payment.objects.create(
            booking=booking,
            amount=(amount if amount is not None else booking.total_amount),
            currency="INR",
            status=status,
            payment_reference=payment_reference,
        )

    def test_customer_dashboard_renders_my_bookings_link(self):
        self.client.force_login(self.customer)

        response = self.client.get(
            reverse("dashboard:customer"),
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            reverse("bookings:my_bookings"),
        )
        self.assertContains(response, "My Bookings")

    def test_unauthenticated_cannot_access_customer_dashboard(self):
        response = self.client.get(
            reverse("dashboard:customer"),
        )

        self.assertEqual(response.status_code, 302)

    def test_provider_cannot_access_customer_dashboard(self):
        self.client.force_login(self.provider_user)

        response = self.client.get(
            reverse("dashboard:customer"),
        )

        self.assertEqual(response.status_code, 403)

    def test_customer_dashboard_booking_counts(self):
        self.create_booking(
            status=Booking.Status.PENDING,
        )
        self.create_booking(
            status=Booking.Status.CONFIRMED,
        )
        self.create_booking(
            status=Booking.Status.COMPLETED,
        )
        self.create_booking(
            status=Booking.Status.CANCELLED,
        )

        self.client.force_login(self.customer)

        response = self.client.get(
            reverse("dashboard:customer"),
        )

        self.assertEqual(response.context["total_bookings"], 4)
        self.assertEqual(response.context["pending_bookings"], 1)
        self.assertEqual(response.context["confirmed_bookings"], 1)
        self.assertEqual(response.context["completed_bookings"], 1)
        self.assertEqual(response.context["cancelled_bookings"], 1)

    def test_customer_dashboard_upcoming_bookings(self):
        today = timezone.localdate()

        future_booking = self.create_booking(
            booking_date=today + timedelta(days=2),
            start_time_value=time(11, 0),
        )

        today_future_booking = self.create_booking(
            booking_date=today,
            start_time_value=time(23, 0),
        )

        self.create_booking(
            booking_date=today - timedelta(days=1),
            start_time_value=time(11, 0),
        )

        self.client.force_login(self.customer)

        response = self.client.get(
            reverse("dashboard:customer"),
        )

        upcoming = list(
            response.context["upcoming_bookings"],
        )

        self.assertEqual(len(upcoming), 2)
        self.assertEqual(upcoming[0], today_future_booking)
        self.assertEqual(upcoming[1], future_booking)

    def test_customer_dashboard_upcoming_bookings_are_limited_to_five(self):
        today = timezone.localdate()

        for offset in range(1, 8):
            self.create_booking(
                booking_date=today + timedelta(days=offset),
                start_time_value=time(10, 0),
            )

        self.client.force_login(self.customer)

        response = self.client.get(
            reverse("dashboard:customer"),
        )

        upcoming = list(
            response.context["upcoming_bookings"],
        )

        self.assertEqual(len(upcoming), 5)

    def test_customer_dashboard_recent_bookings(self):
        older_booking = self.create_booking(
            booking_date=timezone.localdate() - timedelta(days=2),
        )

        newer_booking = self.create_booking(
            booking_date=timezone.localdate() - timedelta(days=1),
        )

        self.client.force_login(self.customer)

        response = self.client.get(
            reverse("dashboard:customer"),
        )

        recent = list(
            response.context["recent_bookings"],
        )

        self.assertEqual(
            recent[:2],
            [
                newer_booking,
                older_booking,
            ],
        )

    def test_customer_dashboard_recent_bookings_are_limited_to_five(self):
        for offset in range(1, 8):
            self.create_booking(
                booking_date=timezone.localdate() - timedelta(days=offset),
            )

        self.client.force_login(self.customer)

        response = self.client.get(
            reverse("dashboard:customer"),
        )

        recent = list(
            response.context["recent_bookings"],
        )

        self.assertEqual(len(recent), 5)

    def test_customer_dashboard_recent_payments(self):
        older_booking = self.create_booking(
            booking_date=timezone.localdate() - timedelta(days=2),
        )

        newer_booking = self.create_booking(
            booking_date=timezone.localdate() - timedelta(days=1),
        )

        older_payment = self.create_payment(
            older_booking,
            payment_reference="PAY-OLDER",
        )

        newer_payment = self.create_payment(
            newer_booking,
            payment_reference="PAY-NEWER",
        )

        self.client.force_login(self.customer)

        response = self.client.get(
            reverse("dashboard:customer"),
        )

        recent_payments = list(
            response.context["recent_payments"],
        )

        self.assertEqual(
            recent_payments[:2],
            [
                newer_payment,
                older_payment,
            ],
        )

    def test_customer_dashboard_recent_payments_are_limited_to_five(self):
        for index in range(7):
            booking = self.create_booking(
                booking_date=timezone.localdate() - timedelta(days=index + 1),
            )

            self.create_payment(
                booking,
                payment_reference=f"PAY-{index}",
            )

        self.client.force_login(self.customer)

        response = self.client.get(
            reverse("dashboard:customer"),
        )

        recent_payments = list(
            response.context["recent_payments"],
        )

        self.assertEqual(len(recent_payments), 5)

    def test_customer_dashboard_review_summary(self):
        first_booking = self.create_booking(
            booking_date=timezone.localdate() - timedelta(days=5),
            status=Booking.Status.COMPLETED,
        )

        second_booking = self.create_booking(
            booking_date=timezone.localdate() - timedelta(days=4),
            status=Booking.Status.COMPLETED,
        )

        Review.objects.create(
            booking=first_booking,
            customer=self.customer,
            service=first_booking.service,
            provider=first_booking.provider,
            rating=4,
            comment="Very good service.",
        )

        Review.objects.create(
            booking=second_booking,
            customer=self.customer,
            service=second_booking.service,
            provider=second_booking.provider,
            rating=5,
            comment="Excellent service.",
        )

        self.client.force_login(self.customer)

        response = self.client.get(
            reverse("dashboard:customer"),
        )

        review_summary = response.context["review_summary"]

        self.assertEqual(review_summary["review_count"], 2)
        self.assertEqual(
            review_summary["average_rating"],
            Decimal("4.5"),
        )

    def test_customer_dashboard_review_summary_empty(self):
        self.client.force_login(self.customer)

        response = self.client.get(
            reverse("dashboard:customer"),
        )

        review_summary = response.context["review_summary"]

        self.assertEqual(review_summary["review_count"], 0)
        self.assertIsNone(
            review_summary["average_rating"],
        )

    def test_customer_dashboard_unread_notification_count(self):
        Notification.objects.create(
            recipient=self.customer,
            notification_type=(Notification.NotificationType.BOOKING_CONFIRMED),
            title="Booking Confirmed",
            message="Your booking has been confirmed.",
            is_read=False,
        )

        Notification.objects.create(
            recipient=self.customer,
            notification_type=(Notification.NotificationType.PAYMENT_SUCCESS),
            title="Payment Successful",
            message="Your payment was successful.",
            is_read=False,
        )

        Notification.objects.create(
            recipient=self.customer,
            notification_type=(Notification.NotificationType.BOOKING_COMPLETED),
            title="Booking Completed",
            message="Your booking is complete.",
            is_read=True,
        )

        self.client.force_login(self.customer)

        response = self.client.get(
            reverse("dashboard:customer"),
        )

        self.assertEqual(
            response.context["unread_notification_count"],
            2,
        )

    def test_customer_dashboard_is_empty_for_customer_without_data(self):
        self.client.force_login(self.customer)

        response = self.client.get(
            reverse("dashboard:customer"),
        )

        self.assertEqual(
            response.context["total_bookings"],
            0,
        )
        self.assertEqual(
            response.context["pending_bookings"],
            0,
        )
        self.assertEqual(
            response.context["confirmed_bookings"],
            0,
        )
        self.assertEqual(
            response.context["completed_bookings"],
            0,
        )
        self.assertEqual(
            response.context["cancelled_bookings"],
            0,
        )
        self.assertEqual(
            list(response.context["upcoming_bookings"]),
            [],
        )
        self.assertEqual(
            list(response.context["recent_bookings"]),
            [],
        )
        self.assertEqual(
            list(response.context["recent_payments"]),
            [],
        )
        self.assertEqual(
            response.context["review_summary"]["review_count"],
            0,
        )
        self.assertIsNone(
            response.context["review_summary"]["average_rating"],
        )
        self.assertEqual(
            response.context["unread_notification_count"],
            0,
        )

    def test_customer_dashboard_never_exposes_another_customers_data(self):
        own_booking = self.create_booking(
            customer=self.customer,
            booking_date=timezone.localdate() - timedelta(days=1),
        )

        other_booking = self.create_booking(
            customer=self.other_customer,
            service=self.other_service,
            booking_date=timezone.localdate() - timedelta(days=2),
        )

        self.create_payment(
            own_booking,
            payment_reference="PAY-OWN",
        )

        self.create_payment(
            other_booking,
            payment_reference="PAY-OTHER",
        )

        Review.objects.create(
            booking=own_booking,
            customer=self.customer,
            service=own_booking.service,
            provider=own_booking.provider,
            rating=5,
            comment="Own review.",
        )

        Review.objects.create(
            booking=other_booking,
            customer=self.other_customer,
            service=other_booking.service,
            provider=other_booking.provider,
            rating=1,
            comment="Other customer's review.",
        )

        self.client.force_login(self.customer)

        response = self.client.get(
            reverse("dashboard:customer"),
        )

        recent_bookings = list(
            response.context["recent_bookings"],
        )

        recent_payments = list(
            response.context["recent_payments"],
        )

        review_summary = response.context["review_summary"]

        self.assertEqual(
            recent_bookings,
            [own_booking],
        )

        self.assertEqual(
            recent_payments[0].booking,
            own_booking,
        )

        self.assertEqual(
            review_summary["review_count"],
            1,
        )
        self.assertEqual(
            review_summary["average_rating"],
            Decimal("5"),
        )

    def test_customer_dashboard_query_count(self):
        self.create_booking()
        self.create_payment(self.create_booking())
        Review.objects.create(
            booking=self.create_booking(status=Booking.Status.COMPLETED),
            customer=self.customer,
            service=self.service,
            provider=self.provider,
            rating=4,
            comment="Good.",
        )

        self.client.force_login(self.customer)

        with self.assertNumQueries(7):
            self.client.get(reverse("dashboard:customer"))


class ProviderDashboardTests(TestCase):

    def setUp(self):
        self.provider_user = User.objects.create_user(
            username="dash_provider",
            email="dash_provider@example.com",
            password="StrongPassword123!",
            role=User.Role.PROVIDER,
            is_verified=True,
        )

        self.other_provider_user = User.objects.create_user(
            username="other_provider",
            email="other_provider@example.com",
            password="StrongPassword123!",
            role=User.Role.PROVIDER,
            is_verified=True,
        )

        self.provider = ProviderProfile.objects.create(
            user=self.provider_user,
            business_name="Dashboard Services",
            email="provider@example.com",
        )

        self.other_provider = ProviderProfile.objects.create(
            user=self.other_provider_user,
            business_name="Other Services",
            email="other_provider@example.com",
        )

        self.category = ServiceCategory.objects.create(
            name="Home Services",
            slug="home-services",
        )

        self.service = Service.objects.create(
            provider=self.provider,
            category=self.category,
            title="Home Cleaning",
            description="Professional home cleaning service.",
            price=Decimal("1500.00"),
            duration_minutes=120,
            is_published=True,
        )

        self.other_service = Service.objects.create(
            provider=self.other_provider,
            category=self.category,
            title="Other Cleaning",
            description="Another cleaning service.",
            price=Decimal("2000.00"),
            duration_minutes=90,
            is_published=True,
        )

        self.customer = User.objects.create_user(
            username="dash_customer",
            email="dash_customer@example.com",
            password="StrongPassword123!",
            role=User.Role.CUSTOMER,
            is_verified=True,
        )

    def create_booking(
        self,
        *,
        customer=None,
        service=None,
        provider=None,
        booking_date=None,
        start_time_value=time(10, 0),
        status=Booking.Status.PENDING,
        total_amount=None,
    ):
        customer = customer or self.customer
        service = service or self.service
        provider = provider or self.provider
        booking_date = booking_date or timezone.localdate()
        end_time_value = (
            datetime.combine(
                booking_date,
                start_time_value,
            )
            + timedelta(hours=1)
        ).time()

        return Booking.objects.create(
            customer=customer,
            service=service,
            provider=provider,
            booking_date=booking_date,
            start_time=start_time_value,
            end_time=end_time_value,
            status=status,
            total_amount=(
                total_amount
                if total_amount is not None
                else service.price
            ),
        )

    def test_provider_dashboard_renders(self):
        self.client.force_login(self.provider_user)

        response = self.client.get(
            reverse("dashboard:provider"),
        )

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(
            response,
            "dashboard/provider.html",
        )

    def test_provider_dashboard_service_counts(self):
        Service.objects.create(
            provider=self.other_provider,
            category=self.category,
            title="Other Service",
            description="Other",
            price=Decimal("500.00"),
            duration_minutes=60,
            is_published=False,
        )

        self.client.force_login(self.provider_user)

        response = self.client.get(
            reverse("dashboard:provider"),
        )

        self.assertEqual(response.context["total_services"], 1)
        self.assertEqual(
            response.context["published_services"], 1
        )
        self.assertEqual(
            response.context["unpublished_services"], 0
        )

    def test_provider_dashboard_booking_counts(self):
        self.create_booking(status=Booking.Status.PENDING)
        self.create_booking(status=Booking.Status.CONFIRMED)
        self.create_booking(status=Booking.Status.COMPLETED)
        self.create_booking(status=Booking.Status.CANCELLED)

        self.client.force_login(self.provider_user)

        response = self.client.get(
            reverse("dashboard:provider"),
        )

        self.assertEqual(response.context["total_bookings"], 4)
        self.assertEqual(response.context["pending_bookings"], 1)
        self.assertEqual(response.context["confirmed_bookings"], 1)
        self.assertEqual(response.context["completed_bookings"], 1)
        self.assertEqual(response.context["cancelled_bookings"], 1)

    def test_provider_dashboard_upcoming_bookings(self):
        today = timezone.localdate()

        future_booking = self.create_booking(
            booking_date=today + timedelta(days=2),
            start_time_value=time(11, 0),
        )

        today_future_booking = self.create_booking(
            booking_date=today,
            start_time_value=time(23, 0),
        )

        self.create_booking(
            booking_date=today - timedelta(days=1),
            start_time_value=time(11, 0),
        )

        self.client.force_login(self.provider_user)

        response = self.client.get(
            reverse("dashboard:provider"),
        )

        upcoming = list(
            response.context["upcoming_bookings"],
        )

        self.assertEqual(len(upcoming), 2)
        self.assertEqual(upcoming[0], today_future_booking)
        self.assertEqual(upcoming[1], future_booking)

    def test_provider_dashboard_upcoming_bookings_are_limited_to_five(self):
        today = timezone.localdate()

        for offset in range(1, 8):
            self.create_booking(
                booking_date=today + timedelta(days=offset),
                start_time_value=time(10, 0),
            )

        self.client.force_login(self.provider_user)

        response = self.client.get(
            reverse("dashboard:provider"),
        )

        upcoming = list(
            response.context["upcoming_bookings"],
        )

        self.assertEqual(len(upcoming), 5)

    def test_provider_dashboard_recent_bookings(self):
        older_booking = self.create_booking(
            booking_date=timezone.localdate() - timedelta(days=2),
        )

        newer_booking = self.create_booking(
            booking_date=timezone.localdate() - timedelta(days=1),
        )

        self.client.force_login(self.provider_user)

        response = self.client.get(
            reverse("dashboard:provider"),
        )

        recent = list(
            response.context["recent_bookings"],
        )

        self.assertEqual(
            recent[:2],
            [
                newer_booking,
                older_booking,
            ],
        )

    def test_provider_dashboard_recent_bookings_are_limited_to_five(self):
        for offset in range(1, 8):
            self.create_booking(
                booking_date=timezone.localdate()
                - timedelta(days=offset),
            )

        self.client.force_login(self.provider_user)

        response = self.client.get(
            reverse("dashboard:provider"),
        )

        recent = list(
            response.context["recent_bookings"],
        )

        self.assertEqual(len(recent), 5)

    def test_provider_dashboard_review_summary(self):
        first_booking = self.create_booking(
            booking_date=timezone.localdate() - timedelta(days=5),
            status=Booking.Status.COMPLETED,
        )

        second_booking = self.create_booking(
            booking_date=timezone.localdate() - timedelta(days=4),
            status=Booking.Status.COMPLETED,
        )

        Review.objects.create(
            booking=first_booking,
            customer=self.customer,
            service=first_booking.service,
            provider=self.provider,
            rating=4,
            comment="Very good service.",
        )

        Review.objects.create(
            booking=second_booking,
            customer=self.customer,
            service=second_booking.service,
            provider=self.provider,
            rating=5,
            comment="Excellent service.",
        )

        self.client.force_login(self.provider_user)

        response = self.client.get(
            reverse("dashboard:provider"),
        )

        review_summary = response.context["review_summary"]

        self.assertEqual(review_summary["review_count"], 2)
        self.assertEqual(
            review_summary["average_rating"],
            Decimal("4.5"),
        )

    def test_provider_dashboard_review_summary_empty(self):
        self.client.force_login(self.provider_user)

        response = self.client.get(
            reverse("dashboard:provider"),
        )

        review_summary = response.context["review_summary"]

        self.assertEqual(review_summary["review_count"], 0)
        self.assertIsNone(
            review_summary["average_rating"],
        )

    def test_provider_dashboard_unread_notification_count(self):
        Notification.objects.create(
            recipient=self.provider_user,
            notification_type=(
                Notification.NotificationType.BOOKING_CREATED
            ),
            title="New Booking",
            message="You have a new booking.",
            is_read=False,
        )

        Notification.objects.create(
            recipient=self.provider_user,
            notification_type=(
                Notification.NotificationType.REVIEW_RECEIVED
            ),
            title="New Review",
            message="You received a new review.",
            is_read=True,
        )

        self.client.force_login(self.provider_user)

        response = self.client.get(
            reverse("dashboard:provider"),
        )

        self.assertEqual(
            response.context["unread_notification_count"],
            1,
        )

    def test_provider_dashboard_is_empty_for_new_provider(self):
        new_provider_user = User.objects.create_user(
            username="new_provider",
            email="new_provider@example.com",
            password="StrongPassword123!",
            role=User.Role.PROVIDER,
            is_verified=True,
        )

        new_provider = ProviderProfile.objects.create(
            user=new_provider_user,
            business_name="New Provider",
            email="new_provider@example.com",
        )

        self.client.force_login(new_provider_user)

        response = self.client.get(
            reverse("dashboard:provider"),
        )

        self.assertEqual(
            response.context["total_services"],
            0,
        )
        self.assertEqual(
            response.context["published_services"],
            0,
        )
        self.assertEqual(
            response.context["unpublished_services"],
            0,
        )
        self.assertEqual(
            response.context["total_bookings"],
            0,
        )
        self.assertEqual(
            response.context["pending_bookings"],
            0,
        )
        self.assertEqual(
            response.context["confirmed_bookings"],
            0,
        )
        self.assertEqual(
            response.context["completed_bookings"],
            0,
        )
        self.assertEqual(
            response.context["cancelled_bookings"],
            0,
        )
        self.assertEqual(
            list(response.context["upcoming_bookings"]),
            [],
        )
        self.assertEqual(
            list(response.context["recent_bookings"]),
            [],
        )
        self.assertEqual(
            response.context["review_summary"]["review_count"],
            0,
        )
        self.assertIsNone(
            response.context["review_summary"]["average_rating"],
        )
        self.assertEqual(
            response.context["unread_notification_count"],
            0,
        )

    def test_provider_dashboard_never_exposes_another_providers_data(self):
        own_booking = self.create_booking(
            booking_date=timezone.localdate() - timedelta(days=1),
        )

        other_booking = self.create_booking(
            customer=self.customer,
            service=self.other_service,
            provider=self.other_provider,
            booking_date=timezone.localdate() - timedelta(days=2),
        )

        Review.objects.create(
            booking=own_booking,
            customer=self.customer,
            service=own_booking.service,
            provider=self.provider,
            rating=5,
            comment="Own review.",
        )

        Review.objects.create(
            booking=other_booking,
            customer=self.customer,
            service=other_booking.service,
            provider=self.other_provider,
            rating=1,
            comment="Other provider's review.",
        )

        self.client.force_login(self.provider_user)

        response = self.client.get(
            reverse("dashboard:provider"),
        )

        recent_bookings = list(
            response.context["recent_bookings"],
        )

        upcoming_bookings = list(
            response.context["upcoming_bookings"],
        )

        review_summary = response.context["review_summary"]

        self.assertEqual(
            recent_bookings,
            [own_booking],
        )

        self.assertEqual(
            upcoming_bookings,
            [],
        )

        self.assertEqual(
            review_summary["review_count"],
            1,
        )
        self.assertEqual(
            review_summary["average_rating"],
            Decimal("5"),
        )

    def test_customer_cannot_access_provider_dashboard(self):
        self.client.force_login(self.customer)

        response = self.client.get(
            reverse("dashboard:provider"),
        )

        self.assertEqual(response.status_code, 403)

    def test_unauthenticated_cannot_access_provider_dashboard(self):
        response = self.client.get(
            reverse("dashboard:provider"),
        )

        self.assertEqual(response.status_code, 302)

    def test_provider_dashboard_query_count(self):
        self.create_booking()
        payment_booking = self.create_booking()
        Payment.objects.create(
            booking=payment_booking,
            amount=payment_booking.total_amount,
            currency="INR",
            status=Payment.Status.SUCCESS,
            payment_reference="PAY-1",
        )
        Review.objects.create(
            booking=self.create_booking(status=Booking.Status.COMPLETED),
            customer=self.customer,
            service=self.service,
            provider=self.provider,
            rating=4,
            comment="Good.",
        )

        self.client.force_login(self.provider_user)

        with self.assertNumQueries(9):
            self.client.get(reverse("dashboard:provider"))
