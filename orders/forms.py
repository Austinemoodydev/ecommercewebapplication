from delivery.models import DeliveryZone
from django import forms

from .models import DeliveryArea


class CheckoutForm(forms.Form):

    address_id = forms.IntegerField(required=False)

    full_name = forms.CharField(max_length=150)
    phone = forms.CharField(max_length=20)
    email = forms.EmailField(required=False)

    county = forms.CharField(max_length=100)
    city = forms.CharField(max_length=100)

    estate = forms.CharField(
        max_length=150,
    )

    delivery_zone = forms.ModelChoiceField(
        queryset=DeliveryZone.objects.filter(
            is_active=True
        ).select_related(
            "provider"
        ),
        required=True,
    )

    house_number = forms.CharField(max_length=100)
    landmark = forms.CharField(max_length=255, required=False)
    delivery_notes = forms.CharField(required=False, widget=forms.Textarea)

    latitude = forms.DecimalField(required=False, max_digits=9, decimal_places=6)
    longitude = forms.DecimalField(required=False, max_digits=9, decimal_places=6)


    def clean(self):

        cleaned = super().clean()

        zone = cleaned.get(
            "delivery_zone"
        )

        county = (
            cleaned.get("county")
            or ""
        ).strip()

        city = (
            cleaned.get("city")
            or ""
        ).strip()

        if not zone:
            return cleaned

        if (
            zone.county.strip().casefold()
            != county.casefold()
        ):

            self.add_error(
                "delivery_zone",
                (
                    "The selected delivery option "
                    "does not match the selected county."
                ),
            )

        if (
            zone.town
            and zone.town.strip().casefold()
            != city.casefold()
        ):

            self.add_error(
                "delivery_zone",
                (
                    "The selected delivery option "
                    "does not match the selected town."
                ),
            )

        return cleaned
