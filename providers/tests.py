from django.test import TestCase
from django.urls import reverse

from accounts.models import User

from .models import ProviderProfile



class ProviderProfileTests(TestCase):

    def setUp(self):
        self.provider = User.objects.create_user(
            username="provider1",
            email="provider@example.com",
            password="StrongPassword123!",
            role=User.Role.PROVIDER,
            is_verified=True,
        )

        self.customer = User.objects.create_user(
            username="customer1",
            email="customer@example.com",
            password="StrongPassword123!",
            role=User.Role.CUSTOMER,
            is_verified=True,
        )

    def test_provider_can_access_profile_page(self):
        self.client.force_login(self.provider)

        response = self.client.get(reverse("providers:profile"))

        self.assertEqual(response.status_code, 200)

    def test_customer_cannot_access_provider_profile(self):
        self.client.force_login(self.customer)

        response = self.client.get(reverse("providers:profile"))

        self.assertEqual(response.status_code, 403)

    def test_provider_can_create_profile(self):
        self.client.force_login(self.provider)

        response = self.client.post(
            reverse("providers:profile"),
            {
                "business_name": "Provia Home Services",
                "business_description": "Professional home services.",
                "phone": "9876543210",
                "email": "business@example.com",
                "address": "123 Main Street",
                "city": "Kozhikode",
                "state": "Kerala",
                "postal_code": "673001",
            },
        )

        self.assertRedirects(
            response,
            reverse("providers:profile"),
        )

        profile = ProviderProfile.objects.get(user=self.provider)

        self.assertEqual(
            profile.business_name,
            "Provia Home Services",
        )

        self.assertEqual(
            profile.city,
            "Kozhikode",
        )

    def test_provider_can_update_existing_profile(self):
        profile = ProviderProfile.objects.create(
            user=self.provider,
            business_name="Old Business Name",
            city="Kozhikode",
        )

        self.client.force_login(self.provider)

        response = self.client.post(
            reverse("providers:profile"),
            {
                "business_name": "Updated Business Name",
                "business_description": "Updated description.",
                "phone": "9876543210",
                "email": "updated@example.com",
                "address": "456 New Street",
                "city": "Malappuram",
                "state": "Kerala",
                "postal_code": "676505",
            },
        )

        self.assertRedirects(
            response,
            reverse("providers:profile"),
        )

        profile.refresh_from_db()

        self.assertEqual(
            profile.business_name,
            "Updated Business Name",
        )

        self.assertEqual(
            profile.city,
            "Malappuram",
        )

    def test_customer_cannot_create_provider_profile(self):
        self.client.force_login(self.customer)

        response = self.client.post(
            reverse("providers:profile"),
            {
                "business_name": "Unauthorized Business",
            },
        )

        self.assertEqual(response.status_code, 403)

        self.assertFalse(
            ProviderProfile.objects.filter(
                business_name="Unauthorized Business"
            ).exists()
        )

    def test_anonymous_user_is_redirected_to_login(self):
        response = self.client.get(reverse("providers:profile"))

        self.assertEqual(response.status_code, 302)

        self.assertIn(
            "/accounts/login/",
            response.url,
        )

    def test_provider_profile_belongs_to_logged_in_provider(self):
        self.client.force_login(self.provider)

        self.client.post(
            reverse("providers:profile"),
            {
                "business_name": "Provider One",
                "business_description": "",
                "phone": "",
                "email": "",
                "address": "",
                "city": "",
                "state": "",
                "postal_code": "",
            },
        )

        profile = ProviderProfile.objects.get(user=self.provider)

        self.assertEqual(
            profile.user,
            self.provider,
        )
