from accounts.store_roles import STORE_OWNER
from django.contrib.auth.models import Group
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from orders.models import Order

from .models import (
    Delivery,
    DeliveryProvider,
)


User = get_user_model()


class DeliveryManagementTests(TestCase):

    def setUp(self):

        self.staff = User.objects.create_user(
            username="deliverystaff",
            password="testpass123",
            role=User.ADMIN,
            is_staff=True,
        )

        store_owner_group, _ = Group.objects.get_or_create(
            name=STORE_OWNER,
        )

        self.staff.groups.add(
            store_owner_group
        )

        self.customer = User.objects.create_user(
            username="deliverycustomer",
            password="testpass123",
            role=User.CUSTOMER,
        )

        self.order = Order.objects.create(
            user=self.customer,
            order_number="DELIVERY-TEST-001",
            full_name="Delivery Customer",
            phone="0712345678",
            email="customer@example.com",
            county="Kisii",
            city="Kisii",
            estate="Town",
            house_number="1",
            subtotal=Decimal("3000.00"),
            shipping_cost=Decimal("500.00"),
            discount=Decimal("0.00"),
            total_amount=Decimal("3500.00"),
            status="processing",
            payment_status="paid",
            inventory_status="consumed",
        )

        self.provider = (
            DeliveryProvider.objects.create(
                name="Test Coach",
                provider_type="bus_coach",
                is_active=True,
            )
        )

    def test_staff_can_open_delivery_list(self):

        self.client.login(
            username="deliverystaff",
            password="testpass123",
        )

        response = self.client.get(
            reverse("delivery_list")
        )

        self.assertEqual(
            response.status_code,
            200,
        )

    def test_external_delivery_can_be_assigned(self):

        self.client.login(
            username="deliverystaff",
            password="testpass123",
        )

        response = self.client.post(
            reverse(
                "delivery_assign",
                kwargs={
                    "order_number": (
                        self.order.order_number
                    )
                },
            ),
            {
                "management_type": "external",
                "method": "station_pickup",
                "provider": self.provider.pk,
                "origin": "Nairobi",
                "destination": "Kisii",
                "pickup_point": "Kisii Parcel Office",
                "transport_reference": "PARCEL-001",
                "driver_name": "",
                "driver_phone": "",
                "customer_delivery_fee": "500.00",
                "actual_delivery_cost": "450.00",
                "expected_arrival": "",
                "notes": "",
            },
        )

        self.assertEqual(
            response.status_code,
            302,
        )

        delivery = Delivery.objects.get(
            order=self.order
        )

        self.assertEqual(
            delivery.provider,
            self.provider,
        )

        self.assertEqual(
            delivery.status,
            "assigned",
        )

        self.assertEqual(
            delivery.transport_reference,
            "PARCEL-001",
        )
