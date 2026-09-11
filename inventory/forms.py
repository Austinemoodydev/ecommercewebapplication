from django import forms


class InventoryAdjustmentForm(forms.Form):

    MOVEMENT_CHOICES = [
        ("restock", "Restock / Supplier Delivery"),
        ("adjustment_in", "Manual Stock Increase"),
        ("adjustment_out", "Manual Stock Reduction"),
        ("damaged", "Damaged / Lost Stock"),
        ("return", "Customer Return"),
    ]

    movement_type = forms.ChoiceField(
        choices=MOVEMENT_CHOICES,
        widget=forms.Select(
            attrs={
                "class": "form-select",
            }
        ),
    )

    quantity = forms.IntegerField(
        min_value=1,
        widget=forms.NumberInput(
            attrs={
                "class": "form-control",
                "min": "1",
            }
        ),
    )

    reference = forms.CharField(
        required=False,
        max_length=150,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": (
                    "Supplier invoice, GRN, "
                    "reference number..."
                ),
            }
        ),
    )

    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(
            attrs={
                "class": "form-control",
                "rows": 4,
                "placeholder": (
                    "Reason or additional details..."
                ),
            }
        ),
    )
