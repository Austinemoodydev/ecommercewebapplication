from accounts.store_roles import STORE_OWNER
from django.contrib.auth.models import Group
from decimal import Decimal

from django.contrib.auth import (
    get_user_model,
)

from django.test import TestCase

from django.urls import reverse

from categories.models import Category

from orders.models import (
    Order,
    OrderItem,
)

from products.models import Product


User = get_user_model()


class Phase9BHistoricalCostTests(
    TestCase
):

    def setUp(self):

        self.staff = (
            User.objects.create_user(
                username="phase9bstaff",
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
                username="phase9bcustomer",
                password="pass12345",
                role=User.CUSTOMER,
            )
        )

        self.category = (
            Category.objects.create(
                name="Phase 9B",
                slug="phase-9b",
            )
        )

        self.product = (
            Product.objects.create(
                category=self.category,
                name="Accounting Laptop",
                slug="accounting-laptop",
                sku="P9B-001",
                price=Decimal("35000.00"),
                cost_price=Decimal("27000.00"),
                stock=20,
                reserved_stock=0,
                is_active=True,
            )
        )

        self.order = (
            Order.objects.create(
                user=self.customer,
                order_number="PHASE9B-001",
                full_name="Accounting Customer",
                phone="0712345678",
                email="phase9b@example.com",
                county="Nairobi",
                city="Nairobi",
                estate="CBD",
                house_number="1",
                subtotal=Decimal("35000.00"),
                shipping_cost=Decimal("0.00"),
                discount=Decimal("0.00"),
                total_amount=Decimal("35000.00"),
                status="delivered",
                payment_status="paid",
                inventory_status="consumed",
            )
        )


    def test_historical_cost_does_not_change_with_product(
        self
    ):

        item = OrderItem.objects.create(
            order=self.order,
            product=self.product,
            product_name=self.product.name,
            price=Decimal("35000.00"),
            unit_cost_at_sale=Decimal("27000.00"),
            cost_subtotal_at_sale=Decimal("27000.00"),
            quantity=1,
            subtotal=Decimal("35000.00"),
        )


        self.product.cost_price = Decimal(
            "31000.00"
        )

        self.product.save(
            update_fields=[
                "cost_price",
            ]
        )


        item.refresh_from_db()


        self.assertEqual(
            item.unit_cost_at_sale,
            Decimal("27000.00"),
        )

        self.assertEqual(
            item.cost_subtotal_at_sale,
            Decimal("27000.00"),
        )


    def test_reports_use_snapshot_not_current_cost(
        self
    ):

        OrderItem.objects.create(
            order=self.order,
            product=self.product,
            product_name=self.product.name,
            price=Decimal("35000.00"),
            unit_cost_at_sale=Decimal("27000.00"),
            cost_subtotal_at_sale=Decimal("27000.00"),
            quantity=1,
            subtotal=Decimal("35000.00"),
        )


        self.product.cost_price = Decimal(
            "33000.00"
        )

        self.product.save(
            update_fields=[
                "cost_price",
            ]
        )


        self.client.login(
            username="phase9bstaff",
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


        self.assertEqual(
            response.context[
                "historical_cogs"
            ],
            Decimal("27000.00"),
        )


        self.assertEqual(
            response.context[
                "legacy_estimated_cogs"
            ],
            Decimal("0.00"),
        )


    def test_legacy_order_is_identified_as_estimate(
        self
    ):

        OrderItem.objects.create(
            order=self.order,
            product=self.product,
            product_name=self.product.name,
            price=Decimal("35000.00"),
            quantity=1,
            subtotal=Decimal("35000.00"),
        )


        self.client.login(
            username="phase9bstaff",
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


        self.assertEqual(
            response.context[
                "legacy_cost_items"
            ],
            1,
        )


        self.assertEqual(
            response.context[
                "historical_cost_items"
            ],
            0,
        )


        self.assertEqual(
            response.context[
                "legacy_estimated_cogs"
            ],
            Decimal("27000.00"),
        )


    def test_snapshot_handles_multiple_quantity(
        self
    ):

        item = OrderItem.objects.create(
            order=self.order,
            product=self.product,
            product_name=self.product.name,
            price=Decimal("35000.00"),
            unit_cost_at_sale=Decimal("27000.00"),
            cost_subtotal_at_sale=Decimal("54000.00"),
            quantity=2,
            subtotal=Decimal("70000.00"),
        )


        self.assertEqual(
            item.cost_subtotal_at_sale,
            Decimal("54000.00"),
        )
