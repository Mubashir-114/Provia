import re

from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.core.management import call_command
from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from providers.models import ProviderProfile

User = get_user_model()


@override_settings(DEBUG=True)
class SetupDevUsersCommandTests(TestCase):

    customer_password = "CustomerDevTest123!"
    provider_password = "ProviderDevTest123!"

    def run_setup_command(self):
        call_command(
            "setup_dev_users",
            customer_password=self.customer_password,
            provider_password=self.provider_password,
        )

    def test_creates_users_and_provider_profile(self):
        self.run_setup_command()

        customer = User.objects.get(username="Mubashir")
        provider = User.objects.get(username="MehnaA")

        self.assertEqual(customer.role, User.Role.CUSTOMER)
        self.assertTrue(customer.is_active)
        self.assertTrue(customer.is_verified)
        self.assertEqual(provider.role, User.Role.PROVIDER)
        self.assertTrue(provider.is_active)
        self.assertTrue(provider.is_verified)
        self.assertTrue(provider.check_password(self.provider_password))
        self.assertIsNotNone(provider.provider_profile)

    def test_is_idempotent_and_does_not_modify_unrelated_users(self):
        unrelated = User.objects.create_user(
            username="unrelated_dev_user",
            email="unrelated@example.com",
            password="UnrelatedPass123!",
            role=User.Role.CUSTOMER,
            is_active=False,
            is_verified=False,
        )

        self.run_setup_command()
        self.run_setup_command()

        self.assertEqual(User.objects.filter(username="Mubashir").count(), 1)
        self.assertEqual(User.objects.filter(username="MehnaA").count(), 1)
        unrelated.refresh_from_db()
        self.assertFalse(unrelated.is_active)
        self.assertFalse(unrelated.is_verified)
        self.assertEqual(unrelated.role, User.Role.CUSTOMER)
        self.assertTrue(unrelated.check_password("UnrelatedPass123!"))

    def test_passwords_work_with_django_authentication(self):
        self.run_setup_command()

        self.assertIsNotNone(
            authenticate(
                username="Mubashir",
                password=self.customer_password,
            )
        )
        self.assertIsNotNone(
            authenticate(
                username="MehnaA",
                password=self.provider_password,
            )
        )

    @override_settings(DEBUG=False)
    def test_command_is_disabled_when_debug_is_false(self):
        from django.core.management import CommandError

        with self.assertRaises(CommandError):
            self.run_setup_command()


