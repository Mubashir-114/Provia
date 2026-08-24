from unittest import mock

from django.core.cache import cache
from django.test import TestCase, override_settings
from django.urls import reverse

from accounts.models import User


class PasswordResetProviderTests(TestCase):
    """Password reset email must go through config.email_provider.send_email."""

    def setUp(self):
        # LocMemCache persists across tests in the same process, so clear it
        # to avoid the password-reset rate limiter leaking between tests.
        cache.clear()

    def _make_user(self):
        return User.objects.create_user(
            username="reset_user",
            email="reset_user@example.com",
            password="OldPass12345!",
            is_verified=True,
        )

    def test_reset_uses_centralized_provider(self):
        self._make_user()
        with mock.patch("accounts.forms.send_email") as spy:
            response = self.client.post(
                reverse("accounts:password_reset"),
                {"email": "reset_user@example.com"},
            )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(spy.called)
        kwargs = spy.call_args.kwargs
        self.assertEqual(kwargs["to"], "reset_user@example.com")
        self.assertEqual(kwargs["subject"], "Provia password reset")
        # Reset URL with valid uid/token must be present in the email body.
        self.assertRegex(
            kwargs["text"],
            r"/accounts/password-reset/[^/]+/[^/]+/",
        )
        self.assertIsNotNone(kwargs["html"])

    def test_reset_payload_does_not_expose_api_key(self):
        self._make_user()
        with mock.patch("accounts.forms.send_email") as spy, override_settings(
            BREVO_API_KEY="re_secret_123"
        ):
            response = self.client.post(
                reverse("accounts:password_reset"),
                {"email": "reset_user@example.com"},
            )
        self.assertEqual(response.status_code, 302)
        payload = str(spy.call_args)
        self.assertNotIn("re_secret_123", payload)


class PasswordResetRateLimitTests(TestCase):
    """Password-reset requests are rate limited per client/IP."""

    def setUp(self):
        cache.clear()

    def _make_user(self):
        return User.objects.create_user(
            username="rate_user",
            email="rate_user@example.com",
            password="OldPass12345!",
            is_verified=True,
        )

    def test_emails_sent_up_to_limit_then_blocked(self):
        self._make_user()
        with mock.patch("accounts.forms.send_email") as spy:
            for _ in range(3):
                response = self.client.post(
                    reverse("accounts:password_reset"),
                    {"email": "rate_user@example.com"},
                )
                self.assertEqual(response.status_code, 302)
            # 4th request is rate limited: no email sent, same redirect.
            response = self.client.post(
                reverse("accounts:password_reset"),
                {"email": "rate_user@example.com"},
            )
            self.assertEqual(response.status_code, 302)
        self.assertEqual(spy.call_count, 3)

    def test_rate_limited_response_is_identical(self):
        self._make_user()
        with mock.patch("accounts.forms.send_email"):
            for _ in range(3):
                self.client.post(
                    reverse("accounts:password_reset"),
                    {"email": "rate_user@example.com"},
                )
            limited = self.client.post(
                reverse("accounts:password_reset"),
                {"email": "rate_user@example.com"},
            )
        # The rate-limited request must still redirect to the generic done page.
        self.assertEqual(limited.status_code, 302)
        self.assertEqual(
            limited.url,
            "/accounts/password-reset/done/",
        )


@override_settings(BREVO_API_KEY="re_test_key_456")
class PasswordResetBrevoPathTests(TestCase):
    def setUp(self):
        # LocMemCache persists across tests in the same process, so clear it
        # to avoid the password-reset rate limiter leaking between tests.
        cache.clear()

    def _make_user(self, username, email):
        return User.objects.create_user(
            username=username,
            email=email,
            password="OldPass12345!",
            is_verified=True,
        )

    def test_reset_uses_brevo_when_key_configured(self):
        self._make_user("reset2", "reset2@example.com")
        with mock.patch("brevo.Brevo") as mock_brevo_cls:
            mock_client = mock_brevo_cls.return_value
            mock_response = mock.MagicMock()
            mock_response.message_id = "email_xyz"
            mock_client.transactional_emails.send_transac_email.return_value = mock_response

            response = self.client.post(
                reverse("accounts:password_reset"),
                {"email": "reset2@example.com"},
            )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            mock_client.transactional_emails.send_transac_email.call_count, 1
        )
        kwargs = mock_client.transactional_emails.send_transac_email.call_args.kwargs
        self.assertEqual(kwargs["to"][0].email, "reset2@example.com")
        self.assertEqual(kwargs["subject"], "Provia password reset")
        self.assertEqual(kwargs["sender"].email, "provia11023012@gmail.com")
        self.assertEqual(kwargs["sender"].name, "Provia")
        self.assertRegex(
            kwargs["text_content"],
            r"/accounts/password-reset/[^/]+/[^/]+/",
        )
        self.assertNotIn("re_test_key_456", str(kwargs))

    def test_reset_redirects_when_brevo_fails(self):
        self._make_user("reset3", "reset3@example.com")
        with mock.patch("brevo.Brevo") as mock_brevo_cls, self.assertLogs(
            "config.email_provider", level="ERROR"
        ) as logs:
            mock_client = mock_brevo_cls.return_value
            mock_client.transactional_emails.send_transac_email.side_effect = Exception(
                "network down"
            )
            response = self.client.post(
                reverse("accounts:password_reset"),
                {"email": "reset3@example.com"},
            )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(any("network down" in line for line in logs.output))
        # API key must never appear in logs.
        self.assertFalse(any("re_test_key_456" in line for line in logs.output))
