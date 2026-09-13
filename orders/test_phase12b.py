from decimal import Decimal

from django.contrib.auth import (
    get_user_model,
)

from django.test import TestCase

from django.urls import reverse

from cart.models import (
    Cart,
    CartItem,
)

from categories.models import Category

from core.store_settings import (
    get_store_settings,
)

from delivery.models import (
    DeliveryZone,
)

from orders.models import Order

from orders.pricing import (
    calculate_order_pricing,
    minimum_order_satisfied,
    total_from_order_snapshot,
)

from products.models import Product


User = get_user_model()


class Phase12BPricingTests(
    TestCase
):

    def test_tax_is_calculated_after_discount(
        self,
    ):

        result = calculate_order_pricing(
            subtotal=Decimal("1000.00"),
            discount=Decimal("100.00"),
            shipping_cost=Decimal("200.00"),
            tax_enabled=True,
            tax_rate=Decimal("16.00"),
        )


        self.assertEqual(
            result["taxable_amount"],
            Decimal("900.00"),
        )


        self.assertEqual(
            result["tax_amount"],
            Decimal("144.00"),
        )


        self.assertEqual(
            result["total_amount"],
            Decimal("1244.00"),
        )


    def test_tax_disabled_is_zero(
        self,
    ):

        result = calculate_order_pricing(
            subtotal=Decimal("1000.00"),
            discount=Decimal("100.00"),
            shipping_cost=Decimal("200.00"),
            tax_enabled=False,
            tax_rate=Decimal("16.00"),
        )


        self.assertEqual(
            result["tax_amount"],
            Decimal("0.00"),
        )


        self.assertEqual(
            result["total_amount"],
            Decimal("1100.00"),
        )


    def test_minimum_order_validation(
        self,
    ):

        self.assertTrue(
            minimum_order_satisfied(
                subtotal=Decimal("500.00"),
                minimum_order_amount=Decimal("500.00"),
            )
        )


        self.assertFalse(
            minimum_order_satisfied(
                subtotal=Decimal("499.99"),
                minimum_order_amount=Decimal("500.00"),
            )
        )


    def test_zero_minimum_does_not_block_purchase(
        self,
    ):

        self.assertTrue(
            minimum_order_satisfied(
                subtotal=Decimal("1.00"),
                minimum_order_amount=Decimal("0.00"),
            )
        )


    def test_delivery_quote_uses_historical_tax_snapshot(
        self,
    ):

        user = User.objects.create_user(
            username="phase12bquote",
            password="pass12345",
        )


        order = Order.objects.create(
            user=user,
            order_number="P12B-Q-001",
            full_name="Phase 12B",
            phone="0712345678",
            county="Nairobi",
            city="Nairobi",
            estate="CBD",
            house_number="1",
            subtotal=Decimal("1000.00"),
            discount=Decimal("100.00"),
            tax_enabled_at_checkout=True,
            tax_rate_at_checkout=Decimal("16.00"),
            tax_amount=Decimal("144.00"),
            shipping_cost=Decimal("0.00"),
            total_amount=Decimal("1044.00"),
        )


        self.assertEqual(
            total_from_order_snapshot(
                order,
                shipping_cost=Decimal("300.00"),
            ),
            Decimal("1344.00"),
        )


