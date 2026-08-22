from django import forms

from .models import Review


class ReviewForm(forms.ModelForm):
    class Meta:
        model = Review
        fields = ["rating", "comment"]
        widgets = {
            "rating": forms.Select(
                choices=[
                    (1, "1 Star"),
                    (2, "2 Stars"),
                    (3, "3 Stars"),
                    (4, "4 Stars"),
                    (5, "5 Stars"),
                ],
            ),
            "comment": forms.Textarea(
                attrs={
                    "rows": 5,
                    "placeholder": "Share your experience with this service...",
                },
            ),
        }

    def clean_rating(self):
        rating = self.cleaned_data.get("rating")

        if rating is None:
            raise forms.ValidationError("Please select a rating.")

        if not 1 <= rating <= 5:
            raise forms.ValidationError("Rating must be between 1 and 5.")

        return rating

    def clean_comment(self):
        comment = self.cleaned_data.get("comment", "").strip()

        if not comment:
            raise forms.ValidationError("Please enter a review comment.")

        return comment
