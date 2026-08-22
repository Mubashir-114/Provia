from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase
from datetime import date, time, timedelta

from django.urls import reverse

from accounts.models import User
from bookings.models import Booking
from bookings.services import create_booking
from providers.models import ProviderProfile
from services.models import (
    ProviderAvailability,
    Service,
    ServiceCategory,
)

from .models import Payment
from .services import (
    cancel_payment,
    create_payment,
    initiate_payment,
    mark_payment_failed,
    mark_payment_success,
)


class PaymentServiceTests(TestCase):

    def setUp(self):
        self.provider_user = User.objects.create_user(
            username="payment_provider",
            email="payment_provider@example.com",
            password="StrongPassword123!",
            role=User.Role.PROVIDER,
            is_verified=True,
        )

        self.customer = User.objects.create_user(
            username="payment_customer",
            email="payment_customer@example.com",
            password="StrongPassword123!",
            role=User.Role.CUSTOMER,
            is_verified=True,
        )

        self.other_customer = User.objects.create_user(
            username="other_payment_customer",
            email="other_payment_customer@example.com",
            password="StrongPassword123!",
            role=User.Role.CUSTOMER,
            is_verified=True,
        )

        self.provider = ProviderProfile.objects.create(
            user=self.provider_user,
            business_name="Payment Provider Services",
        )

        self.category = ServiceCategory.objects.create(
            name="Payment Testing",
            slug="payment-testing",
            is_active=True,
        )

        self.service = Service.objects.create(
            provider=self.provider,
            category=self.category,
            title="Payment Test Service",
            description="Service used for payment testing.",
            price=Decimal("1500.00"),
            duration_minutes=60,
            is_published=True,
        )

        self.booking_date = date.today() + timedelta(days=7)

        ProviderAvailability.objects.create(
            provider=self.provider,
            weekday=self.booking_date.weekday(),
            start_time=time(9, 0),
            end_time=time(17, 0),
            is_active=True,
        )

        self.booking = create_booking(
            customer=self.customer,
            service=self.service,
            booking_date=self.booking_date,
            start_time=time(10, 0),
            customer_notes="Payment test booking.",
        )

    def test_create_payment_creates_pending_payment(self):
        payment = create_payment(
            booking=self.booking,
            customer=self.customer,
        )

        self.assertEqual(payment.booking, self.booking)
        self.assertEqual(
            payment.amount,
            Decimal("1500.00"),
        )
        self.assertEqual(payment.currency, "INR")
        self.assertEqual(
            payment.status,
            Payment.Status.PENDING,
        )

    def test_payment_amount_comes_from_booking_total_amount(self):
        self.booking.total_amount = Decimal("1250.00")
        self.booking.save(update_fields=["total_amount"])

        payment = create_payment(
            booking=self.booking,
            customer=self.customer,
        )

        self.assertEqual(
            payment.amount,
            Decimal("1250.00"),
        )

    def test_customer_cannot_create_payment_for_another_customer_booking(self):
        with self.assertRaises(ValidationError):
            create_payment(
                booking=self.booking,
                customer=self.other_customer,
            )

        self.assertFalse(
            Payment.objects.filter(
                booking=self.booking,
            ).exists()
        )

    def test_cancelled_booking_cannot_create_payment(self):
        self.booking.status = Booking.Status.CANCELLED
        self.booking.save(update_fields=["status"])

        with self.assertRaises(ValidationError):
            create_payment(
                booking=self.booking,
                customer=self.customer,
            )

    def test_create_payment_does_not_duplicate_existing_payment(self):
        first_payment = create_payment(
            booking=self.booking,
            customer=self.customer,
        )

        second_payment = create_payment(
            booking=self.booking,
            customer=self.customer,
        )

        self.assertEqual(
            first_payment.pk,
            second_payment.pk,
        )

        self.assertEqual(
            Payment.objects.filter(
                booking=self.booking,
            ).count(),
            1,
        )

    def test_initiate_payment_changes_status_to_initiated(self):
        payment = create_payment(
            booking=self.booking,
            customer=self.customer,
        )

        payment = initiate_payment(
            payment=payment,
            customer=self.customer,
        )

        self.assertEqual(
            payment.status,
            Payment.Status.INITIATED,
        )

        self.assertTrue(payment.payment_reference.startswith("PRV-"))

    def test_initiated_payment_is_idempotent(self):
        payment = create_payment(
            booking=self.booking,
            customer=self.customer,
        )

        first = initiate_payment(
            payment=payment,
            customer=self.customer,
        )

        first_reference = first.payment_reference

        second = initiate_payment(
            payment=payment,
            customer=self.customer,
        )

        self.assertEqual(
            second.status,
            Payment.Status.INITIATED,
        )

        self.assertEqual(
            second.payment_reference,
            first_reference,
        )

    def test_customer_cannot_initiate_another_customers_payment(self):
        payment = create_payment(
            booking=self.booking,
            customer=self.customer,
        )

        with self.assertRaises(ValidationError):
            initiate_payment(
                payment=payment,
                customer=self.other_customer,
            )

    def test_successful_payment_confirms_booking(self):
        payment = create_payment(
            booking=self.booking,
            customer=self.customer,
        )

        payment = initiate_payment(
            payment=payment,
            customer=self.customer,
        )

        payment = mark_payment_success(
            payment=payment,
            customer=self.customer,
        )

        payment.refresh_from_db()
        self.booking.refresh_from_db()

        self.assertEqual(
            payment.status,
            Payment.Status.SUCCESS,
        )

        self.assertEqual(
            self.booking.status,
            Booking.Status.CONFIRMED,
        )

    def test_successful_payment_cannot_be_completed_again_from_initiated_flow(self):
        payment = create_payment(
            booking=self.booking,
            customer=self.customer,
        )

        payment = initiate_payment(
            payment=payment,
            customer=self.customer,
        )

        payment = mark_payment_success(
            payment=payment,
            customer=self.customer,
        )

        repeated = mark_payment_success(
            payment=payment,
            customer=self.customer,
        )

        self.assertEqual(
            repeated.status,
            Payment.Status.SUCCESS,
        )

    def test_customer_cannot_mark_another_customers_payment_success(self):
        payment = create_payment(
            booking=self.booking,
            customer=self.customer,
        )

        payment = initiate_payment(
            payment=payment,
            customer=self.customer,
        )

        with self.assertRaises(ValidationError):
            mark_payment_success(
                payment=payment,
                customer=self.other_customer,
            )

    def test_payment_failure_changes_status_to_failed(self):
        payment = create_payment(
            booking=self.booking,
            customer=self.customer,
        )

        payment = initiate_payment(
            payment=payment,
            customer=self.customer,
        )

        payment = mark_payment_failed(
            payment=payment,
            customer=self.customer,
        )

        self.assertEqual(
            payment.status,
            Payment.Status.FAILED,
        )

        self.booking.refresh_from_db()

        self.assertEqual(
            self.booking.status,
            Booking.Status.PENDING,
        )

    def test_failed_payment_cannot_be_marked_successful(self):
        payment = create_payment(
            booking=self.booking,
            customer=self.customer,
        )

        payment = initiate_payment(
            payment=payment,
            customer=self.customer,
        )

        payment = mark_payment_failed(
            payment=payment,
            customer=self.customer,
        )

        with self.assertRaises(ValidationError):
            mark_payment_success(
                payment=payment,
                customer=self.customer,
            )

    def test_pending_payment_can_be_cancelled(self):
        payment = create_payment(
            booking=self.booking,
            customer=self.customer,
        )

        payment = cancel_payment(
            payment=payment,
            customer=self.customer,
        )

        self.assertEqual(
            payment.status,
            Payment.Status.CANCELLED,
        )

        self.booking.refresh_from_db()

        self.assertEqual(
            self.booking.status,
            Booking.Status.PENDING,
        )

    def test_initiated_payment_can_be_cancelled(self):
        payment = create_payment(
            booking=self.booking,
            customer=self.customer,
        )

        payment = initiate_payment(
            payment=payment,
            customer=self.customer,
        )

        payment = cancel_payment(
            payment=payment,
            customer=self.customer,
        )

        self.assertEqual(
            payment.status,
            Payment.Status.CANCELLED,
        )

    def test_successful_payment_cannot_be_cancelled(self):
        payment = create_payment(
            booking=self.booking,
            customer=self.customer,
        )

        payment = initiate_payment(
            payment=payment,
            customer=self.customer,
        )

        payment = mark_payment_success(
            payment=payment,
            customer=self.customer,
        )

        with self.assertRaises(ValidationError):
            cancel_payment(
                payment=payment,
                customer=self.customer,
            )

    def test_cancelled_payment_cannot_be_initiated(self):
        payment = create_payment(
            booking=self.booking,
            customer=self.customer,
        )

        payment = cancel_payment(
            payment=payment,
            customer=self.customer,
        )

        with self.assertRaises(ValidationError):
            initiate_payment(
                payment=payment,
                customer=self.customer,
            )

    def test_cancelled_payment_cannot_be_completed(self):
        payment = create_payment(
            booking=self.booking,
            customer=self.customer,
        )

        payment = cancel_payment(
            payment=payment,
            customer=self.customer,
        )

        with self.assertRaises(ValidationError):
            mark_payment_success(
                payment=payment,
                customer=self.customer,
            )

    def test_payment_amount_mismatch_is_rejected(self):
        payment = Payment(
            booking=self.booking,
            amount=Decimal("999.00"),
            currency="INR",
            status=Payment.Status.PENDING,
        )

        with self.assertRaises(ValidationError):
            payment.full_clean()

    def test_payment_uses_booking_amount_not_service_current_price(self):
        original_booking_amount = self.booking.total_amount

        self.service.price = Decimal("2500.00")
        self.service.save(update_fields=["price"])

        payment = create_payment(
            booking=self.booking,
            customer=self.customer,
        )

        self.assertEqual(
            payment.amount,
            original_booking_amount,
        )

        self.assertNotEqual(
            payment.amount,
            self.service.price,
        )

    def test_failed_payment_can_be_reinitiated(self):
        payment = create_payment(
            booking=self.booking,
            customer=self.customer,
        )

        payment = initiate_payment(
            payment=payment,
            customer=self.customer,
        )

        payment = mark_payment_failed(
            payment=payment,
            customer=self.customer,
        )

        self.assertEqual(
            payment.status,
            Payment.Status.FAILED,
        )

        payment = initiate_payment(
            payment=payment,
            customer=self.customer,
        )

        self.assertEqual(
            payment.status,
            Payment.Status.INITIATED,
        )

        self.assertTrue(
            payment.payment_reference,
        )