class Phase12BCheckoutTests(
    TestCase
):

    def setUp(self):

        self.user = (
            User.objects.create_user(
                username="phase12bcustomer",
                password="pass12345",
                email="phase12b@example.com",
                phone="0712345678",
                role=User.CUSTOMER,
            )
        )


        self.category = (
            Category.objects.create(
                name="Phase 12B",
                slug="phase-12b",
            )
        )


        self.product = (
            Product.objects.create(
                category=self.category,
                name="Phase 12B Product",
                slug="phase-12b-product",
                sku="P12B-001",
                price=Decimal("1000.00"),
                stock=20,
                reserved_stock=0,
                is_active=True,
            )
        )


        self.zone = (
            DeliveryZone.objects.create(
                county="Nairobi",
                town="Nairobi",
                method="local_door",
                pricing_mode="fixed",
                fee=Decimal("200.00"),
                is_active=True,
            )
        )


        self.cart = (
            Cart.objects.create(
                user=self.user
            )
        )


        CartItem.objects.create(
            cart=self.cart,
            product=self.product,
            quantity=2,
        )


        self.store = (
            get_store_settings()
        )


        self.client.login(
            username="phase12bcustomer",
            password="pass12345",
        )


    def test_default_store_settings_allow_purchase(
        self,
    ):

        self.assertTrue(
            self.store.orders_enabled
        )


        self.assertEqual(
            self.store.minimum_order_amount,
            Decimal("0.00"),
        )


        self.assertFalse(
            self.store.tax_enabled
        )


    def test_disabled_orders_block_checkout(
        self,
    ):

        self.store.orders_enabled = False

        self.store.save()


        response = self.client.get(
            reverse(
                "checkout"
            )
        )


        self.assertEqual(
            response.status_code,
            302,
        )


        self.assertEqual(
            Order.objects.count(),
            0,
        )


    def test_minimum_order_blocks_checkout_only_when_configured(
        self,
    ):

        self.store.orders_enabled = True

        self.store.minimum_order_amount = (
            Decimal("5000.00")
        )

        self.store.save()


        response = self.client.get(
            reverse(
                "checkout"
            )
        )


        self.assertEqual(
            response.status_code,
            302,
        )


        self.assertEqual(
            Order.objects.count(),
            0,
        )


    def test_tax_rate_does_not_apply_when_tax_disabled(
        self,
    ):

        self.store.tax_enabled = False

        self.store.tax_rate = (
            Decimal("16.00")
        )

        self.store.save()


        result = calculate_order_pricing(
            subtotal=Decimal("2000.00"),
            discount=Decimal("0.00"),
            shipping_cost=Decimal("200.00"),
            tax_enabled=self.store.tax_enabled,
            tax_rate=self.store.tax_rate,
        )


        self.assertEqual(
            result["tax_amount"],
            Decimal("0.00"),
        )


        self.assertEqual(
            result["total_amount"],
            Decimal("2200.00"),
        )


    def test_checkout_captures_tax_and_currency_snapshot(
        self,
    ):

        self.store.orders_enabled = True

        self.store.minimum_order_amount = (
            Decimal("500.00")
        )

        self.store.tax_enabled = True

        self.store.tax_rate = (
            Decimal("16.00")
        )

        self.store.currency_code = "KES"

        self.store.currency_symbol = "KSh"

        self.store.save()


        response = self.client.post(
            reverse(
                "checkout"
            ),
            {
                "full_name":
                    "Phase 12B Customer",

                "phone":
                    "0712345678",

                "email":
                    "phase12b@example.com",

                "county":
                    "Nairobi",

                "city":
                    "Nairobi",

                "estate":
                    "CBD",

                "delivery_zone":
                    str(
                        self.zone.pk
                    ),

                "house_number":
                    "10",

                "landmark":
                    "",

                "delivery_notes":
                    "",
            },
        )


        self.assertEqual(
            response.status_code,
            302,
        )


        order = (
            Order.objects.get()
        )


        self.assertEqual(
            order.subtotal,
            Decimal("2000.00"),
        )


        self.assertTrue(
            order.tax_enabled_at_checkout
        )


        self.assertEqual(
            order.tax_rate_at_checkout,
            Decimal("16.00"),
        )


        self.assertEqual(
            order.tax_amount,
            Decimal("320.00"),
        )


        self.assertEqual(
            order.shipping_cost,
            Decimal("200.00"),
        )


        self.assertEqual(
            order.total_amount,
            Decimal("2520.00"),
        )


        self.assertEqual(
            order.currency_code_at_checkout,
            "KES",
        )


        self.assertEqual(
            order.currency_symbol_at_checkout,
            "KSh",
        )


        self.assertEqual(
            order.minimum_order_amount_at_checkout,
            Decimal("500.00"),
        )


    def test_old_order_tax_snapshot_is_immutable_against_new_store_settings(
        self,
    ):

        order = Order.objects.create(
            user=self.user,
            order_number="P12B-HIST-001",
            full_name="Historical Customer",
            phone="0712345678",
            county="Nairobi",
            city="Nairobi",
            estate="CBD",
            house_number="1",
            subtotal=Decimal("1000.00"),
            discount=Decimal("0.00"),
            tax_enabled_at_checkout=True,
            tax_rate_at_checkout=Decimal("16.00"),
            tax_amount=Decimal("160.00"),
            shipping_cost=Decimal("100.00"),
            total_amount=Decimal("1260.00"),
            currency_code_at_checkout="KES",
            currency_symbol_at_checkout="KSh",
        )


        self.store.tax_rate = (
            Decimal("20.00")
        )

        self.store.currency_code = "USD"

        self.store.currency_symbol = "$"

        self.store.save()


        order.refresh_from_db()


        self.assertEqual(
            order.tax_rate_at_checkout,
            Decimal("16.00"),
        )


        self.assertEqual(
            order.tax_amount,
            Decimal("160.00"),
        )


        self.assertEqual(
            order.currency_code_at_checkout,
            "KES",
        )


        self.assertEqual(
            order.currency_symbol_at_checkout,
            "KSh",
        )
