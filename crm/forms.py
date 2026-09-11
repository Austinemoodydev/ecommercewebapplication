from django import forms

from .models import CustomerNote


class CustomerNoteForm(
    forms.ModelForm
):

    class Meta:

        model = CustomerNote

        fields = [
            "note",
            "is_pinned",
        ]

        widgets = {

            "note": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                    "placeholder": (
                        "Add an internal "
                        "customer note..."
                    ),
                }
            ),

            "is_pinned": (
                forms.CheckboxInput(
                    attrs={
                        "class": (
                            "form-check-input"
                        ),
                    }
                )
            ),
        }

    def clean_note(self):

        note = (
            self.cleaned_data[
                "note"
            ].strip()
        )

        if len(note) < 2:

            raise forms.ValidationError(
                (
                    "Please enter a "
                    "meaningful note."
                )
            )

        return note
