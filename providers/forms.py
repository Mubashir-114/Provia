from django import forms

from .models import ProviderProfile


class ProviderProfileForm(forms.ModelForm):
    class Meta:
        model = ProviderProfile
        fields = (
            "business_name",
            "business_description",
            "phone",
            "email",
            "address",
            "city",
            "state",
            "postal_code",
        )

        widgets = {
            "business_name": forms.TextInput(
                attrs={
                    "class": "w-full rounded-lg border px-4 py-3",
                    "placeholder": "Your business name",
                }
            ),
            "business_description": forms.Textarea(
                attrs={
                    "class": "w-full rounded-lg border px-4 py-3",
                    "rows": 5,
                    "placeholder": "Describe your services and business",
                }
            ),
            "phone": forms.TextInput(
                attrs={
                    "class": "w-full rounded-lg border px-4 py-3",
                    "placeholder": "Business phone number",
                }
            ),
            "email": forms.EmailInput(
                attrs={
                    "class": "w-full rounded-lg border px-4 py-3",
                    "placeholder": "Business email",
                }
            ),
            "address": forms.Textarea(
                attrs={
                    "class": "w-full rounded-lg border px-4 py-3",
                    "rows": 3,
                    "placeholder": "Business address",
                }
            ),
            "city": forms.TextInput(
                attrs={
                    "class": "w-full rounded-lg border px-4 py-3",
                    "placeholder": "City",
                }
            ),
            "state": forms.TextInput(
                attrs={
                    "class": "w-full rounded-lg border px-4 py-3",
                    "placeholder": "State",
                }
            ),
            "postal_code": forms.TextInput(
                attrs={
                    "class": "w-full rounded-lg border px-4 py-3",
                    "placeholder": "Postal code",
                }
            ),
        }
