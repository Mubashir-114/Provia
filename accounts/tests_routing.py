from datetime import date, time
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import resolve, reverse

from bookings.models import Booking
from providers.models import ProviderProfile
from services.models import Service, ServiceCategory

User = get_user_model()


class GlobalRoutingTests(TestCase):
    """
    Test suite for Phase 1 Foundation:
    Global routing, canonical URL names, role-based authorization, and UI link connections.
    """

    def setUp(self):
        # Create Customer
        self.customer = User.objects.create_user(
            username="customer_user",
            email="customer@example.com",
            password="password123",
            role=User.Role.CUSTOMER,
            is_verified=True,
        )

        # Create Provider
        self.provider_user = User.objects.create_user(
            username="provider_user",
            email="provider@example.com",
            password="password123",
            role=User.Role.PROVIDER,
            is_verified=True,
        )
        self.provider_profile = ProviderProfile.objects.create(
            user=self.provider_user,
            business_name="Apex Plumbing",
            phone="1234567890",
            city="Kozhikode",
            state="Kerala",
        )

        # Create Category & Service
        self.category = ServiceCategory.objects.create(
            name="Plumbing",
            slug="plumbing",
        )
        self.service = Service.objects.create(
            provider=self.provider_profile,
            category=self.category,
            title="Leak Repair",
            description="Professional leak repair service",
            price=500.00,
            duration_minutes=60,
            is_published=True,
        )

        # Create Booking
        self.booking = Booking.objects.create(
            customer=self.customer,
            provider=self.provider_profile,
            service=self.service,
            booking_date=date.today(),
            start_time=time(10, 0),
            end_time=time(11, 0),
            status=Booking.Status.PENDING,
        )

    # -------------------------------------------------------------------------
    # 1. URL RESOLUTION TESTS
    # -------------------------------------------------------------------------

    def test_canonical_urls_resolve(self):
        """Verify all Phase 1 canonical URL names resolve to the expected path."""
        self.assertEqual(reverse("home"), "/")
        self.assertEqual(reverse("accounts:login"), "/accounts/login/")
        self.assertEqual(reverse("accounts:logout"), "/accounts/logout/")
        self.assertEqual(reverse("accounts:register"), "/accounts/register/")
        self.assertEqual(reverse("accounts:profile"), "/accounts/profile/")
        self.assertEqual(reverse("dashboard:customer"), "/dashboard/customer/")
        self.assertEqual(reverse("dashboard:provider"), "/dashboard/provider/")
        self.assertEqual(reverse("providers:profile"), "/providers/profile/")
        self.assertEqual(reverse("services:public_list"), "/services/discover/")
        self.assertEqual(
            reverse("services:public_detail", kwargs={"pk": self.service.pk}),
            f"/services/discover/{self.service.pk}/",
        )
        self.assertEqual(reverse("services:list"), "/services/")
        self.assertEqual(reverse("services:create"), "/services/create/")
        self.assertEqual(reverse("services:availability_list"), "/services/availability/")
        self.assertEqual(reverse("bookings:my_bookings"), "/bookings/my/")
        self.assertEqual(
            reverse("bookings:create", kwargs={"service_id": self.service.pk}),
            f"/bookings/service/{self.service.pk}/book/",
        )
        self.assertEqual(
            reverse("bookings:detail", kwargs={"pk": self.booking.pk}),
            f"/bookings/{self.booking.pk}/",
        )
        self.assertEqual(reverse("bookings:provider_bookings"), "/bookings/provider/")
        self.assertEqual(
            reverse("bookings:provider_detail", kwargs={"pk": self.booking.pk}),
            f"/bookings/provider/{self.booking.pk}/",
        )

    # -------------------------------------------------------------------------
    # 2. AUTHENTICATION & ACCESS CONTROL TESTS
    # -------------------------------------------------------------------------

    def test_guest_access_public_pages(self):
        """Guest users should access home and public service discovery pages."""
        response_home = self.client.get(reverse("home"))
        self.assertEqual(response_home.status_code, 200)

        response_discover = self.client.get(reverse("services:public_list"))
        self.assertEqual(response_discover.status_code, 200)

        response_detail = self.client.get(
            reverse("services:public_detail", kwargs={"pk": self.service.pk})
        )
        self.assertEqual(response_detail.status_code, 200)

    def test_guest_restricted_from_dashboards(self):
        """Guest users must be redirected to login when accessing protected dashboards."""
        response_cust = self.client.get(reverse("dashboard:customer"))
        self.assertRedirects(response_cust, f"/accounts/login/?next={reverse('dashboard:customer')}")

        response_prov = self.client.get(reverse("dashboard:provider"))
        self.assertRedirects(response_prov, f"/accounts/login/?next={reverse('dashboard:provider')}")

    def test_customer_role_protection(self):
        """Customer users cannot access provider dashboard or provider bookings."""
        self.client.login(username="customer_user", password="password123")

        response = self.client.get(reverse("dashboard:provider"))
        self.assertEqual(response.status_code, 403)

        response_prov_bk = self.client.get(reverse("bookings:provider_bookings"))
        self.assertEqual(response_prov_bk.status_code, 403)

    def test_provider_role_protection(self):
        """Provider users cannot access customer dashboard or customer bookings."""
        self.client.login(username="provider_user", password="password123")

        response = self.client.get(reverse("dashboard:customer"))
        self.assertEqual(response.status_code, 403)

        response_my_bk = self.client.get(reverse("bookings:my_bookings"))
        self.assertEqual(response_my_bk.status_code, 403)

    def test_post_logout_terminates_session(self):
        """POST logout terminates user session and redirects to home."""
        self.client.login(username="customer_user", password="password123")

        response = self.client.post(reverse("accounts:logout"))
        self.assertRedirects(response, reverse("home"))

        # Verify session is terminated
        response_dash = self.client.get(reverse("dashboard:customer"))
        self.assertRedirects(response_dash, f"/accounts/login/?next={reverse('dashboard:customer')}")

    # -------------------------------------------------------------------------
    # 3. NAVIGATION CONNECTION & UI LINK TESTS
    # -------------------------------------------------------------------------

    def test_provider_dashboard_contains_bookings_link(self):
        """Provider dashboard HTML must contain provider bookings URL."""
        self.client.login(username="provider_user", password="password123")

        response = self.client.get(reverse("dashboard:provider"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, reverse("bookings:provider_bookings"))

    def test_customer_dashboard_contains_my_bookings_link(self):
        """Customer dashboard HTML must contain my_bookings URL."""
        self.client.login(username="customer_user", password="password123")

        response = self.client.get(reverse("dashboard:customer"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, reverse("bookings:my_bookings"))

    def test_service_detail_contains_booking_action(self):
        """Public service detail view contains booking action/login redirect."""
        self.client.login(username="customer_user", password="password123")

        response = self.client.get(
            reverse("services:public_detail", kwargs={"pk": self.service.pk})
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            reverse("bookings:create", kwargs={"service_id": self.service.pk}),
        )

    def test_booking_detail_contains_back_link(self):
        """Customer booking detail page contains deterministic back link to my_bookings."""
        self.client.login(username="customer_user", password="password123")

        response = self.client.get(
            reverse("bookings:detail", kwargs={"pk": self.booking.pk})
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, reverse("bookings:my_bookings"))

    def test_provider_booking_detail_contains_back_link(self):
        """Provider booking detail page contains deterministic back link to provider_bookings."""
        self.client.login(username="provider_user", password="password123")

        response = self.client.get(
            reverse("bookings:provider_detail", kwargs={"pk": self.booking.pk})
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, reverse("bookings:provider_bookings"))
