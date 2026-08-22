from django.test import TestCase
from django.urls import reverse

from .models import ServiceCategory

from django.db import IntegrityError
from django.test import TestCase
from decimal import Decimal

from django.db import IntegrityError
from django.test import TestCase

from providers.models import ProviderProfile

from datetime import time

from django.core.exceptions import ValidationError

from .models import (
    ProviderAvailability,
    Service,
    ServiceCategory,
    ServiceLocation,
)


class ServiceModelTests(TestCase):

    def setUp(self):
        self.user = self._create_provider_user()

        self.provider = ProviderProfile.objects.create(
            user=self.user,
            business_name="Provia Home Services",
        )

        self.category = ServiceCategory.objects.create(
            name="Home Cleaning",
            slug="home-cleaning",
        )

    def _create_provider_user(self):
        from accounts.models import User

        return User.objects.create_user(
            username="serviceprovider",
            email="provider@example.com",
            password="StrongPassword123!",
            role=User.Role.PROVIDER,
            is_verified=True,
        )

    def test_service_can_be_created(self):
        service = Service.objects.create(
            provider=self.provider,
            category=self.category,
            title="Deep Home Cleaning",
            description="Professional deep cleaning service.",
            price=Decimal("1500.00"),
            duration_minutes=120,
        )

        self.assertEqual(
            service.provider,
            self.provider,
        )

        self.assertEqual(
            service.category,
            self.category,
        )

        self.assertEqual(
            service.price,
            Decimal("1500.00"),
        )

        self.assertEqual(
            service.duration_minutes,
            120,
        )

        self.assertFalse(service.is_published)

    def test_service_string_representation(self):
        service = Service.objects.create(
            provider=self.provider,
            category=self.category,
            title="Bathroom Cleaning",
            description="Professional bathroom cleaning.",
            price=Decimal("500.00"),
            duration_minutes=60,
        )

        self.assertEqual(
            str(service),
            "Bathroom Cleaning",
        )

    def test_service_is_unpublished_by_default(self):
        service = Service.objects.create(
            provider=self.provider,
            category=self.category,
            title="Kitchen Cleaning",
            description="Professional kitchen cleaning.",
            price=Decimal("700.00"),
            duration_minutes=60,
        )

        self.assertFalse(
            service.is_published,
        )

    def test_service_belongs_to_provider(self):
        service = Service.objects.create(
            provider=self.provider,
            category=self.category,
            title="Floor Cleaning",
            description="Professional floor cleaning.",
            price=Decimal("600.00"),
            duration_minutes=60,
        )

        self.assertIn(
            service,
            self.provider.services.all(),
        )

    def test_service_belongs_to_category(self):
        service = Service.objects.create(
            provider=self.provider,
            category=self.category,
            title="Window Cleaning",
            description="Professional window cleaning.",
            price=Decimal("800.00"),
            duration_minutes=90,
        )

        self.assertIn(
            service,
            self.category.services.all(),
        )

    def test_category_cannot_be_deleted_when_used_by_service(self):
        Service.objects.create(
            provider=self.provider,
            category=self.category,
            title="Cleaning Service",
            description="Professional cleaning.",
            price=Decimal("1000.00"),
            duration_minutes=60,
        )

        with self.assertRaises(IntegrityError):
            self.category.delete()


class ServiceCategoryModelTests(TestCase):

    def test_category_can_be_created(self):
        category = ServiceCategory.objects.create(
            name="Home Cleaning",
            slug="home-cleaning",
            description="Professional home cleaning services.",
        )

        self.assertEqual(
            category.name,
            "Home Cleaning",
        )

        self.assertEqual(
            category.slug,
            "home-cleaning",
        )

        self.assertTrue(
            category.is_active,
        )

    def test_category_string_representation(self):
        category = ServiceCategory.objects.create(
            name="Plumbing",
            slug="plumbing",
        )

        self.assertEqual(
            str(category),
            "Plumbing",
        )

    def test_category_is_active_by_default(self):
        category = ServiceCategory.objects.create(
            name="Electrical",
            slug="electrical",
        )

        self.assertTrue(
            category.is_active,
        )

    def test_category_can_be_deactivated(self):
        category = ServiceCategory.objects.create(
            name="Painting",
            slug="painting",
            is_active=False,
        )

        self.assertFalse(
            category.is_active,
        )

    def test_category_name_must_be_unique(self):
        ServiceCategory.objects.create(
            name="Photography",
            slug="photography",
        )

        with self.assertRaises(IntegrityError):
            ServiceCategory.objects.create(
                name="Photography",
                slug="photography-2",
            )

    def test_category_slug_must_be_unique(self):
        ServiceCategory.objects.create(
            name="AC Repair",
            slug="ac-repair",
        )

        with self.assertRaises(IntegrityError):
            ServiceCategory.objects.create(
                name="Air Conditioner Repair",
                slug="ac-repair",
            )


