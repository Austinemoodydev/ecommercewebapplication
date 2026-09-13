from decimal import Decimal

from django.contrib.auth import (
    get_user_model,
)

from django.test import TestCase
from django.urls import reverse

from cart.models import Cart, CartItem

from categories.models import Category

from delivery.models import DeliveryZone

from orders.guest_access import (
    generate_guest_access_token,
    hash_guest_access_token,
    verify_guest_access_token,
)

from orders.models import Order

from products.models import Product


User = get_user_model()


class Phase13ABGuestAccessTests(
    TestCase
):

    def setUp(self):

        self.category = (
            Category.objects.create(
                name="Guest Category",
                slug="guest-category",
            )
        )


        self.product = (
            Product.objects.create(
                category=self.category,
                name="Guest Product",
                slug="guest-product",
                description="Guest checkout item",
                sku="GUEST-001",
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


    def _create_guest_cart(self):

        session = self.client.session

        session[
            "phase13ab"
        ] = True

        session.save()


        cart = Cart.objects.create(
            session_key=session.session_key
        )


        CartItem.objects.create(
            cart=cart,
            product=self.product,
            quantity=1,
        )


        return cart


    def test_token_hash_verification(
        self,
    ):

        token = (
            generate_guest_access_token()
        )


        order = Order(
            guest_checkout=True,
            guest_access_token_hash=(
                hash_guest_access_token(
                    token
                )
            ),
        )


        self.assertTrue(
            verify_guest_access_token(
                order,
                token,
            )
        )


        self.assertFalse(
            verify_guest_access_token(
                order,
                "wrong-token",
            )
        )


    def test_normal_order_rejects_guest_token(
        self,
    ):

        token = (
            generate_guest_access_token()
        )


        order = Order(
            guest_checkout=False,
            guest_access_token_hash=(
                hash_guest_access_token(
                    token
                )
            ),
        )


        self.assertFalse(
            verify_guest_access_token(
                order,
                token,
            )
        )


    def test_guest_checkout_requires_email(
        self,
    ):

        self._create_guest_cart()


        response = self.client.post(
            reverse(
                "checkout"
            ),
            {
                "full_name":
                    "Guest Customer",

                "phone":
                    "0712345678",

                "email":
                    "",

                "county":
                    "Nairobi",

                "city":
                    "Nairobi",

                "estate":
                    "CBD",

                "house_number":
                    "1",

                "delivery_zone":
                    str(
                        self.zone.pk
                    ),
            },
        )


        self.assertEqual(
            response.status_code,
            200,
        )


        self.assertEqual(
            Order.objects.count(),
            0,
        )


        self.assertContains(
            response,
            "Email is required for guest checkout",
        )


    def test_guest_checkout_creates_order_without_user(
        self,
    ):

        self._create_guest_cart()


        response = self.client.post(
            reverse(
                "checkout"
            ),
            {
                "full_name":
                    "Guest Customer",

                "phone":
                    "0712345678",

                "email":
                    "guest@example.com",

                "county":
                    "Nairobi",

                "city":
                    "Nairobi",

                "estate":
                    "CBD",

                "house_number":
                    "1",

                "delivery_zone":
                    str(
                        self.zone.pk
                    ),
            },
        )


        self.assertEqual(
            response.status_code,
            302,
        )


        order = (
            Order.objects.get()
        )


        self.assertIsNone(
            order.user
        )

        self.assertTrue(
            order.guest_checkout
        )

        self.assertEqual(
            order.email,
            "guest@example.com",
        )

        self.assertEqual(
            len(
                order.guest_access_token_hash
            ),
            64,
        )


        self.assertIn(
            order.order_number,
            response.url,
        )


        # Raw token must not be stored in the DB.
        self.assertNotIn(
            order.guest_access_token_hash,
            response.url,
        )


    def test_wrong_guest_token_returns_404(
        self,
    ):

        token = (
            generate_guest_access_token()
        )


        order = Order.objects.create(
            user=None,
            guest_checkout=True,
            guest_access_token_hash=(
                hash_guest_access_token(
                    token
                )
            ),
            order_number="GUEST-SEC-001",
            full_name="Guest",
            phone="0712345678",
            email="guest@example.com",
            county="Nairobi",
            city="Nairobi",
            estate="CBD",
            house_number="1",
            subtotal=Decimal("1000.00"),
            total_amount=Decimal("1000.00"),
        )


        response = self.client.get(
            reverse(
                "guest_order_detail",
                args=[
                    order.order_number,
                    "definitely-wrong",
                ],
            )
        )


        self.assertEqual(
            response.status_code,
            404,
        )


    def test_correct_guest_token_can_view_order(
        self,
    ):

        token = (
            generate_guest_access_token()
        )


        order = Order.objects.create(
            user=None,
            guest_checkout=True,
            guest_access_token_hash=(
                hash_guest_access_token(
                    token
                )
            ),
            order_number="GUEST-SEC-002",
            full_name="Guest",
            phone="0712345678",
            email="guest@example.com",
            county="Nairobi",
            city="Nairobi",
            estate="CBD",
            house_number="1",
            subtotal=Decimal("1000.00"),
            total_amount=Decimal("1000.00"),
        )


        response = self.client.get(
            reverse(
                "guest_order_detail",
                args=[
                    order.order_number,
                    token,
                ],
            )
        )


        self.assertEqual(
            response.status_code,
            200,
        )


        self.assertContains(
            response,
            "GUEST-SEC-002",
        )


    def test_order_number_alone_does_not_expose_guest_order(
        self,
    ):

        token = (
            generate_guest_access_token()
        )


        order = Order.objects.create(
            user=None,
            guest_checkout=True,
            guest_access_token_hash=(
                hash_guest_access_token(
                    token
                )
            ),
            order_number="GUEST-SEC-003",
            full_name="Guest",
            phone="0712345678",
            email="guest@example.com",
            county="Nairobi",
            city="Nairobi",
            estate="CBD",
            house_number="1",
            subtotal=Decimal("1000.00"),
            total_amount=Decimal("1000.00"),
        )


        response = self.client.get(
            reverse(
                "order_confirmation",
                args=[
                    order.order_number
                ],
            )
        )


        self.assertEqual(
            response.status_code,
            302,
        )


        self.assertIn(
            "/accounts/",
            response.url,
        )


    def test_authenticated_checkout_still_uses_user_order(
        self,
    ):

        user = (
            User.objects.create_user(
                username="phase13-user",
                password="pass12345",
                email="member@example.com",
            )
        )


        self.client.force_login(
            user
        )


        cart = Cart.objects.create(
            user=user
        )


        CartItem.objects.create(
            cart=cart,
            product=self.product,
            quantity=1,
        )


        response = self.client.post(
            reverse(
                "checkout"
            ),
            {
                "full_name":
                    "Member Customer",

                "phone":
                    "0712345678",

                "email":
                    "member@example.com",

                "county":
                    "Nairobi",

                "city":
                    "Nairobi",

                "estate":
                    "CBD",

                "house_number":
                    "1",

                "delivery_zone":
                    str(
                        self.zone.pk
                    ),
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
            order.user,
            user,
        )

        self.assertFalse(
            order.guest_checkout
        )

        self.assertEqual(
            order.guest_access_token_hash,
            "",
        )
