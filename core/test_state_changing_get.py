from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from accounts.models import (
    Address,
    CustomUser,
)
from cart.models import Cart
from categories.models import Category
from products.models import Product
from wishlist.models import Wishlist


class StateChangingGetSecurityTests(TestCase):

    def setUp(self):

        self.user = (
            CustomUser.objects.create_user(
                username="state-get-user",
                email="state-get@example.com",
                password="StrongPass123!",
            )
        )

        self.client.force_login(
            self.user
        )

        self.category = (
            Category.objects.create(
                name="Security category",
                slug="security-category",
            )
        )

        self.product = (
            Product.objects.create(
                category=self.category,
                name="Security product",
                slug="security-product",
                description="Security test product",
                sku="SEC-GET-001",
                price=Decimal("100.00"),
                stock=10,
            )
        )


    # ========================================================
    # CART
    # ========================================================

    def test_get_cannot_add_item_to_cart(self):

        response = self.client.get(
            reverse(
                "add_to_cart",
                args=[self.product.id],
            )
        )

        self.assertEqual(
            response.status_code,
            405,
        )

        cart = Cart.objects.filter(
            user=self.user
        ).first()

        if cart is not None:

            self.assertFalse(
                cart.items.exists()
            )


    def test_cart_quantity_and_remove_gets_do_not_mutate(self):

        self.client.post(
            reverse(
                "add_to_cart",
                args=[self.product.id],
            )
        )

        cart = Cart.objects.get(
            user=self.user
        )

        item = cart.items.get()

        original_quantity = (
            item.quantity
        )


        response = self.client.get(
            reverse(
                "increase_quantity",
                args=[item.id],
            )
        )

        self.assertEqual(
            response.status_code,
            405,
        )

        item.refresh_from_db()

        self.assertEqual(
            item.quantity,
            original_quantity,
        )


        response = self.client.get(
            reverse(
                "decrease_quantity",
                args=[item.id],
            )
        )

        self.assertEqual(
            response.status_code,
            405,
        )

        item.refresh_from_db()

        self.assertEqual(
            item.quantity,
            original_quantity,
        )


        response = self.client.get(
            reverse(
                "remove_from_cart",
                args=[item.id],
            )
        )

        self.assertEqual(
            response.status_code,
            405,
        )

        self.assertTrue(
            cart.items.filter(
                id=item.id
            ).exists()
        )


    def test_cart_post_still_mutates(self):

        response = self.client.post(
            reverse(
                "add_to_cart",
                args=[self.product.id],
            )
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        cart = Cart.objects.get(
            user=self.user
        )

        self.assertEqual(
            cart.items.count(),
            1,
        )


    # ========================================================
    # WISHLIST
    # ========================================================

    def test_get_cannot_toggle_wishlist(self):

        response = self.client.get(
            reverse(
                "toggle_wishlist",
                args=[self.product.id],
            )
        )

        self.assertEqual(
            response.status_code,
            405,
        )

        self.assertFalse(
            Wishlist.objects.filter(
                user=self.user,
                product=self.product,
            ).exists()
        )


    def test_wishlist_post_still_works(self):

        response = self.client.post(
            reverse(
                "toggle_wishlist",
                args=[self.product.id],
            )
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertTrue(
            Wishlist.objects.filter(
                user=self.user,
                product=self.product,
            ).exists()
        )


    # ========================================================
    # COUPON SESSION
    # ========================================================

    def test_get_cannot_remove_coupon_from_session(self):

        session = self.client.session

        session[
            "coupon_code"
        ] = "TESTCOUPON"

        session.save()


        response = self.client.get(
            reverse(
                "remove_coupon"
            )
        )

        self.assertEqual(
            response.status_code,
            405,
        )


        session = self.client.session

        self.assertEqual(
            session.get(
                "coupon_code"
            ),
            "TESTCOUPON",
        )


    def test_coupon_removal_post_still_works(self):

        session = self.client.session

        session[
            "coupon_code"
        ] = "TESTCOUPON"

        session.save()


        response = self.client.post(
            reverse(
                "remove_coupon"
            )
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertNotIn(
            "coupon_code",
            self.client.session,
        )


    # ========================================================
    # ADDRESS ACTIONS ALREADY HARDENED
    # ========================================================

    def test_address_delete_get_is_still_blocked(self):

        address = Address.objects.create(
            user=self.user,
            full_name="Security User",
            phone="0712345678",
            county="Nairobi",
            city="Nairobi",
            estate="Test Estate",
            house_number="1",
        )

        response = self.client.get(
            reverse(
                "delete_address",
                args=[address.id],
            )
        )

        self.assertEqual(
            response.status_code,
            405,
        )

        self.assertTrue(
            Address.objects.filter(
                id=address.id
            ).exists()
        )


    def test_address_default_get_is_still_blocked(self):

        first = Address.objects.create(
            user=self.user,
            full_name="First",
            phone="0711111111",
            county="Nairobi",
            city="Nairobi",
            estate="Estate",
            house_number="1",
            is_default=True,
        )

        second = Address.objects.create(
            user=self.user,
            full_name="Second",
            phone="0722222222",
            county="Nairobi",
            city="Nairobi",
            estate="Estate",
            house_number="2",
            is_default=False,
        )


        response = self.client.get(
            reverse(
                "set_default_address",
                args=[second.id],
            )
        )

        self.assertEqual(
            response.status_code,
            405,
        )


        first.refresh_from_db()
        second.refresh_from_db()

        self.assertTrue(
            first.is_default
        )

        self.assertFalse(
            second.is_default
        )


    # ========================================================
    # LOGOUT ALREADY HARDENED BY DJANGO LOGOUTVIEW
    # ========================================================

    def test_logout_get_does_not_log_user_out(self):

        response = self.client.get(
            reverse(
                "logout"
            )
        )

        self.assertEqual(
            response.status_code,
            405,
        )

        self.assertIn(
            "_auth_user_id",
            self.client.session,
        )
