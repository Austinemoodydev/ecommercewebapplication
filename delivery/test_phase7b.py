from decimal import Decimal

from django.contrib.auth import get_user_model

from django.test import TestCase

from django.urls import reverse

from orders.models import Order

from .models import (
    Delivery,
    DeliveryEvent,
    DeliveryProvider,
    DeliveryZone,
)


User = get_user_model()


class DeliveryPhase7BTests(TestCase):

    def setUp(self):

        self.customer = (
            User.objects.create_user(
                username="trackingcustomer",
                password="pass12345",
                role=User.CUSTOMER,
            )
        )

        self.other_customer = (
            User.objects.create_user(
                username="othercustomer",
                password="pass12345",
                role=User.CUSTOMER,
            )
        )

        self.staff = (
            User.objects.create_user(
                username="deliverystaff7b",
                password="pass12345",
                role=User.ADMIN,
                is_staff=True,
            )
        )

        self.order = Order.objects.create(
            user=self.customer,
            order_number="TRACK-001",
            full_name="Tracking Customer",
            phone="0712345678",
            email="track@example.com",
            county="Kisii",
            city="Kisii",
            estate="Town",
            house_number="1",
            subtotal=Decimal("2500.00"),
            shipping_cost=Decimal("500.00"),
            discount=Decimal("0.00"),
            total_amount=Decimal("3000.00"),
            status="shipped",
            payment_status="paid",
            inventory_status="consumed",
        )

        self.provider = (
            DeliveryProvider.objects.create(
                name="Sample Coach",
                provider_type="bus_coach",
            )
        )

        self.delivery = (
            Delivery.objects.create(
                order=self.order,
                management_type="external",
                method="station_pickup",
                provider=self.provider,
                status="in_transit",
                origin="Nairobi",
                destination="Kisii",
                pickup_point=(
                    "Kisii Parcel Office"
                ),
                transport_reference=(
                    "PARCEL-777"
                ),
                customer_delivery_fee=(
                    Decimal("500.00")
                ),
                actual_delivery_cost=(
                    Decimal("450.00")
                ),
            )
        )

        DeliveryEvent.objects.create(
            delivery=self.delivery,
            status="dispatched",
            message=(
                "Parcel left Nairobi."
            ),
            created_by=self.staff,
        )

    def test_owner_can_view_tracking(self):

        self.client.login(
            username="trackingcustomer",
            password="pass12345",
        )

        response = self.client.get(
            reverse(
                "customer_delivery_tracking",
                kwargs={
                    "order_number": (
                        self.order.order_number
                    )
                },
            )
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertContains(
            response,
            "PARCEL-777",
        )

        self.assertContains(
            response,
            "Kisii Parcel Office",
        )

    def test_other_customer_cannot_view_tracking(self):

        self.client.login(
            username="othercustomer",
            password="pass12345",
        )

        response = self.client.get(
            reverse(
                "customer_delivery_tracking",
                kwargs={
                    "order_number": (
                        self.order.order_number
                    )
                },
            )
        )

        self.assertEqual(
            response.status_code,
            404,
        )

    def test_delivery_zone_can_be_created(self):

        zone = DeliveryZone.objects.create(
            county="Kisii",
            town="Kisii Town",
            method="station_pickup",
            provider=self.provider,
            pickup_point=(
                "Kisii Parcel Office"
            ),
            pricing_mode="fixed",
            fee=Decimal("500.00"),
            estimated_time="1 day",
        )

        self.assertEqual(
            zone.fee,
            Decimal("500.00"),
        )
