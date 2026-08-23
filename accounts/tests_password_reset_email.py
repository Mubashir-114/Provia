from unittest import mock

from django.test import TestCase, override_settings
from django.urls import reverse

from accounts.models import User


class PasswordResetProviderTests(TestCase):
    """Password reset email must go through config.email_provider.send_email."""

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
            RESEND_API_KEY="re_secret_123"
        ):
            response = self.client.post(
                reverse("accounts:password_reset"),
                {"email": "reset_user@example.com"},
            )
        self.assertEqual(response.status_code, 302)
        payload = str(spy.call_args)
        self.assertNotIn("re_secret_123", payload)


class PasswordResetResendPathTests(TestCase):
    def _make_user(self, username, email):
        return User.objects.create_user(
            username=username,
            email=email,
            password="OldPass12345!",
            is_verified=True,
        )

    def test_reset_uses_resend_when_key_configured(self):
        self._make_user("reset2", "reset2@example.com")
        with override_settings(RESEND_API_KEY="re_test_key_456"), mock.patch(
            "resend.Emails.send", return_value={"id": "email_xyz"}
        ) as send:
            response = self.client.post(
                reverse("accounts:password_reset"),
                {"email": "reset2@example.com"},
            )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(send.call_count, 1)
        params = send.call_args.args[0]
        self.assertEqual(params["to"], ["reset2@example.com"])
        self.assertEqual(params["subject"], "Provia password reset")
        self.assertRegex(
            params["text"],
            r"/accounts/password-reset/[^/]+/[^/]+/",
        )
        self.assertNotIn("re_test_key_456", str(params))

    def test_reset_redirects_when_resend_fails(self):
        self._make_user("reset3", "reset3@example.com")
        with override_settings(RESEND_API_KEY="re_test_key_456"), mock.patch(
            "resend.Emails.send", side_effect=Exception("network down")
        ), self.assertLogs("config.email_provider", level="ERROR") as logs:
            response = self.client.post(
                reverse("accounts:password_reset"),
                {"email": "reset3@example.com"},
            )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(any("network down" in line for line in logs.output))
        # API key must never appear in logs.
        self.assertFalse(any("re_test_key_456" in line for line in logs.output))
