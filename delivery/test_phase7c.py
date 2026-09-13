from accounts.store_roles import STORE_OWNER
from django.contrib.auth.models import Group
from decimal import Decimal

from django.contrib.auth import (
    get_user_model,
)

from django.test import TestCase

from django.urls import reverse

from orders.models import Order

from delivery.models import (
    Delivery,
    DeliveryProvider,
    DeliveryZone,
)


User = get_user_model()


class DeliveryCheckoutIntegrationTests(
    TestCase
):

    def setUp(self):

        self.customer = (
            User.objects.create_user(
                username="phase7ccustomer",
                password="pass12345",
                role=User.CUSTOMER,
            )
        )

        self.staff = (
            User.objects.create_user(
                username="phase7cstaff",
                password="pass12345",
                role=User.ADMIN,
                is_staff=True,
            )
        )

        store_owner_group, _ = Group.objects.get_or_create(
            name=STORE_OWNER,
        )

        self.staff.groups.add(
            store_owner_group
        )

        self.provider = (
            DeliveryProvider.objects.create(
                name="Phase 7C Coach",
                provider_type="bus_coach",
            )
        )

        self.zone = (
            DeliveryZone.objects.create(
                county="Kisii",
                town="Kisii",
                method="station_pickup",
                provider=self.provider,
                pickup_point="Kisii Parcel Office",
                pricing_mode="confirm",
                fee=Decimal("0.00"),
                estimated_time="1 day",
            )
        )

        self.order = Order.objects.create(
            user=self.customer,
            order_number="QUOTE-001",
            full_name="Quote Customer",
            phone="0712345678",
            email="quote@example.com",
            county="Kisii",
            city="Kisii",
            estate="Town",
            house_number="1",
            subtotal=Decimal("3000.00"),
            shipping_cost=Decimal("0.00"),
            discount=Decimal("200.00"),
            total_amount=Decimal("2800.00"),
            delivery_zone=self.zone,
            delivery_pricing_status="quote_pending",
            payment_status="pending",
            inventory_status="reserved",
        )

        self.delivery = (
            Delivery.objects.create(
                order=self.order,
                management_type="external",
                method="station_pickup",
                provider=self.provider,
                status="pending",
                destination="Kisii",
                pickup_point="Kisii Parcel Office",
                customer_delivery_fee=Decimal("0.00"),
            )
        )


    def test_staff_can_confirm_delivery_quote(
        self
    ):

        self.client.login(
            username="phase7cstaff",
            password="pass12345",
        )

        response = self.client.post(
            reverse(
                "delivery_set_quote",
                kwargs={
                    "pk": self.delivery.pk
                },
            ),
            {
                "delivery_fee": "500.00",
            },
        )

        self.assertEqual(
            response.status_code,
            302,
        )

        self.order.refresh_from_db()

        self.delivery.refresh_from_db()

        self.assertEqual(
            self.order.shipping_cost,
            Decimal("500.00"),
        )

        self.assertEqual(
            self.order.total_amount,
            Decimal("3300.00"),
        )

        self.assertEqual(
            self.order.delivery_pricing_status,
            "quoted",
        )

        self.assertEqual(
            self.delivery.customer_delivery_fee,
            Decimal("500.00"),
        )


    def test_customer_cannot_set_delivery_quote(
        self
    ):

        self.client.login(
            username="phase7ccustomer",
            password="pass12345",
        )

        response = self.client.post(
            reverse(
                "delivery_set_quote",
                kwargs={
                    "pk": self.delivery.pk
                },
            ),
            {
                "delivery_fee": "1.00",
            },
        )

        self.assertNotEqual(
            response.status_code,
            200,
        )

        self.order.refresh_from_db()

        self.assertEqual(
            self.order.delivery_pricing_status,
            "quote_pending",
        )