class ServiceLocationModelTests(TestCase):

    def setUp(self):
        from accounts.models import User

        user = User.objects.create_user(
            username="locationprovider",
            email="location@example.com",
            password="StrongPassword123!",
            role=User.Role.PROVIDER,
            is_verified=True,
        )

        provider = ProviderProfile.objects.create(
            user=user,
            business_name="Provia Services",
        )

        category = ServiceCategory.objects.create(
            name="Plumbing",
            slug="plumbing",
        )

        self.service = Service.objects.create(
            provider=provider,
            category=category,
            title="Emergency Plumbing",
            description="Emergency plumbing service.",
            price=Decimal("1000.00"),
            duration_minutes=60,
        )

    def test_service_location_can_be_created(self):
        location = ServiceLocation.objects.create(
            service=self.service,
            address="123 Main Street",
            city="Kozhikode",
            state="Kerala",
            postal_code="673001",
            service_radius_km=15,
        )

        self.assertEqual(
            location.service,
            self.service,
        )

        self.assertEqual(
            location.city,
            "Kozhikode",
        )

        self.assertEqual(
            location.service_radius_km,
            15,
        )

    def test_service_has_one_location(self):
        location = ServiceLocation.objects.create(
            service=self.service,
            city="Kozhikode",
            state="Kerala",
        )

        self.assertEqual(
            self.service.location,
            location,
        )

    def test_location_string_representation(self):
        location = ServiceLocation.objects.create(
            service=self.service,
            city="Kozhikode",
            state="Kerala",
        )

        self.assertEqual(
            str(location),
            "Emergency Plumbing - Kozhikode",
        )


class ProviderAvailabilityModelTests(TestCase):

    def setUp(self):
        from accounts.models import User

        user = User.objects.create_user(
            username="availabilityprovider",
            email="availability@example.com",
            password="StrongPassword123!",
            role=User.Role.PROVIDER,
            is_verified=True,
        )

        self.provider = ProviderProfile.objects.create(
            user=user,
            business_name="Provia Services",
        )

    def test_availability_can_be_created(self):
        availability = ProviderAvailability.objects.create(
            provider=self.provider,
            weekday=ProviderAvailability.Weekday.MONDAY,
            start_time=time(9, 0),
            end_time=time(17, 0),
        )

        self.assertEqual(
            availability.provider,
            self.provider,
        )

        self.assertEqual(
            availability.weekday,
            ProviderAvailability.Weekday.MONDAY,
        )

        self.assertTrue(
            availability.is_active,
        )

    def test_invalid_time_range_is_rejected(self):
        availability = ProviderAvailability(
            provider=self.provider,
            weekday=ProviderAvailability.Weekday.TUESDAY,
            start_time=time(17, 0),
            end_time=time(9, 0),
        )

        with self.assertRaises(ValidationError):
            availability.full_clean()

    def test_equal_start_and_end_time_is_rejected(self):
        availability = ProviderAvailability(
            provider=self.provider,
            weekday=ProviderAvailability.Weekday.WEDNESDAY,
            start_time=time(10, 0),
            end_time=time(10, 0),
        )

        with self.assertRaises(ValidationError):
            availability.full_clean()

    def test_provider_cannot_have_duplicate_weekday(self):
        ProviderAvailability.objects.create(
            provider=self.provider,
            weekday=ProviderAvailability.Weekday.THURSDAY,
            start_time=time(9, 0),
            end_time=time(17, 0),
        )

        with self.assertRaises(Exception):
            ProviderAvailability.objects.create(
                provider=self.provider,
                weekday=ProviderAvailability.Weekday.THURSDAY,
                start_time=time(10, 0),
                end_time=time(18, 0),
            )

    def test_availability_string_representation(self):
        availability = ProviderAvailability.objects.create(
            provider=self.provider,
            weekday=ProviderAvailability.Weekday.FRIDAY,
            start_time=time(9, 0),
            end_time=time(17, 0),
        )

        self.assertEqual(
            str(availability),
            "Provia Services - Friday",
        )

