from decimal import Decimal
from datetime import date, time, timedelta

from django.test import TestCase
from django.urls import reverse

from accounts.models import User
from bookings.models import Booking
from bookings.services import create_booking
from providers.models import ProviderProfile
from reviews.models import Review
from reviews.services import create_review
from services.models import ProviderAvailability, Service, ServiceCategory


class ReviewViewTests(TestCase):

    def setUp(self):
        self.provider_user = User.objects.create_user(
            username="review_provider",
            email="review_provider@example.com",
            password="StrongPassword123!",
            role=User.Role.PROVIDER,
            is_verified=True,
        )

        self.customer = User.objects.create_user(
            username="review_customer",
            email="review_customer@example.com",
            password="StrongPassword123!",
            role=User.Role.CUSTOMER,
            is_verified=True,
        )

        self.other_customer = User.objects.create_user(
            username="other_review_customer",
            email="other_review_customer@example.com",
            password="StrongPassword123!",
            role=User.Role.CUSTOMER,
            is_verified=True,
        )

        self.provider = ProviderProfile.objects.create(
            user=self.provider_user,
            business_name="Review Testing Services",
        )

        self.category = ServiceCategory.objects.create(
            name="Review Testing",
            slug="review-testing",
            is_active=True,
        )

        self.service = Service.objects.create(
            provider=self.provider,
            category=self.category,
            title="Review Test Service",
            description="Service used for review testing.",
            price=Decimal("1000.00"),
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
        )

        self.booking.status = Booking.Status.COMPLETED
        self.booking.save(update_fields=["status"])

    def test_customer_can_delete_review_and_redirects_to_booking_detail(self):
        review = create_review(
            booking=self.booking,
            customer=self.customer,
            rating=5,
            comment="Great service!",
        )

        self.client.force_login(self.customer)

        response = self.client.post(
            reverse(
                "reviews:delete",
                kwargs={"booking_id": self.booking.pk},
            )
        )

        self.assertRedirects(
            response,
            reverse(
                "bookings:detail",
                kwargs={"pk": self.booking.pk},
            ),
        )

        self.assertFalse(Review.objects.filter(pk=review.pk).exists())

    def test_unauthorized_user_cannot_delete_review(self):
        review = create_review(
            booking=self.booking,
            customer=self.customer,
            rating=4,
            comment="Good service!",
        )

        self.client.force_login(self.other_customer)

        response = self.client.post(
            reverse(
                "reviews:delete",
                kwargs={"booking_id": self.booking.pk},
            )
        )

        self.assertEqual(response.status_code, 302)
        self.assertTrue(Review.objects.filter(pk=review.pk).exists())
