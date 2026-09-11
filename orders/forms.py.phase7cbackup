from django import forms

from .models import DeliveryArea


class CheckoutForm(forms.Form):

    address_id = forms.IntegerField(required=False)

    full_name = forms.CharField(max_length=150)
    phone = forms.CharField(max_length=20)
    email = forms.EmailField(required=False)

    county = forms.CharField(max_length=100)
    city = forms.CharField(max_length=100)

    delivery_area = forms.ModelChoiceField(
        queryset=DeliveryArea.objects.filter(is_active=True),
        required=True,
    )

    house_number = forms.CharField(max_length=100)
    landmark = forms.CharField(max_length=255, required=False)
    delivery_notes = forms.CharField(required=False, widget=forms.Textarea)

    latitude = forms.DecimalField(required=False, max_digits=9, decimal_places=6)
    longitude = forms.DecimalField(required=False, max_digits=9, decimal_places=6)
