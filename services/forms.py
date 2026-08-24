from django import forms

from .models import (
    ProviderAvailability,
    Service,
    ServiceCategory,
)

class ServiceForm(forms.ModelForm):
    image = forms.ImageField(
        required=False,
        help_text="Optional. Upload a photo representing your service (JPEG, PNG, WebP). If omitted, an appropriate category icon will be shown automatically.",
        widget=forms.ClearableFileInput(
            attrs={
                "class": "w-full rounded-lg border px-4 py-3 bg-[#131412] text-[#e9ebe7] border-[#343533]",
                "accept": "image/jpeg,image/png,image/webp",
            }
        ),
    )

    class Meta:
        model = Service

        fields = (
            "category",
            "title",
            "description",
            "price",
            "duration_minutes",
            "image",
        )

        widgets = {
            "category": forms.Select(
                attrs={
                    "class": "w-full rounded-lg border px-4 py-3",
                }
            ),
            "title": forms.TextInput(
                attrs={
                    "class": "w-full rounded-lg border px-4 py-3",
                    "placeholder": "e.g. Deep Home Cleaning",
                }
            ),
            "description": forms.Textarea(
                attrs={
                    "class": "w-full rounded-lg border px-4 py-3",
                    "rows": 5,
                    "placeholder": "Describe what the customer receives...",
                }
            ),
            "price": forms.NumberInput(
                attrs={
                    "class": "w-full rounded-lg border px-4 py-3",
                    "step": "0.01",
                    "min": "0",
                    "placeholder": "0.00",
                }
            ),
            "duration_minutes": forms.NumberInput(
                attrs={
                    "class": "w-full rounded-lg border px-4 py-3",
                    "min": "1",
                    "placeholder": "Duration in minutes",
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["category"].queryset = ServiceCategory.objects.filter(
            is_active=True,
        ).order_by("name")

    def clean_image(self):
        from config.image_validation import validate_image_file

        image = self.cleaned_data.get("image")
        if image:
            validate_image_file(image)
        return image


class ProviderAvailabilityForm(forms.ModelForm):
    class Meta:
        model = ProviderAvailability

        fields = (
            "weekday",
            "start_time",
            "end_time",
            "is_active",
        )

        widgets = {
            "weekday": forms.Select(
                attrs={
                    "class": "w-full rounded-lg border px-4 py-3",
                }
            ),
            "start_time": forms.TimeInput(
                format="%H:%M",
                attrs={
                    "class": "w-full rounded-lg border px-4 py-3",
                    "type": "time",
                },
            ),
            "end_time": forms.TimeInput(
                format="%H:%M",
                attrs={
                    "class": "w-full rounded-lg border px-4 py-3",
                    "type": "time",
                },
            ),
            "is_active": forms.CheckboxInput(
                attrs={
                    "class": "h-4 w-4",
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["start_time"].input_formats = ["%H:%M"]
        self.fields["end_time"].input_formats = ["%H:%M"]
