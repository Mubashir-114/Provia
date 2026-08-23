import unittest
from unittest import mock

from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse

from accounts.models import User


RESEND_PATH = "resend.Emails.send"


class ResendFallbackTests(TestCase):
    """Without RESEND_API_KEY the provider must use Django's mail backend."""

    def test_no_key_uses_django_backend(self):
        response = self.client.post(
            reverse("accounts:register"),
            {
                "username": "fallback1",
                "email": "fallback1@example.com",
                "first_name": "Fall",
                "last_name": "Back",
                "phone": "1234567890",
                "role": User.Role.CUSTOMER,
                "password1": "SecurePass123!",
                "password2": "SecurePass123!",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["fallback1@example.com"])
        self.assertEqual(mail.outbox[0].subject, "Verify your Provia email")


@override_settings(RESEND_API_KEY="re_test_key_123")
class ResendProviderTests(TestCase):
    def test_verification_email_sent_via_resend(self):
        with mock.patch(RESEND_PATH, return_value={"id": "email_abc"}) as send:
            response = self.client.post(
                reverse("accounts:register"),
                {
                    "username": "resend1",
                    "email": "resend1@example.com",
                    "first_name": "Re",
                    "last_name": "Send",
                    "phone": "1234567890",
                    "role": User.Role.CUSTOMER,
                    "password1": "SecurePass123!",
                    "password2": "SecurePass123!",
                },
            )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(send.call_count, 1)

        params = send.call_args.args[0]
        self.assertEqual(params["to"], ["resend1@example.com"])
        self.assertEqual(params["subject"], "Verify your Provia email")
        self.assertIn("verify-email", params["html"])
        self.assertTrue(params["text"])
        # API key must never be placed in the message payload.
        self.assertNotIn("re_test_key_123", str(params))

    def test_resend_verification_uses_resend(self):
        user = User.objects.create_user(
            username="resend2",
            email="resend2@example.com",
            password="SecurePass123!",
            is_verified=False,
        )
        with mock.patch(RESEND_PATH, return_value={"id": "email_def"}) as send:
            response = self.client.post(
                reverse("accounts:resend_verification"),
                {"email": "resend2@example.com"},
            )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(send.call_count, 1)
        self.assertEqual(send.call_args.args[0]["to"], ["resend2@example.com"])


@override_settings(RESEND_API_KEY="re_test_key_123")
class ResendFailureTests(TestCase):
    def test_registration_redirects_when_resend_fails(self):
        with mock.patch(RESEND_PATH, side_effect=Exception("boom")), self.assertLogs(
            "config.email_provider", level="ERROR"
        ) as logs:
            response = self.client.post(
                reverse("accounts:register"),
                {
                    "username": "fail1",
                    "email": "fail1@example.com",
                    "first_name": "Fail",
                    "last_name": "One",
                    "phone": "1234567890",
                    "role": User.Role.CUSTOMER,
                    "password1": "SecurePass123!",
                    "password2": "SecurePass123!",
                },
            )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(any("boom" in line for line in logs.output))
        self.assertFalse(any("re_test_key_123" in line for line in logs.output))

    def test_resend_redirects_when_resend_fails(self):
        User.objects.create_user(
            username="fail2",
            email="fail2@example.com",
            password="SecurePass123!",
            is_verified=False,
        )
        with mock.patch(RESEND_PATH, side_effect=Exception("nope")):
            response = self.client.post(
                reverse("accounts:resend_verification"),
                {"email": "fail2@example.com"},
            )
        self.assertEqual(response.status_code, 302)
