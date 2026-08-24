from django.test import TestCase
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile

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


class ProviderProfileImageTests(TestCase):
    def setUp(self):
        self.provider = User.objects.create_user(
            username="provider_img_user",
            email="provider_img@example.com",
            password="StrongPassword123!",
            role=User.Role.PROVIDER,
            is_verified=True,
        )
        self.profile = ProviderProfile.objects.create(
            user=self.provider,
            business_name="Test Provider",
        )

    def _create_test_image(self, fmt="JPEG"):
        from PIL import Image
        import io

        image = Image.new("RGB", (100, 100), color="blue")
        image_file = io.BytesIO()
        image.save(image_file, fmt)
        image_file.seek(0)
        return image_file.read(), "image/jpeg" if fmt == "JPEG" else f"image/{fmt.lower()}"

    def _mock_cloudinary_upload(self):
        from unittest.mock import patch

        return patch("cloudinary.uploader.upload")

    def test_provider_can_upload_profile_image(self):
        self.client.force_login(self.provider)

        image_data, content_type = self._create_test_image()

        with self._mock_cloudinary_upload() as mock_upload:
            mock_upload.return_value = {
                "public_id": "provider_test_id",
                "version": 1234567890,
                "format": "jpg",
                "resource_type": "image",
                "type": "upload",
            }
            response = self.client.post(
                reverse("providers:profile"),
                {
                    "business_name": "Provia Home Services",
                    "business_description": "",
                    "phone": "",
                    "email": "",
                    "address": "",
                    "city": "",
                    "state": "",
                    "postal_code": "",
                    "profile_picture": SimpleUploadedFile(
                        "test.jpg", image_data, content_type=content_type
                    ),
                },
            )

        self.assertRedirects(response, reverse("providers:profile"))
        profile = ProviderProfile.objects.get(user=self.provider)
        self.assertTrue(bool(profile.profile_picture))

    def test_provider_cannot_modify_another_provider_image(self):
        other_provider = User.objects.create_user(
            username="other_provider",
            email="other@example.com",
            password="StrongPassword123!",
            role=User.Role.PROVIDER,
            is_verified=True,
        )
        ProviderProfile.objects.create(
            user=other_provider,
            business_name="Other Business",
        )

        self.client.force_login(self.provider)

        response = self.client.post(
            reverse("providers:profile"),
            {
                "business_name": "Other Business",
                "business_description": "",
                "phone": "",
                "email": "",
                "address": "",
                "city": "",
                "state": "",
                "postal_code": "",
                "profile_picture": SimpleUploadedFile(
                    "hack.jpg", b"fakeimage", content_type="image/jpeg"
                ),
            },
        )
        self.assertEqual(response.status_code, 200)
        profile = ProviderProfile.objects.get(user=other_provider)
        self.assertFalse(bool(profile.profile_picture))

    def test_unsupported_image_type_is_rejected(self):
        self.client.force_login(self.provider)

        response = self.client.post(
            reverse("providers:profile"),
            {
                "business_name": "Provia Home Services",
                "business_description": "",
                "phone": "",
                "email": "",
                "address": "",
                "city": "",
                "state": "",
                "postal_code": "",
                "profile_picture": SimpleUploadedFile(
                    "test.txt", b"not an image", content_type="text/plain"
                ),
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("profile_picture", response.context["form"].errors)

    def test_oversized_image_is_rejected(self):
        self.client.force_login(self.provider)

        response = self.client.post(
            reverse("providers:profile"),
            {
                "business_name": "Provia Home Services",
                "business_description": "",
                "phone": "",
                "email": "",
                "address": "",
                "city": "",
                "state": "",
                "postal_code": "",
                "profile_picture": SimpleUploadedFile(
                    "big.jpg", b"x" * (5 * 1024 * 1024 + 1), content_type="image/jpeg"
                ),
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("profile_picture", response.context["form"].errors)

    def test_existing_profile_without_image_continues_to_work(self):
        self.client.force_login(self.provider)

        response = self.client.get(reverse("providers:profile"))
        self.assertEqual(response.status_code, 200)
        profile = ProviderProfile.objects.get(user=self.provider)
        self.assertFalse(bool(profile.profile_picture))

    def test_image_field_can_be_replaced_safely(self):
        profile = self.profile
        self.client.force_login(self.provider)

        image_data, content_type = self._create_test_image()

        with self._mock_cloudinary_upload() as mock_upload:
            mock_upload.return_value = {
                "public_id": "replace_test_id",
                "version": 1234567890,
                "format": "jpg",
                "resource_type": "image",
                "type": "upload",
            }
            response = self.client.post(
                reverse("providers:profile"),
                {
                    "business_name": "Replace Test",
                    "business_description": "",
                    "phone": "",
                    "email": "",
                    "address": "",
                    "city": "",
                    "state": "",
                    "postal_code": "",
                    "profile_picture": SimpleUploadedFile(
                        "test.jpg", image_data, content_type=content_type
                    ),
                },
            )

        self.assertRedirects(response, reverse("providers:profile"))
        profile.refresh_from_db()
        self.assertTrue(bool(profile.profile_picture))

        new_image_data, _ = self._create_test_image(fmt="PNG")

        with self._mock_cloudinary_upload() as mock_upload:
            mock_upload.return_value = {
                "public_id": "replace_test_id_v2",
                "version": 1234567891,
                "format": "png",
                "resource_type": "image",
                "type": "upload",
            }
            response = self.client.post(
                reverse("providers:profile"),
                {
                    "business_name": "Replace Test",
                    "business_description": "",
                    "phone": "",
                    "email": "",
                    "address": "",
                    "city": "",
                    "state": "",
                    "postal_code": "",
                    "profile_picture": SimpleUploadedFile(
                        "test.png", new_image_data, content_type="image/png"
                    ),
                },
            )

        self.assertRedirects(response, reverse("providers:profile"))
        profile.refresh_from_db()
        self.assertTrue(bool(profile.profile_picture))