@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    ALLOWED_HOSTS=["testserver"],
)
class Phase2AuthenticationTests(TestCase):

    def test_01_customer_registration(self):
        response = self.client.post(
            reverse("accounts:register"),
            {
                "username": "customer1",
                "email": "customer1@example.com",
                "first_name": "Jane",
                "last_name": "Doe",
                "phone": "1234567890",
                "role": User.Role.CUSTOMER,
                "password1": "SecurePass123!",
                "password2": "SecurePass123!",
            },
        )
        self.assertRedirects(response, reverse("accounts:verification_sent"))
        user = User.objects.get(username="customer1")
        self.assertEqual(user.role, User.Role.CUSTOMER)
        self.assertFalse(user.is_verified)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("customer1@example.com", mail.outbox[0].to)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_02_provider_registration(self):
        response = self.client.post(
            reverse("accounts:register"),
            {
                "username": "provider1",
                "email": "provider1@example.com",
                "first_name": "John",
                "last_name": "Smith",
                "phone": "9876543210",
                "role": User.Role.PROVIDER,
                "password1": "SecurePass123!",
                "password2": "SecurePass123!",
            },
        )
        self.assertRedirects(response, reverse("accounts:verification_sent"))
        user = User.objects.get(username="provider1")
        self.assertEqual(user.role, User.Role.PROVIDER)
        self.assertFalse(user.is_verified)
        self.assertEqual(len(mail.outbox), 1)

    def test_03_admin_cannot_register(self):
        response = self.client.post(
            reverse("accounts:register"),
            {
                "username": "fakeadmin",
                "email": "fakeadmin@example.com",
                "first_name": "Fake",
                "last_name": "Admin",
                "phone": "1234567890",
                "role": User.Role.ADMIN,
                "password1": "SecurePass123!",
                "password2": "SecurePass123!",
            },
        )
        self.assertEqual(response.status_code, 200)
        form = response.context["form"]
        self.assertIn("role", form.errors)
        self.assertFalse(User.objects.filter(username="fakeadmin").exists())

    def test_04_new_users_start_unverified(self):
        user = User.objects.create_user(
            username="testuser",
            email="testuser@example.com",
            password="UserPass123!",
        )
        self.assertFalse(user.is_verified)

    def test_05_verification_changes_is_verified_to_true(self):
        user = User.objects.create_user(
            username="unverified_user",
            email="unverified@example.com",
            password="UserPass123!",
            is_verified=False,
        )
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)

        url = reverse(
            "accounts:verify_email",
            kwargs={"uidb64": uid, "token": token},
        )
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "accounts/email_verified.html")
        user.refresh_from_db()
        self.assertTrue(user.is_verified)

    def test_06_invalid_verification_token_rejected(self):
        user = User.objects.create_user(
            username="unverified_user2",
            email="unverified2@example.com",
            password="UserPass123!",
            is_verified=False,
        )
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        invalid_token = "invalid-token-123"

        url = reverse(
            "accounts:verify_email",
            kwargs={"uidb64": uid, "token": invalid_token},
        )
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(
            response, "accounts/email_verification_invalid.html"
        )
        user.refresh_from_db()
        self.assertFalse(user.is_verified)

        # Invalid UID test
        invalid_url = reverse(
            "accounts:verify_email",
            kwargs={"uidb64": "invaliduid", "token": "invalidtoken"},
        )
        invalid_resp = self.client.get(invalid_url)
        self.assertEqual(invalid_resp.status_code, 200)
        self.assertTemplateUsed(
            invalid_resp, "accounts/email_verification_invalid.html"
        )

    def test_07_already_verified_user_handled_correctly(self):
        user = User.objects.create_user(
            username="already_verified",
            email="verified@example.com",
            password="UserPass123!",
            is_verified=True,
        )
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)

        url = reverse(
            "accounts:verify_email",
            kwargs={"uidb64": uid, "token": token},
        )
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(
            response, "accounts/email_already_verified.html"
        )

    def test_08_resend_verification(self):
        # 1. Unverified user -> sends email
        unverified = User.objects.create_user(
            username="resend_unverified",
            email="resend_unverified@example.com",
            password="UserPass123!",
            is_verified=False,
        )
        mail.outbox.clear()
        response = self.client.post(
            reverse("accounts:resend_verification"),
            {"email": unverified.email},
        )
        self.assertRedirects(response, reverse("accounts:verification_sent"))
        self.assertEqual(len(mail.outbox), 1)

        # 2. Verified user -> does not send email
        verified = User.objects.create_user(
            username="resend_verified",
            email="resend_verified@example.com",
            password="UserPass123!",
            is_verified=True,
        )
        mail.outbox.clear()
        response2 = self.client.post(
            reverse("accounts:resend_verification"),
            {"email": verified.email},
        )
        self.assertRedirects(response2, reverse("accounts:verification_sent"))
        self.assertEqual(len(mail.outbox), 0)

        # 3. Unknown email -> does not send email, safe redirect
        mail.outbox.clear()
        response3 = self.client.post(
            reverse("accounts:resend_verification"),
            {"email": "unknown@example.com"},
        )
        self.assertRedirects(response3, reverse("accounts:verification_sent"))
        self.assertEqual(len(mail.outbox), 0)

    def test_09_unverified_user_login_rejected(self):
        User.objects.create_user(
            username="unverified_login",
            email="unverified_login@example.com",
            password="UserPass123!",
            is_verified=False,
        )
        response = self.client.post(
            reverse("accounts:login"),
            {
                "username": "unverified_login",
                "password": "UserPass123!",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_10_verified_customer_login(self):
        User.objects.create_user(
            username="verified_customer",
            email="customer@example.com",
            password="UserPass123!",
            role=User.Role.CUSTOMER,
            is_verified=True,
        )
        response = self.client.post(
            reverse("accounts:login"),
            {
                "username": "verified_customer",
                "password": "UserPass123!",
            },
        )
        self.assertRedirects(response, reverse("dashboard:customer"))
        self.assertIn("_auth_user_id", self.client.session)

    def test_11_verified_provider_login(self):
        provider_user = User.objects.create_user(
            username="verified_provider",
            email="provider@example.com",
            password="UserPass123!",
            role=User.Role.PROVIDER,
            is_verified=True,
        )
        ProviderProfile.objects.create(
            user=provider_user,
            business_name="Test Provider",
            email="provider@example.com",
        )
        response = self.client.post(
            reverse("accounts:login"),
            {
                "username": "verified_provider",
                "password": "UserPass123!",
            },
        )
        self.assertRedirects(response, reverse("dashboard:provider"))
        self.assertIn("_auth_user_id", self.client.session)

    def test_11a_verified_customer_can_login_with_email(self):
        User.objects.create_user(
            username="email_customer",
            email="email_customer@example.com",
            password="UserPass123!",
            role=User.Role.CUSTOMER,
            is_verified=True,
        )
        response = self.client.post(
            reverse("accounts:login"),
            {
                "username": "email_customer@example.com",
                "password": "UserPass123!",
            },
        )
        self.assertRedirects(response, reverse("dashboard:customer"))
        self.assertIn("_auth_user_id", self.client.session)

    def test_11b_verified_provider_can_login_with_email(self):
        provider_user = User.objects.create_user(
            username="email_provider",
            email="email_provider@example.com",
            password="UserPass123!",
            role=User.Role.PROVIDER,
            is_verified=True,
        )
        ProviderProfile.objects.create(
            user=provider_user,
            business_name="Email Provider",
            email="email_provider@example.com",
        )
        response = self.client.post(
            reverse("accounts:login"),
            {
                "username": "email_provider@example.com",
                "password": "UserPass123!",
            },
        )
        self.assertRedirects(response, reverse("dashboard:provider"))
        self.assertIn("_auth_user_id", self.client.session)

    def test_12_invalid_login_rejected(self):
        User.objects.create_user(
            username="valid_user",
            email="valid@example.com",
            password="UserPass123!",
            is_verified=True,
        )
        response = self.client.post(
            reverse("accounts:login"),
            {
                "username": "valid_user",
                "password": "WrongPassword!",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_12a_unknown_username_rejected(self):
        response = self.client.post(
            reverse("accounts:login"),
            {
                "username": "unknown_user",
                "password": "UserPass123!",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_13_inactive_user_login_rejected(self):
        User.objects.create_user(
            username="inactive_user",
            email="inactive@example.com",
            password="UserPass123!",
            is_verified=True,
            is_active=False,
        )
        response = self.client.post(
            reverse("accounts:login"),
            {
                "username": "inactive_user",
                "password": "UserPass123!",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_13a_admin_login_redirects_to_admin(self):
        User.objects.create_user(
            username="admin_user",
            email="admin@example.com",
            password="UserPass123!",
            role=User.Role.ADMIN,
            is_verified=True,
            is_staff=True,
        )
        response = self.client.post(
            reverse("accounts:login"),
            {
                "username": "admin_user",
                "password": "UserPass123!",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], "/admin/")
        self.assertIn("_auth_user_id", self.client.session)

    def test_13b_safe_next_url_is_used_after_login(self):
        User.objects.create_user(
            username="next_customer",
            email="next_customer@example.com",
            password="UserPass123!",
            role=User.Role.CUSTOMER,
            is_verified=True,
        )
        response = self.client.post(
            f"{reverse('accounts:login')}?next={reverse('accounts:profile')}",
            {
                "username": "next_customer",
                "password": "UserPass123!",
            },
        )
        self.assertRedirects(response, reverse("accounts:profile"))
        self.assertIn("_auth_user_id", self.client.session)

    def test_13c_unsafe_next_url_falls_back_to_role_dashboard(self):
        User.objects.create_user(
            username="unsafe_next_customer",
            email="unsafe_next_customer@example.com",
            password="UserPass123!",
            role=User.Role.CUSTOMER,
            is_verified=True,
        )
        response = self.client.post(
            f"{reverse('accounts:login')}?next=https://evil.example/dashboard/",
            {
                "username": "unsafe_next_customer",
                "password": "UserPass123!",
            },
        )
        self.assertRedirects(response, reverse("dashboard:customer"))
        self.assertIn("_auth_user_id", self.client.session)

    @override_settings(DEBUG=True)
    def test_13d_development_users_login_through_endpoint(self):
        call_command("setup_dev_users")

        self.assertIsNotNone(
            authenticate(
                username="Mubashir",
                password="ProviaCustomerDev2026!",
            )
        )
        self.assertIsNotNone(
            authenticate(
                username="MehnaA",
                password="ProviaProviderDev2026!",
            )
        )

        response = self.client.post(
            reverse("accounts:login"),
            {
                "username": "MehnaA",
                "password": "ProviaProviderDev2026!",
            },
        )
        self.assertRedirects(response, reverse("dashboard:provider"))

        self.client.post(reverse("accounts:logout"))

        response = self.client.post(
            reverse("accounts:login"),
            {
                "username": "Mubashir",
                "password": "ProviaCustomerDev2026!",
            },
        )
        self.assertRedirects(response, reverse("dashboard:customer"))

    def test_14_customer_cannot_access_provider_dashboard(self):
        customer = User.objects.create_user(
            username="cust_dash",
            email="cust_dash@example.com",
            password="UserPass123!",
            role=User.Role.CUSTOMER,
            is_verified=True,
        )
        self.client.force_login(customer)
        response = self.client.get(reverse("dashboard:provider"))
        self.assertEqual(response.status_code, 403)

    def test_15_provider_cannot_access_customer_dashboard(self):
        provider = User.objects.create_user(
            username="prov_dash",
            email="prov_dash@example.com",
            password="UserPass123!",
            role=User.Role.PROVIDER,
            is_verified=True,
        )
        self.client.force_login(provider)
        response = self.client.get(reverse("dashboard:customer"))
        self.assertEqual(response.status_code, 403)

    def test_16_anonymous_dashboard_access_redirects_to_login(self):
        response = self.client.get(reverse("dashboard:customer"))
        self.assertRedirects(
            response, "/accounts/login/?next=/dashboard/customer/"
        )

        response_prov = self.client.get(reverse("dashboard:provider"))
        self.assertRedirects(
            response_prov, "/accounts/login/?next=/dashboard/provider/"
        )

    def test_17_password_reset_flow(self):
        user = User.objects.create_user(
            username="reset_user",
            email="reset_user@example.com",
            password="OldPass12345!",
            is_verified=True,
        )

        mail.outbox.clear()
        response = self.client.post(
            reverse("accounts:password_reset"),
            {"email": user.email},
        )
        self.assertRedirects(
            response, reverse("accounts:password_reset_done")
        )
        self.assertEqual(len(mail.outbox), 1)

        match = re.search(
            r"/accounts/password-reset/(?P<uidb64>[^/]+)/(?P<token>[^/]+)/",
            mail.outbox[0].body,
        )
        self.assertIsNotNone(match)

        confirm_url = reverse(
            "accounts:password_reset_confirm",
            kwargs=match.groupdict(),
        )
        response = self.client.get(confirm_url)
        self.assertEqual(response.status_code, 302)

        set_pass_url = response["Location"]
        response = self.client.get(set_pass_url)
        self.assertEqual(response.status_code, 200)

        response = self.client.post(
            set_pass_url,
            {
                "new_password1": "NewPass12345!",
                "new_password2": "NewPass12345!",
            },
        )
        self.assertRedirects(
            response, reverse("accounts:password_reset_complete")
        )
        user.refresh_from_db()
        self.assertFalse(user.check_password("OldPass12345!"))
        self.assertTrue(user.check_password("NewPass12345!"))
        self.assertIsNone(
            authenticate(username=user.username, password="OldPass12345!")
        )
        self.assertEqual(
            authenticate(username=user.username, password="NewPass12345!"),
            user,
        )

    def test_18_profile_requires_authentication(self):
        response = self.client.get(reverse("accounts:profile"))
        self.assertRedirects(
            response, "/accounts/login/?next=/accounts/profile/"
        )

    def test_19_profile_update_works(self):
        user = User.objects.create_user(
            username="profile_user",
            email="old_email@example.com",
            password="UserPass123!",
            first_name="OldFirst",
            last_name="OldLast",
            phone="1111111111",
            is_verified=True,
        )
        self.client.force_login(user)

        response = self.client.post(
            reverse("accounts:profile"),
            {
                "first_name": "NewFirst",
                "last_name": "NewLast",
                "email": "new_email@example.com",
                "phone": "9999999999",
            },
        )
        self.assertRedirects(response, reverse("accounts:profile"))
        user.refresh_from_db()
        self.assertEqual(user.first_name, "NewFirst")
        self.assertEqual(user.last_name, "NewLast")
        self.assertEqual(user.email, "new_email@example.com")
        self.assertEqual(user.phone, "9999999999")

    def test_20_profile_form_cannot_modify_role_or_is_verified(self):
        user = User.objects.create_user(
            username="tamper_user",
            email="tamper@example.com",
            password="UserPass123!",
            role=User.Role.CUSTOMER,
            is_verified=True,
            is_staff=False,
            is_superuser=False,
        )
        self.client.force_login(user)

        response = self.client.post(
            reverse("accounts:profile"),
            {
                "first_name": "Tamper",
                "last_name": "User",
                "email": "tamper@example.com",
                "phone": "5555555555",
                "role": User.Role.ADMIN,
                "is_verified": False,
                "is_staff": True,
                "is_superuser": True,
            },
        )
        self.assertRedirects(response, reverse("accounts:profile"))
        user.refresh_from_db()
        self.assertEqual(user.role, User.Role.CUSTOMER)
        self.assertTrue(user.is_verified)
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
