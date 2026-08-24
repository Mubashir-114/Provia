from django import forms

from .models import ProviderProfile

class ProviderProfileForm(forms.ModelForm):
    profile_picture = forms.ImageField(
        required=False,
        widget=forms.ClearableFileInput(
            attrs={
                "class": "w-full rounded-lg border px-4 py-3",
                "accept": "image/jpeg,image/png,image/webp",
            }
        ),
    )

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
            "profile_picture",
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

    def clean_profile_picture(self):
        from config.image_validation import validate_image_file

        picture = self.cleaned_data.get("profile_picture")
        if picture:
            validate_image_file(picture)
        return picture
