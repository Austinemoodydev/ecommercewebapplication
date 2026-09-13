from accounts.store_roles import STORE_OWNER
from django.contrib.auth.models import Group
from decimal import Decimal

from django.contrib.auth import (
    get_user_model,
)

from django.test import TestCase

from django.urls import reverse

from categories.models import Category

from delivery.models import (
    Delivery,
    DeliveryProvider,
)

from orders.models import (
    Order,
    OrderItem,
)

from products.models import Product


User = get_user_model()


class Phase9CAdvancedAnalyticsTests(
    TestCase
):

    def setUp(self):

        self.staff = (
            User.objects.create_user(
                username="phase9cstaff",
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

        self.customer = (
            User.objects.create_user(
                username="phase9ccustomer",
                password="pass12345",
                role=User.CUSTOMER,
            )
        )


        self.category = (
            Category.objects.create(
                name="Computers",
                slug="computers-phase9c",
            )
        )


        self.product = (
            Product.objects.create(
                category=self.category,
                name="Phase 9C Laptop",
                slug="phase-9c-laptop",
                sku="P9C-001",
                price=Decimal(
                    "40000.00"
                ),
                cost_price=Decimal(
                    "30000.00"
                ),
                stock=20,
                reserved_stock=0,
                is_active=True,
            )
        )


        self.order1 = (
            self._make_order(
                "P9C-001",
                Decimal(
                    "40000.00"
                ),
            )
        )


        self.order2 = (
            self._make_order(
                "P9C-002",
                Decimal(
                    "40000.00"
                ),
            )
        )


        self.provider = (
            DeliveryProvider.objects.create(
                name="Phase 9C Courier",
                provider_type="courier",
            )
        )


        Delivery.objects.create(
            order=self.order1,
            management_type="external",
            method="local_door",
            provider=self.provider,
            destination="Nairobi CBD",
            customer_delivery_fee=Decimal(
                "500.00"
            ),
            actual_delivery_cost=Decimal(
                "350.00"
            ),
            status="delivered",
        )


    def _make_order(
        self,
        number,
        amount,
    ):

        order = Order.objects.create(
            user=self.customer,
            order_number=number,
            full_name="Phase 9C Customer",
            phone="0712345678",
            email="phase9c@example.com",
            county="Nairobi",
            city="Nairobi",
            estate="CBD",
            house_number="1",
            subtotal=amount,
            shipping_cost=Decimal(
                "0.00"
            ),
            discount=Decimal(
                "0.00"
            ),
            total_amount=amount,
            status="delivered",
            payment_status="paid",
            inventory_status="consumed",
        )


        OrderItem.objects.create(
            order=order,
            product=self.product,
            product_name=self.product.name,
            price=amount,
            unit_cost_at_sale=Decimal(
                "30000.00"
            ),
            cost_subtotal_at_sale=Decimal(
                "30000.00"
            ),
            quantity=1,
            subtotal=amount,
        )


        return order


    def test_category_performance(
        self
    ):

        self.client.login(
            username="phase9cstaff",
            password="pass12345",
        )


        response = self.client.get(
            reverse(
                "admin_sales_reports"
            )
        )


        self.assertEqual(
            response.status_code,
            200,
        )


        rows = response.context[
            "category_performance"
        ]


        self.assertEqual(
            rows[0][
                "product__category__name"
            ],
            "Computers",
        )


        self.assertEqual(
            rows[0][
                "quantity_sold"
            ],
            2,
        )


    def test_repeat_customer_detected(
        self
    ):

        self.client.login(
            username="phase9cstaff",
            password="pass12345",
        )


        response = self.client.get(
            reverse(
                "admin_sales_reports"
            )
        )


        self.assertEqual(
            response.context[
                "repeat_customer_count"
            ],
            1,
        )


        self.assertEqual(
            response.context[
                "unique_customer_count"
            ],
            1,
        )


        self.assertEqual(
            response.context[
                "repeat_customer_rate"
            ],
            100.0,
        )


    def test_delivery_provider_margin(
        self
    ):

        self.client.login(
            username="phase9cstaff",
            password="pass12345",
        )


        response = self.client.get(
            reverse(
                "admin_sales_reports"
            )
        )


        rows = response.context[
            "delivery_provider_performance"
        ]


        self.assertEqual(
            len(rows),
            1,
        )


        self.assertEqual(
            rows[0][
                "provider"
            ],
            "Phase 9C Courier",
        )


        self.assertEqual(
            rows[0][
                "margin"
            ],
            Decimal(
                "150.00"
            ),
        )


    def test_county_performance(
        self
    ):

        self.client.login(
            username="phase9cstaff",
            password="pass12345",
        )


        response = self.client.get(
            reverse(
                "admin_sales_reports"
            )
        )


        rows = response.context[
            "county_performance"
        ]


        self.assertEqual(
            rows[0][
                "county"
            ],
            "Nairobi",
        )


        self.assertEqual(
            rows[0][
                "order_count"
            ],
            2,
        )
