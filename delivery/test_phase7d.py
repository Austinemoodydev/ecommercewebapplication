from decimal import Decimal

from django.core.exceptions import (
    ValidationError,
)

from django.test import TestCase

from delivery.models import (
    DeliveryProvider,
    DeliveryZone,
)


class DeliveryZoneHardeningTests(
    TestCase
):

    def setUp(self):

        self.provider = (
            DeliveryProvider.objects.create(
                name="Phase7D Provider",
                provider_type="bus_coach",
            )
        )


    def test_store_pickup_is_free(self):

        zone = DeliveryZone.objects.create(
            county="Nairobi",
            town="Nairobi",
            method="store_pickup",
            pricing_mode="confirm",
            fee=Decimal("500.00"),
        )

        self.assertEqual(
            zone.fee,
            Decimal("0.00"),
        )

        self.assertEqual(
            zone.pricing_mode,
            "fixed",
        )


    def test_duplicate_zone_rejected(self):

        DeliveryZone.objects.create(
            county="Kisii",
            town="Kisii",
            method="station_pickup",
            provider=self.provider,
            pickup_point="Main Office",
            pricing_mode="fixed",
            fee=Decimal("500.00"),
        )

        duplicate = DeliveryZone(
            county="kisii",
            town="kisii",
            method="station_pickup",
            provider=self.provider,
            pickup_point="main office",
            pricing_mode="fixed",
            fee=Decimal("550.00"),
        )

        with self.assertRaises(
            ValidationError
        ):

            duplicate.save()


    def test_negative_free_threshold_rejected(
        self
    ):

        zone = DeliveryZone(
            county="Migori",
            town="Rongo",
            method="local_door",
            pricing_mode="fixed",
            fee=Decimal("300.00"),
            free_delivery_threshold=(
                Decimal("-1.00")
            ),
        )

        with self.assertRaises(
            ValidationError
        ):

            zone.save()
