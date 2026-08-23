import unittest
from unittest import mock

from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse

from accounts.models import User


BREVO_PATH = "brevo.Brevo"


class BrevoFallbackTests(TestCase):
    """Without BREVO_API_KEY the provider must use Django's mail backend."""

    @override_settings(BREVO_API_KEY="")
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


@override_settings(BREVO_API_KEY="re_test_key_123")
class BrevoProviderTests(TestCase):
    def test_verification_email_sent_via_brevo(self):
        with mock.patch(BREVO_PATH) as mock_brevo_cls:
            mock_client = mock_brevo_cls.return_value
            mock_response = mock.MagicMock()
            mock_response.message_id = "email_abc"
            mock_client.transactional_emails.send_transac_email.return_value = mock_response

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
        self.assertEqual(
            mock_client.transactional_emails.send_transac_email.call_count, 1
        )

        kwargs = mock_client.transactional_emails.send_transac_email.call_args.kwargs
        self.assertEqual(kwargs["to"][0].email, "resend1@example.com")
        self.assertEqual(kwargs["subject"], "Verify your Provia email")
        self.assertIn("verify-email", kwargs["html_content"])
        self.assertTrue(kwargs["text_content"])
        self.assertEqual(kwargs["sender"].email, "provia11023012@gmail.com")
        self.assertEqual(kwargs["sender"].name, "Provia")
        # API key must never be placed in the message payload.
        self.assertNotIn("re_test_key_123", str(kwargs))

    def test_resend_verification_uses_brevo(self):
        user = User.objects.create_user(
            username="resend2",
            email="resend2@example.com",
            password="SecurePass123!",
            is_verified=False,
        )
        with mock.patch(BREVO_PATH) as mock_brevo_cls:
            mock_client = mock_brevo_cls.return_value
            mock_response = mock.MagicMock()
            mock_response.message_id = "email_def"
            mock_client.transactional_emails.send_transac_email.return_value = mock_response

            response = self.client.post(
                reverse("accounts:resend_verification"),
                {"email": "resend2@example.com"},
            )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            mock_client.transactional_emails.send_transac_email.call_count, 1
        )
        kwargs = mock_client.transactional_emails.send_transac_email.call_args.kwargs
        self.assertEqual(kwargs["to"][0].email, "resend2@example.com")
        self.assertEqual(kwargs["sender"].email, "provia11023012@gmail.com")
        self.assertEqual(kwargs["sender"].name, "Provia")


@override_settings(BREVO_API_KEY="re_test_key_123")
class BrevoFailureTests(TestCase):
    def test_registration_redirects_when_brevo_fails(self):
        with mock.patch(BREVO_PATH) as mock_brevo_cls:
            mock_client = mock_brevo_cls.return_value
            mock_client.transactional_emails.send_transac_email.side_effect = Exception(
                "boom"
            )
            with self.assertLogs("config.email_provider", level="ERROR") as logs:
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

    def test_resend_redirects_when_brevo_fails(self):
        User.objects.create_user(
            username="fail2",
            email="fail2@example.com",
            password="SecurePass123!",
            is_verified=False,
        )
        with mock.patch(BREVO_PATH) as mock_brevo_cls:
            mock_client = mock_brevo_cls.return_value
            mock_client.transactional_emails.send_transac_email.side_effect = Exception(
                "nope"
            )
            response = self.client.post(
                reverse("accounts:resend_verification"),
                {"email": "fail2@example.com"},
            )
        self.assertEqual(response.status_code, 302)
