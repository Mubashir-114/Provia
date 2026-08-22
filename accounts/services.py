from django.conf import settings
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode


class EmailVerificationService:

    @staticmethod
    def generate_token(user):
        return default_token_generator.make_token(user)

    @staticmethod
    def generate_uid(user):
        return urlsafe_base64_encode(force_bytes(user.pk))

    @classmethod
    def send_verification_email(cls, user, request):
        uid = cls.generate_uid(user)
        token = cls.generate_token(user)

        verification_path = reverse(
            "accounts:verify_email",
            kwargs={
                "uidb64": uid,
                "token": token,
            },
        )

        verification_url = request.build_absolute_uri(verification_path)

        message = render_to_string(
            "accounts/email_verification.txt",
            {
                "user": user,
                "verification_url": verification_url,
            },
        )

        html_message = render_to_string(
            "accounts/email_verification.html",
            {
                "user": user,
                "verification_url": verification_url,
            },
        )

        email = EmailMultiAlternatives(
            subject="Verify your Provia email",
            body=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[user.email],
        )

        email.attach_alternative(
            html_message,
            "text/html",
        )

        email.send(fail_silently=False)
