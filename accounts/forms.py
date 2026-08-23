from django import forms
from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.forms import (
    AuthenticationForm,
    PasswordResetForm,
    SetPasswordForm,
    UserCreationForm,
)
from django.template import loader

from config.email_provider import send_email

from .models import User


class RegistrationForm(UserCreationForm):
    email = forms.EmailField(
        required=True,
    )

    role = forms.ChoiceField(
        choices=[
            (User.Role.CUSTOMER, "Customer"),
            (User.Role.PROVIDER, "Service Provider"),
        ],
    )

    class Meta:
        model = User
        fields = (
            "username",
            "email",
            "first_name",
            "last_name",
            "phone",
            "role",
            "password1",
            "password2",
        )


class LoginForm(AuthenticationForm):
    username = forms.CharField(
        label="Username or Email",
        widget=forms.TextInput(
            attrs={
                "class": "w-full rounded-lg border px-4 py-3",
                "placeholder": "Enter your username or email",
                "autocomplete": "username",
            }
        ),
    )

    password = forms.CharField(
        label="Password",
        widget=forms.PasswordInput(
            attrs={
                "class": "w-full rounded-lg border px-4 py-3",
                "placeholder": "Enter your password",
                "autocomplete": "current-password",
            }
        ),
    )

    def clean(self):
        identifier = self.cleaned_data.get("username")
        password = self.cleaned_data.get("password")

        if identifier is not None and password:
            username = self._resolve_auth_username(identifier)
            self.user_cache = authenticate(
                self.request,
                username=username,
                password=password,
            )
            if self.user_cache is None:
                raise self.get_invalid_login_error()
            self.confirm_login_allowed(self.user_cache)

        return self.cleaned_data

    def _resolve_auth_username(self, identifier):
        UserModel = get_user_model()

        if UserModel.objects.filter(username=identifier).exists():
            return identifier

        email_matches = UserModel.objects.filter(email__iexact=identifier)
        if email_matches.count() == 1:
            return email_matches.get().get_username()

        return identifier


class ProviaPasswordResetForm(PasswordResetForm):
    def send_mail(
        self,
        subject_template_name,
        email_template_name,
        context,
        from_email,
        to_email,
        html_email_template_name=None,
    ):
        """Render the reset email with Django's secure token/URL context, but
        deliver it through the centralized Brevo-aware email provider instead
        of Django's SMTP backend."""
        subject = loader.render_to_string(subject_template_name, context)
        # Email subject *must not* contain newlines.
        subject = "".join(subject.splitlines())
        body = loader.render_to_string(email_template_name, context)

        html = None
        if html_email_template_name is not None:
            html = loader.render_to_string(html_email_template_name, context)

        send_email(
            to=to_email,
            subject=subject,
            text=body,
            html=html,
            from_email=from_email,
        )


class ProviaSetPasswordForm(SetPasswordForm):
    pass


class ResendVerificationForm(forms.Form):
    email = forms.EmailField(
        required=True,
        label="Email address",
    )


class ProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = (
            "first_name",
            "last_name",
            "email",
            "phone",
        )

        widgets = {
            "first_name": forms.TextInput(
                attrs={
                    "class": "w-full rounded-lg border px-4 py-3",
                }
            ),
            "last_name": forms.TextInput(
                attrs={
                    "class": "w-full rounded-lg border px-4 py-3",
                }
            ),
            "email": forms.EmailInput(
                attrs={
                    "class": "w-full rounded-lg border px-4 py-3",
                }
            ),
            "phone": forms.TextInput(
                attrs={
                    "class": "w-full rounded-lg border px-4 py-3",
                }
            ),
        }
