from django import forms

from .models import RefundRequest
from .models import ReturnRequest


class RefundRequestForm(forms.ModelForm):
    class Meta:
        model = RefundRequest
        fields = ("amount", "reason")
        widgets = {"reason": forms.Textarea(attrs={"rows": 4})}

    def __init__(self, *args, order, **kwargs):
        super().__init__(*args, **kwargs)
        self.order = order
        self.instance.order = order
        self.fields["amount"].initial = order.total_amount

    def clean_amount(self):
        amount = self.cleaned_data["amount"]
        if amount <= 0 or amount > self.order.total_amount:
            raise forms.ValidationError("Refund amount must be greater than zero and no more than the order total.")
        return amount


class ReturnRequestForm(forms.ModelForm):
    class Meta:
        model = ReturnRequest
        fields = ("request_type", "reason")
        widgets = {"reason": forms.Textarea(attrs={"rows": 4})}