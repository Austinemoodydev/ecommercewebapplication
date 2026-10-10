from delivery.models import DeliveryZone, PickupPoint
from django import forms

from .models import DeliveryArea


class CheckoutForm(forms.Form):

    address_id = forms.IntegerField(required=False)

    full_name = forms.CharField(max_length=150)
    phone = forms.CharField(max_length=20)
    email = forms.EmailField(required=False)

    county = forms.CharField(max_length=100)
    city = forms.CharField(max_length=100)

    estate = forms.CharField(max_length=150, required=False)

    delivery_zone = forms.ModelChoiceField(
        queryset=DeliveryZone.objects.filter(
            is_active=True
        ).select_related(
            "provider"
        ),
        required=True,
    )
    pickup_point = forms.ModelChoiceField(
        queryset=PickupPoint.objects.filter(is_active=True).select_related(
            "zone", "provider"
        ),
        required=False,
    )

    house_number = forms.CharField(max_length=100, required=False)
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

        pickup_point = cleaned.get("pickup_point")
        if zone.method == "station_pickup":
            if not pickup_point:
                self.add_error(
                    "pickup_point",
                    "Choose the courier or bus station where you will collect the order.",
                )
            elif pickup_point.zone_id != zone.pk or not pickup_point.is_active:
                self.add_error(
                    "pickup_point",
                    "The selected pickup point is not available for this delivery option.",
                )
        elif pickup_point:
            self.add_error(
                "pickup_point",
                "Pickup points are only used for station pickup.",
            )

        if zone.method in {"local_door", "long_distance", "personal_rider", "other"}:
            if not (cleaned.get("estate") or "").strip():
                self.add_error("estate", "Enter the estate, street or delivery area.")
            if not (cleaned.get("house_number") or "").strip():
                self.add_error("house_number", "Enter the building or house details.")

        return cleaned
