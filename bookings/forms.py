from datetime import date

from django import forms
from django.core.exceptions import ValidationError

from bookings.models import Booking


class BookingForm(forms.Form):
    booking_date = forms.DateField(
        widget=forms.DateInput(
            attrs={
                "type": "date",
                "class": "w-full rounded-lg border px-4 py-3",
            }
        )
    )

    start_time = forms.TimeField(
        widget=forms.HiddenInput(),
        error_messages={
            "required": "Please select a time slot.",
        },
    )

    customer_notes = forms.CharField(
        required=False,
        widget=forms.Textarea(
            attrs={
                "class": "w-full rounded-lg border px-4 py-3",
                "rows": 4,
                "placeholder": "Anything the provider should know?",
            }
        ),
    )

    def clean_booking_date(self):
        booking_date = self.cleaned_data.get("booking_date")
        if booking_date and booking_date <= date.today():
            raise ValidationError("Please select a future date.")
        return booking_date


class BookingStatusUpdateForm(forms.Form):
    status = forms.ChoiceField(
        choices=Booking.Status.choices,
        widget=forms.Select(
            attrs={
                "class": "w-full rounded-lg border px-4 py-3",
            }
        ),
    )

    provider_notes = forms.CharField(
        required=False,
        widget=forms.Textarea(
            attrs={
                "class": "w-full rounded-lg border px-4 py-3",
                "rows": 3,
                "placeholder": "Add notes for the customer (optional)...",
            }
        ),
    )
