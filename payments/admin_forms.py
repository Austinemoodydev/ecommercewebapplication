from django import forms


class PaymentReviewResolutionForm(
    forms.Form
):

    resolution = forms.CharField(
        label="Resolution",
        min_length=3,
        max_length=2000,
        widget=forms.Textarea(
            attrs={
                "class": "form-control",
                "rows": 4,
                "placeholder": (
                    "Explain what was verified "
                    "and how this payment case "
                    "was resolved."
                ),
            }
        ),
    )

    def clean_resolution(self):

        return (
            self.cleaned_data[
                "resolution"
            ].strip()
        )