class PaymentViewTests(TestCase):

    def setUp(self):
        self.provider_user = User.objects.create_user(
            username="view_provider",
            email="view_provider@example.com",
            password="StrongPassword123!",
            role=User.Role.PROVIDER,
            is_verified=True,
        )

        self.customer = User.objects.create_user(
            username="view_customer",
            email="view_customer@example.com",
            password="StrongPassword123!",
            role=User.Role.CUSTOMER,
            is_verified=True,
        )

        self.other_customer = User.objects.create_user(
            username="view_other_customer",
            email="view_other_customer@example.com",
            password="StrongPassword123!",
            role=User.Role.CUSTOMER,
            is_verified=True,
        )

        self.provider = ProviderProfile.objects.create(
            user=self.provider_user,
            business_name="Payment View Provider",
        )

        self.category = ServiceCategory.objects.create(
            name="Payment View Testing",
            slug="payment-view-testing",
            is_active=True,
        )

        self.service = Service.objects.create(
            provider=self.provider,
            category=self.category,
            title="Payment View Test Service",
            description="Service used for payment view testing.",
            price=Decimal("950.00"),
            duration_minutes=60,
            is_published=True,
        )

        self.booking_date = date.today() + timedelta(days=7)

        ProviderAvailability.objects.create(
            provider=self.provider,
            weekday=self.booking_date.weekday(),
            start_time=time(9, 0),
            end_time=time(17, 0),
            is_active=True,
        )

        self.booking = create_booking(
            customer=self.customer,
            service=self.service,
            booking_date=self.booking_date,
            start_time=time(11, 0),
            customer_notes="Payment view test booking.",
        )

    # ---------------------------------------------------------
    # CHECKOUT
    # ---------------------------------------------------------

    def test_customer_can_open_checkout_for_own_booking(self):
        self.client.force_login(self.customer)

        response = self.client.get(
            reverse(
                "payments:checkout",
                kwargs={"booking_id": self.booking.pk},
            )
        )

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(
            response,
            "payments/checkout.html",
        )

        self.assertContains(
            response,
            self.service.title,
        )

        self.assertContains(
            response,
            "950.00",
        )

        self.assertTrue(
            Payment.objects.filter(
                booking=self.booking,
            ).exists()
        )

    def test_checkout_uses_booking_total_amount(self):
        self.booking.total_amount = Decimal("875.00")
        self.booking.save(update_fields=["total_amount"])

        self.client.force_login(self.customer)

        response = self.client.get(
            reverse(
                "payments:checkout",
                kwargs={"booking_id": self.booking.pk},
            )
        )

        self.assertEqual(response.status_code, 200)

        payment = Payment.objects.get(
            booking=self.booking,
        )

        self.assertEqual(
            payment.amount,
            Decimal("875.00"),
        )

        self.assertContains(
            response,
            "875.00",
        )

    def test_customer_cannot_open_checkout_for_another_customers_booking(self):
        self.client.force_login(self.other_customer)

        response = self.client.get(
            reverse(
                "payments:checkout",
                kwargs={"booking_id": self.booking.pk},
            )
        )

        self.assertEqual(
            response.status_code,
            404,
        )

    def test_unauthenticated_customer_is_redirected_from_checkout(self):
        response = self.client.get(
            reverse(
                "payments:checkout",
                kwargs={"booking_id": self.booking.pk},
            )
        )

        self.assertEqual(
            response.status_code,
            302,
        )

        self.assertIn(
            "/login/",
            response.url,
        )

    def test_cancelled_booking_cannot_enter_checkout(self):
        self.booking.status = Booking.Status.CANCELLED
        self.booking.save(update_fields=["status"])

        self.client.force_login(self.customer)

        response = self.client.get(
            reverse(
                "payments:checkout",
                kwargs={"booking_id": self.booking.pk},
            )
        )

        self.assertEqual(
            response.status_code,
            302,
        )

        self.assertRedirects(
            response,
            reverse(
                "bookings:detail",
                kwargs={"pk": self.booking.pk},
            ),
        )

        self.assertFalse(
            Payment.objects.filter(
                booking=self.booking,
            ).exists()
        )

    # ---------------------------------------------------------
    # INITIATE
    # ---------------------------------------------------------

    def test_customer_can_initiate_own_payment(self):
        payment = create_payment(
            booking=self.booking,
            customer=self.customer,
        )

        self.client.force_login(self.customer)

        response = self.client.post(
            reverse(
                "payments:initiate",
                kwargs={"payment_id": payment.pk},
            )
        )

        self.assertEqual(response.status_code, 200)

        self.assertTemplateUsed(
            response,
            "payments/mock_payment.html",
        )

        payment.refresh_from_db()

        self.assertEqual(
            payment.status,
            Payment.Status.INITIATED,
        )

        self.assertTrue(payment.payment_reference)

    def test_get_initiate_endpoint_is_not_allowed(self):
        payment = create_payment(
            booking=self.booking,
            customer=self.customer,
        )

        self.client.force_login(self.customer)

        response = self.client.get(
            reverse(
                "payments:initiate",
                kwargs={"payment_id": payment.pk},
            )
        )

        self.assertEqual(
            response.status_code,
            405,
        )

    def test_customer_cannot_initiate_another_customers_payment(self):
        payment = create_payment(
            booking=self.booking,
            customer=self.customer,
        )

        self.client.force_login(self.other_customer)

        response = self.client.post(
            reverse(
                "payments:initiate",
                kwargs={"payment_id": payment.pk},
            )
        )

        self.assertEqual(
            response.status_code,
            404,
        )

        payment.refresh_from_db()

        self.assertEqual(
            payment.status,
            Payment.Status.PENDING,
        )

    def test_unauthenticated_customer_cannot_initiate_payment(self):
        payment = create_payment(
            booking=self.booking,
            customer=self.customer,
        )

        response = self.client.post(
            reverse(
                "payments:initiate",
                kwargs={"payment_id": payment.pk},
            )
        )

        self.assertEqual(
            response.status_code,
            302,
        )

        self.assertIn(
            "/login/",
            response.url,
        )

    # ---------------------------------------------------------
    # SUCCESS
    # ---------------------------------------------------------

    def test_successful_payment_confirms_booking_through_view(self):
        payment = create_payment(
            booking=self.booking,
            customer=self.customer,
        )

        initiate_payment(
            payment=payment,
            customer=self.customer,
        )

        self.client.force_login(self.customer)

        response = self.client.post(
            reverse(
                "payments:mock_success",
                kwargs={"payment_id": payment.pk},
            )
        )

        self.assertRedirects(
            response,
            reverse(
                "payments:detail",
                kwargs={"payment_id": payment.pk},
            ),
        )

        payment.refresh_from_db()
        self.booking.refresh_from_db()

        self.assertEqual(
            payment.status,
            Payment.Status.SUCCESS,
        )

        self.assertEqual(
            self.booking.status,
            Booking.Status.CONFIRMED,
        )

    def test_get_success_endpoint_is_not_allowed(self):
        payment = create_payment(
            booking=self.booking,
            customer=self.customer,
        )

        initiate_payment(
            payment=payment,
            customer=self.customer,
        )

        self.client.force_login(self.customer)

        response = self.client.get(
            reverse(
                "payments:mock_success",
                kwargs={"payment_id": payment.pk},
            )
        )

        self.assertEqual(
            response.status_code,
            405,
        )

    def test_other_customer_cannot_complete_payment(self):
        payment = create_payment(
            booking=self.booking,
            customer=self.customer,
        )

        initiate_payment(
            payment=payment,
            customer=self.customer,
        )

        self.client.force_login(self.other_customer)

        response = self.client.post(
            reverse(
                "payments:mock_success",
                kwargs={"payment_id": payment.pk},
            )
        )

        self.assertEqual(
            response.status_code,
            404,
        )

        payment.refresh_from_db()
        self.booking.refresh_from_db()

        self.assertEqual(
            payment.status,
            Payment.Status.INITIATED,
        )

        self.assertEqual(
            self.booking.status,
            Booking.Status.PENDING,
        )

    # ---------------------------------------------------------
    # FAILURE
    # ---------------------------------------------------------

    def test_failed_payment_keeps_booking_pending(self):
        payment = create_payment(
            booking=self.booking,
            customer=self.customer,
        )

        initiate_payment(
            payment=payment,
            customer=self.customer,
        )

        self.client.force_login(self.customer)

        response = self.client.post(
            reverse(
                "payments:mock_failure",
                kwargs={"payment_id": payment.pk},
            )
        )

        self.assertRedirects(
            response,
            reverse(
                "payments:detail",
                kwargs={"payment_id": payment.pk},
            ),
        )

        payment.refresh_from_db()
        self.booking.refresh_from_db()

        self.assertEqual(
            payment.status,
            Payment.Status.FAILED,
        )

        self.assertEqual(
            self.booking.status,
            Booking.Status.PENDING,
        )

    def test_get_failure_endpoint_is_not_allowed(self):
        payment = create_payment(
            booking=self.booking,
            customer=self.customer,
        )

        initiate_payment(
            payment=payment,
            customer=self.customer,
        )

        self.client.force_login(self.customer)

        response = self.client.get(
            reverse(
                "payments:mock_failure",
                kwargs={"payment_id": payment.pk},
            )
        )

        self.assertEqual(
            response.status_code,
            405,
        )

    # ---------------------------------------------------------
    # PAYMENT DETAIL
    # ---------------------------------------------------------

    def test_customer_can_view_own_payment_detail(self):
        payment = create_payment(
            booking=self.booking,
            customer=self.customer,
        )

        self.client.force_login(self.customer)

        response = self.client.get(
            reverse(
                "payments:detail",
                kwargs={"payment_id": payment.pk},
            )
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertTemplateUsed(
            response,
            "payments/detail.html",
        )

        self.assertContains(
            response,
            "Payment",
        )

        self.assertContains(
            response,
            "950.00",
        )

    def test_customer_cannot_view_another_customers_payment(self):
        payment = create_payment(
            booking=self.booking,
            customer=self.customer,
        )

        self.client.force_login(self.other_customer)

        response = self.client.get(
            reverse(
                "payments:detail",
                kwargs={"payment_id": payment.pk},
            )
        )

        self.assertEqual(
            response.status_code,
            404,
        )

    def test_failed_payment_shows_retry_button(self):
        payment = create_payment(
            booking=self.booking,
            customer=self.customer,
        )
        initiate_payment(
            payment=payment,
            customer=self.customer,
        )
        mark_payment_failed(
            payment=payment,
            customer=self.customer,
        )

        self.client.force_login(self.customer)
        response = self.client.get(
            reverse(
                "payments:detail",
                kwargs={"payment_id": payment.pk},
            )
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Retry Payment")

    def test_successful_payment_does_not_show_retry_button(self):
        payment = create_payment(
            booking=self.booking,
            customer=self.customer,
        )
        initiate_payment(
            payment=payment,
            customer=self.customer,
        )
        mark_payment_success(
            payment=payment,
            customer=self.customer,
        )

        self.client.force_login(self.customer)
        response = self.client.get(
            reverse(
                "payments:detail",
                kwargs={"payment_id": payment.pk},
            )
        )
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Retry Payment")

    # ---------------------------------------------------------
    # CANCEL
    # ---------------------------------------------------------

    def test_customer_can_cancel_pending_payment(self):
        payment = create_payment(
            booking=self.booking,
            customer=self.customer,
        )

        self.client.force_login(self.customer)

        response = self.client.post(
            reverse(
                "payments:cancel",
                kwargs={"payment_id": payment.pk},
            )
        )

        self.assertRedirects(
            response,
            reverse(
                "bookings:detail",
                kwargs={"pk": self.booking.pk},
            ),
        )

        payment.refresh_from_db()

        self.assertEqual(
            payment.status,
            Payment.Status.CANCELLED,
        )

    def test_get_cancel_endpoint_is_not_allowed(self):
        payment = create_payment(
            booking=self.booking,
            customer=self.customer,
        )

        self.client.force_login(self.customer)

        response = self.client.get(
            reverse(
                "payments:cancel",
                kwargs={"payment_id": payment.pk},
            )
        )

        self.assertEqual(
            response.status_code,
            405,
        )

    def test_successful_payment_cannot_be_cancelled_through_view(self):
        payment = create_payment(
            booking=self.booking,
            customer=self.customer,
        )

        initiate_payment(
            payment=payment,
            customer=self.customer,
        )

        mark_payment_success(
            payment=payment,
            customer=self.customer,
        )

        self.client.force_login(self.customer)

        response = self.client.post(
            reverse(
                "payments:cancel",
                kwargs={"payment_id": payment.pk},
            )
        )

        self.assertRedirects(
            response,
            reverse(
                "payments:detail",
                kwargs={"payment_id": payment.pk},
            ),
        )

        payment.refresh_from_db()

        self.assertEqual(
            payment.status,
            Payment.Status.SUCCESS,
        )

    # ---------------------------------------------------------
    # TEMPLATE REGRESSION CHECKS
    # ---------------------------------------------------------

    def test_checkout_does_not_render_raw_django_include_tag(self):
        self.client.force_login(self.customer)

        response = self.client.get(
            reverse(
                "payments:checkout",
                kwargs={"booking_id": self.booking.pk},
            )
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertNotContains(
            response,
            '{% include "components/back_button.html"',
        )

    def test_payment_detail_does_not_render_raw_django_variable(self):
        payment = create_payment(
            booking=self.booking,
            customer=self.customer,
        )

        self.client.force_login(self.customer)

        response = self.client.get(
            reverse(
                "payments:detail",
                kwargs={"payment_id": payment.pk},
            )
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertNotContains(
            response,
            '{{ booking.start_time|time:"H:i" }}',
        )
