from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model

from django.test import TestCase

from django.urls import reverse

from django.utils import timezone


from categories.models import Category

from products.models import Product

from cart.models import (
    Cart,
    CartItem,
)


User = get_user_model()


class Phase14BAdminAbandonedCartTests(
    TestCase
):

    def setUp(self):

        self.staff = (
            User.objects.create_user(
                username="phase14b-admin",
                email="admin@example.com",
                password="pass12345",
                is_staff=True,
            )
        )


        self.customer = (
            User.objects.create_user(
                username="phase14b-customer",
                email="buyer@example.com",
                password="pass12345",
            )
        )


        category = Category.objects.create(
            name="Phase 14B",
            slug="phase-14b",
        )


        self.product = Product.objects.create(
            category=category,
            name="Abandoned Product",
            slug="abandoned-product",
            sku="ABANDONED-001",
            description="Test product",
            price=Decimal("250.00"),
            stock=20,
        )


    def create_abandoned_cart(
        self,
        *,
        user=None,
        session_key=None,
        quantity=2,
        checkout_started=False,
    ):

        cart = Cart.objects.create(
            user=user,
            session_key=session_key,
        )


        CartItem.objects.create(
            cart=cart,
            product=self.product,
            quantity=quantity,
        )


        old_time = (
            timezone.now()
            - timedelta(hours=30)
        )


        values = {
            "last_activity_at":
                old_time,
        }


        if checkout_started:

            values[
                "checkout_started_at"
            ] = (
                old_time
                + timedelta(hours=1)
            )


        Cart.objects.filter(
            pk=cart.pk
        ).update(
            **values
        )


        cart.refresh_from_db()


        return cart


    def test_non_staff_cannot_access_list(
        self,
    ):

        self.client.force_login(
            self.customer
        )


        response = self.client.get(
            reverse(
                "admin_abandoned_cart_list"
            )
        )


        self.assertEqual(
            response.status_code,
            302,
        )


    def test_staff_can_view_abandoned_cart_list(
        self,
    ):

        cart = self.create_abandoned_cart(
            user=self.customer,
        )


        self.client.force_login(
            self.staff
        )


        response = self.client.get(
            reverse(
                "admin_abandoned_cart_list"
            )
        )


        self.assertEqual(
            response.status_code,
            200,
        )


        self.assertContains(
            response,
            f"#{cart.pk}",
        )


        self.assertContains(
            response,
            "buyer@example.com",
        )


    def test_cart_value_is_calculated(
        self,
    ):

        self.create_abandoned_cart(
            user=self.customer,
            quantity=2,
        )


        self.client.force_login(
            self.staff
        )


        response = self.client.get(
            reverse(
                "admin_abandoned_cart_list"
            )
        )


        self.assertEqual(
            response.context[
                "total_value"
            ],
            Decimal("500.00"),
        )


    def test_guest_cart_is_displayed(
        self,
    ):

        self.create_abandoned_cart(
            session_key=
                "phase14b-guest-session",
        )


        self.client.force_login(
            self.staff
        )


        response = self.client.get(
            reverse(
                "admin_abandoned_cart_list"
            )
        )


        self.assertEqual(
            response.context[
                "guest_count"
            ],
            1,
        )


        self.assertContains(
            response,
            "Guest",
        )


    def test_customer_filter(
        self,
    ):

        customer_cart = (
            self.create_abandoned_cart(
                user=self.customer,
            )
        )


        guest_cart = (
            self.create_abandoned_cart(
                session_key="guest-filter",
            )
        )


        self.client.force_login(
            self.staff
        )


        response = self.client.get(
            reverse(
                "admin_abandoned_cart_list"
            ),
            {
                "type": "customer",
            },
        )


        carts = list(
            response.context[
                "carts"
            ]
        )


        self.assertIn(
            customer_cart,
            carts,
        )


        self.assertNotIn(
            guest_cart,
            carts,
        )


    def test_checkout_started_filter(
        self,
    ):

        started = (
            self.create_abandoned_cart(
                user=self.customer,
                checkout_started=True,
            )
        )


        not_started = (
            self.create_abandoned_cart(
                session_key=
                    "checkout-filter-guest",
                checkout_started=False,
            )
        )


        self.client.force_login(
            self.staff
        )


        response = self.client.get(
            reverse(
                "admin_abandoned_cart_list"
            ),
            {
                "checkout":
                    "started",
            },
        )


        carts = list(
            response.context[
                "carts"
            ]
        )


        self.assertIn(
            started,
            carts,
        )


        self.assertNotIn(
            not_started,
            carts,
        )


    def test_search_by_product(
        self,
    ):

        cart = self.create_abandoned_cart(
            user=self.customer
        )


        self.client.force_login(
            self.staff
        )


        response = self.client.get(
            reverse(
                "admin_abandoned_cart_list"
            ),
            {
                "q":
                    "Abandoned Product",
            },
        )


        self.assertIn(
            cart,
            list(
                response.context[
                    "carts"
                ]
            ),
        )


    def test_staff_can_view_abandoned_cart_detail(
        self,
    ):

        cart = self.create_abandoned_cart(
            user=self.customer,
            quantity=2,
        )


        self.client.force_login(
            self.staff
        )


        response = self.client.get(
            reverse(
                "admin_abandoned_cart_detail",
                args=[cart.pk],
            )
        )


        self.assertEqual(
            response.status_code,
            200,
        )


        self.assertContains(
            response,
            "Abandoned Product",
        )


        self.assertContains(
            response,
            "500.00",
        )


    def test_recent_cart_cannot_be_opened_as_abandoned(
        self,
    ):

        cart = Cart.objects.create(
            user=self.customer,
        )


        CartItem.objects.create(
            cart=cart,
            product=self.product,
            quantity=1,
        )


        self.client.force_login(
            self.staff
        )


        response = self.client.get(
            reverse(
                "admin_abandoned_cart_detail",
                args=[cart.pk],
            )
        )


        self.assertEqual(
            response.status_code,
            404,
        )


    def test_converted_cart_cannot_be_opened_as_abandoned(
        self,
    ):

        cart = self.create_abandoned_cart(
            user=self.customer
        )


        Cart.objects.filter(
            pk=cart.pk
        ).update(
            converted_at=timezone.now()
        )


        self.client.force_login(
            self.staff
        )


        response = self.client.get(
            reverse(
                "admin_abandoned_cart_detail",
                args=[cart.pk],
            )
        )


        self.assertEqual(
            response.status_code,
            404,
        )