class CustomerDiscoveryTests(TestCase):

    def setUp(self):
        from accounts.models import User

        self.provider_user = User.objects.create_user(
            username="discoveryprovider",
            email="discovery@example.com",
            password="StrongPassword123!",
            role=User.Role.PROVIDER,
            is_verified=True,
        )

        self.provider = ProviderProfile.objects.create(
            user=self.provider_user,
            business_name="Provia Local Services",
        )

        self.category = ServiceCategory.objects.create(
            name="Home Cleaning",
            slug="home-cleaning",
            is_active=True,
        )

        self.other_category = ServiceCategory.objects.create(
            name="Plumbing",
            slug="plumbing",
            is_active=True,
        )

        self.published_service = Service.objects.create(
            provider=self.provider,
            category=self.category,
            title="Deep Home Cleaning",
            description="Professional deep cleaning service.",
            price=Decimal("1500.00"),
            duration_minutes=120,
            is_published=True,
        )

        self.draft_service = Service.objects.create(
            provider=self.provider,
            category=self.category,
            title="Draft Cleaning Service",
            description="This should not be public.",
            price=Decimal("800.00"),
            duration_minutes=60,
            is_published=False,
        )

        self.plumbing_service = Service.objects.create(
            provider=self.provider,
            category=self.other_category,
            title="Emergency Plumbing",
            description="Emergency plumbing repairs.",
            price=Decimal("1000.00"),
            duration_minutes=60,
            is_published=True,
        )

        ServiceLocation.objects.create(
            service=self.published_service,
            city="Kozhikode",
            state="Kerala",
            postal_code="673001",
            service_radius_km=15,
        )

        ServiceLocation.objects.create(
            service=self.plumbing_service,
            city="Malappuram",
            state="Kerala",
            postal_code="676505",
            service_radius_km=10,
        )

    def test_public_service_list_is_accessible_without_login(self):
        response = self.client.get(
            reverse("services:public_list")
        )

        self.assertEqual(
            response.status_code,
            200,
        )

    def test_only_published_services_are_visible(self):
        response = self.client.get(
            reverse("services:public_list")
        )

        self.assertContains(
            response,
            "Deep Home Cleaning",
        )

        self.assertContains(
            response,
            "Emergency Plumbing",
        )

        self.assertNotContains(
            response,
            "Draft Cleaning Service",
        )

    def test_search_filters_services(self):
        response = self.client.get(
            reverse("services:public_list"),
            {"q": "plumbing"},
        )

        self.assertContains(
            response,
            "Emergency Plumbing",
        )

        self.assertNotContains(
            response,
            "Deep Home Cleaning",
        )

    def test_category_filter(self):
        response = self.client.get(
            reverse("services:public_list"),
            {"category": "home-cleaning"},
        )

        self.assertContains(
            response,
            "Deep Home Cleaning",
        )

        self.assertNotContains(
            response,
            "Emergency Plumbing",
        )

    def test_city_filter(self):
        response = self.client.get(
            reverse("services:public_list"),
            {"city": "Kozhikode"},
        )

        self.assertContains(
            response,
            "Deep Home Cleaning",
        )

        self.assertNotContains(
            response,
            "Emergency Plumbing",
        )

    def test_public_service_detail(self):
        response = self.client.get(
            reverse(
                "services:public_detail",
                kwargs={
                    "pk": self.published_service.pk,
                },
            )
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertContains(
            response,
            "Deep Home Cleaning",
        )

        self.assertContains(
            response,
            "Provia Local Services",
        )

    def test_draft_service_detail_is_not_public(self):
        response = self.client.get(
            reverse(
                "services:public_detail",
                kwargs={
                    "pk": self.draft_service.pk,
                },
            )
        )

        self.assertEqual(
            response.status_code,
            404,
        )

    def test_inactive_category_services_are_not_public(self):
        self.category.is_active = False
        self.category.save()

        response = self.client.get(
            reverse("services:public_list")
        )

        self.assertNotContains(
            response,
            "Deep Home Cleaning",
        )
    def test_public_listing_handles_service_without_location(self):
        service_without_location = Service.objects.create(
            provider=self.provider,
            category=self.category,
            title="Basic Cleaning",
            description="Basic cleaning service.",
            price=Decimal("500.00"),
            duration_minutes=30,
            is_published=True,
        )

        response = self.client.get(
            reverse("services:public_list")
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertContains(
            response,
            service_without_location.title,
        )

    def test_combined_filters(self):
        response = self.client.get(
            reverse("services:public_list"),
            {"q": "Deep", "category": "home-cleaning", "city": "Kozhikode"},
        )
        self.assertContains(response, "Deep Home Cleaning")
        self.assertNotContains(response, "Emergency Plumbing")

    def test_inactive_category_detail_returns_404(self):
        self.category.is_active = False
        self.category.save()

        response = self.client.get(
            reverse("services:public_detail", kwargs={"pk": self.published_service.pk})
        )
        self.assertEqual(response.status_code, 404)

    def test_public_service_detail_shows_active_availability_only(self):
        ProviderAvailability.objects.create(
            provider=self.provider,
            weekday=ProviderAvailability.Weekday.MONDAY,
            start_time=time(9, 0),
            end_time=time(17, 0),
            is_active=True,
        )
        ProviderAvailability.objects.create(
            provider=self.provider,
            weekday=ProviderAvailability.Weekday.TUESDAY,
            start_time=time(9, 0),
            end_time=time(17, 0),
            is_active=False,
        )

        response = self.client.get(
            reverse("services:public_detail", kwargs={"pk": self.published_service.pk})
        )
        self.assertContains(response, "Monday")
        self.assertNotContains(response, "Tuesday")

    def test_pagination_and_query_preservation(self):
        for i in range(12):
            s = Service.objects.create(
                provider=self.provider,
                category=self.category,
                title=f"Extra Service {i}",
                description="Extra description",
                price=Decimal("100.00"),
                duration_minutes=30,
                is_published=True,
            )
            ServiceLocation.objects.create(service=s, city="Kozhikode", state="Kerala")

        response = self.client.get(
            reverse("services:public_list"),
            {"category": "home-cleaning", "page": 2},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "category=home-cleaning")


class ServicePublishingViewsTests(TestCase):

    def setUp(self):
        from accounts.models import User

        self.user1 = User.objects.create_user(
            username="provider1",
            email="provider1@example.com",
            password="StrongPassword123!",
            role=User.Role.PROVIDER,
            is_verified=True,
        )
        self.provider1 = ProviderProfile.objects.create(
            user=self.user1,
            business_name="Provider One Services",
        )

        self.user2 = User.objects.create_user(
            username="provider2",
            email="provider2@example.com",
            password="StrongPassword123!",
            role=User.Role.PROVIDER,
            is_verified=True,
        )
        self.provider2 = ProviderProfile.objects.create(
            user=self.user2,
            business_name="Provider Two Services",
        )

        self.category = ServiceCategory.objects.create(
            name="Plumbing",
            slug="plumbing",
        )

        self.service = Service.objects.create(
            provider=self.provider1,
            category=self.category,
            title="Tap Repair",
            description="Fixing leaking taps",
            price=Decimal("300.00"),
            duration_minutes=30,
            is_published=False,
        )

    def test_provider_can_publish_own_service(self):
        self.client.login(username="provider1", password="StrongPassword123!")
        response = self.client.post(
            reverse("services:publish", kwargs={"pk": self.service.pk})
        )
        self.assertRedirects(response, reverse("services:list"))
        self.service.refresh_from_db()
        self.assertTrue(self.service.is_published)

    def test_provider_can_unpublish_own_service(self):
        self.service.is_published = True
        self.service.save()

        self.client.login(username="provider1", password="StrongPassword123!")
        response = self.client.post(
            reverse("services:unpublish", kwargs={"pk": self.service.pk})
        )
        self.assertRedirects(response, reverse("services:list"))
        self.service.refresh_from_db()
        self.assertFalse(self.service.is_published)

    def test_another_provider_cannot_publish_service(self):
        self.client.login(username="provider2", password="StrongPassword123!")
        response = self.client.post(
            reverse("services:publish", kwargs={"pk": self.service.pk})
        )
        self.assertEqual(response.status_code, 404)
        self.service.refresh_from_db()
        self.assertFalse(self.service.is_published)

    def test_another_provider_cannot_unpublish_service(self):
        self.service.is_published = True
        self.service.save()

        self.client.login(username="provider2", password="StrongPassword123!")
        response = self.client.post(
            reverse("services:unpublish", kwargs={"pk": self.service.pk})
        )
        self.assertEqual(response.status_code, 404)
        self.service.refresh_from_db()
        self.assertTrue(self.service.is_published)

    def test_get_request_cannot_publish_service(self):
        self.client.login(username="provider1", password="StrongPassword123!")
        response = self.client.get(
            reverse("services:publish", kwargs={"pk": self.service.pk})
        )
        self.assertEqual(response.status_code, 405)
        self.service.refresh_from_db()
        self.assertFalse(self.service.is_published)

    def test_get_request_cannot_unpublish_service(self):
        self.service.is_published = True
        self.service.save()

        self.client.login(username="provider1", password="StrongPassword123!")
        response = self.client.get(
            reverse("services:unpublish", kwargs={"pk": self.service.pk})
        )
        self.assertEqual(response.status_code, 405)
        self.service.refresh_from_db()
        self.assertTrue(self.service.is_published)

