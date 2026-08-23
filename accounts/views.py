import logging
from urllib.parse import urlparse

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.contrib.auth.tokens import default_token_generator
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.urls import reverse
from django.utils.http import urlsafe_base64_decode, url_has_allowed_host_and_scheme
from accounts.services import EmailVerificationService

from django.contrib.auth.forms import PasswordResetForm, SetPasswordForm

from .forms import RegistrationForm, LoginForm, ResendVerificationForm, ProfileForm

logger = logging.getLogger(__name__)


def register_view(request):
    if request.user.is_authenticated:
        return redirect("home")

    if request.method == "POST":
        form = RegistrationForm(request.POST)

        if form.is_valid():
            user = form.save()

            try:
                EmailVerificationService.send_verification_email(
                    user=user,
                    request=request,
                )
            except Exception:
                logger.exception(
                    "Failed to send verification email for new user %s",
                    user.pk,
                )

            messages.success(
                request,
                "Account created successfully. "
                "Please check your email to verify your account.",
            )

            return redirect("accounts:verification_sent")

    else:
        form = RegistrationForm()

    return render(
        request,
        "accounts/register.html",
        {"form": form},
    )


def login_view(request):
    form = LoginForm(
        request=request,
        data=request.POST or None,
    )

    if request.method == "POST" and form.is_valid():
        user = form.get_user()
        if not user.is_verified:
            messages.error(
                request,
                "Please verify your email before logging in.",
            )
            return render(
                request,
                "accounts/login.html",
                {"form": form},
            )

        login(request, user)

        next_url = request.POST.get("next") or request.GET.get("next")

        blocked_next_paths = {
            reverse("accounts:login"),
            reverse("accounts:logout"),
        }

        if (
            next_url
            and urlparse(next_url).path not in blocked_next_paths
            and url_has_allowed_host_and_scheme(
                url=next_url,
                allowed_hosts={request.get_host()},
                require_https=request.is_secure(),
            )
        ):
            return redirect(next_url)

        if user.role == user.Role.PROVIDER:
            return redirect("dashboard:provider")

        if user.role == user.Role.ADMIN:
            return redirect("/admin/")

        return redirect("dashboard:customer")

    return render(
        request,
        "accounts/login.html",
        {"form": form},
    )


@login_required
def logout_view(request):
    logout(request)

    messages.success(
        request,
        "You have been logged out successfully.",
    )

    return redirect("home")


def verify_email(request, uidb64, token):
    User = get_user_model()

    try:
        uid = urlsafe_base64_decode(uidb64).decode()
        user = User.objects.get(pk=uid)
    except (
        TypeError,
        ValueError,
        OverflowError,
        ValidationError,
        User.DoesNotExist,
    ):
        user = None

    if user is None:
        return render(
            request,
            "accounts/email_verification_invalid.html",
        )

    if user.is_verified:
        return render(
            request,
            "accounts/email_already_verified.html",
        )

    if not default_token_generator.check_token(user, token):
        return render(
            request,
            "accounts/email_verification_invalid.html",
        )

    user.is_verified = True
    user.save(update_fields=["is_verified"])

    return render(
        request,
        "accounts/email_verified.html",
    )


def verification_sent(request):
    return render(
        request,
        "accounts/verification_sent.html",
    )


def resend_verification(request):
    User = get_user_model()

    if request.method == "POST":
        form = ResendVerificationForm(request.POST)

        if form.is_valid():
            email = form.cleaned_data["email"]

            user = User.objects.filter(
                email=email,
                is_active=True,
            ).first()

            if user and not user.is_verified:
                try:
                    EmailVerificationService.send_verification_email(
                        user=user,
                        request=request,
                    )
                except Exception:
                    logger.exception(
                        "Failed to resend verification email for user %s",
                        user.pk,
                    )

            return redirect("accounts:verification_sent")

    else:
        form = ResendVerificationForm()

    return render(
        request,
        "accounts/resend_verification.html",
        {"form": form},
    )


@login_required
def profile_view(request):
    if request.method == "POST":
        form = ProfileForm(
            request.POST,
            instance=request.user,
        )

        if form.is_valid():
            form.save()

            messages.success(
                request,
                "Your profile has been updated successfully.",
            )

            return redirect("accounts:profile")

    else:
        form = ProfileForm(
            instance=request.user,
        )

    return render(
        request,
        "accounts/profile.html",
        {"form": form},
    )
