from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase

from orders.forms import CheckoutForm

from .models import DeliveryProvider, DeliveryZone, PickupPoint


class PickupPointConfigurationTests(TestCase):
    def setUp(self):
        self.provider = DeliveryProvider.objects.create(
            name="Test Coach",
            provider_type="bus_coach",
        )
        self.rongo_zone = DeliveryZone.objects.create(
            county="Migori",
            town="Rongo",
            method="station_pickup",
            pricing_mode="fixed",
            fee=Decimal("300.00"),
            estimated_time="1-2 days",
        )
        self.pickup_point = PickupPoint.objects.create(
            zone=self.rongo_zone,
            provider=self.provider,
            name="Rongo Parcel Office",
            address="Rongo town centre, main bus stage",
            fee=Decimal("250.00"),
            opening_hours="Mon-Sat, 7:00 AM-7:00 PM",
        )

    def checkout_data(self, **overrides):
        data = {
            "full_name": "Akinyi Test",
            "phone": "0712345678",
            "email": "akinyi@example.com",
            "county": "Migori",
            "city": "Rongo",
            "estate": "",
            "house_number": "",
            "landmark": "",
            "delivery_notes": "",
            "delivery_zone": self.rongo_zone.pk,
            "pickup_point": self.pickup_point.pk,
        }
        data.update(overrides)
        return data

    def test_pickup_point_can_override_zone_fee(self):
        self.assertEqual(self.pickup_point.effective_fee, Decimal("250.00"))
        self.assertEqual(self.pickup_point.effective_estimated_time, "1-2 days")

    def test_station_pickup_does_not_require_door_address(self):
        form = CheckoutForm(self.checkout_data())
        self.assertTrue(form.is_valid(), form.errors)

    def test_station_pickup_requires_a_matching_pickup_point(self):
        form = CheckoutForm(self.checkout_data(pickup_point=""))
        self.assertFalse(form.is_valid())
        self.assertIn("pickup_point", form.errors)

    def test_door_delivery_requires_address_details(self):
        door_zone = DeliveryZone.objects.create(
            county="Migori",
            town="Rongo",
            method="local_door",
            fee=Decimal("450.00"),
        )
        form = CheckoutForm(
            self.checkout_data(
                delivery_zone=door_zone.pk,
                pickup_point="",
            )
        )
        self.assertFalse(form.is_valid())
        self.assertIn("estate", form.errors)
        self.assertIn("house_number", form.errors)

    def test_pickup_point_rejects_non_pickup_zone(self):
        door_zone = DeliveryZone.objects.create(
            county="Migori",
            town="Awendo",
            method="local_door",
            fee=Decimal("400.00"),
        )
        invalid_point = PickupPoint(
            zone=door_zone,
            provider=self.provider,
            name="Invalid Station",
            address="Awendo",
        )
        with self.assertRaises(ValidationError):
            invalid_point.full_clean()
