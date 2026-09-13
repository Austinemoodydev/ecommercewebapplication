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

from cart.selectors.abandoned_cart_selector import (
    AbandonedCartSelector,
)

from cart.services.cart_activity_service import (
    CartActivityService,
)


User = get_user_model()


class Phase14AAbandonedCartTests(
    TestCase
):

    def setUp(self):

        self.user = (
            User.objects.create_user(
                username="phase14-user",
                email="phase14@example.com",
                password="pass12345",
            )
        )


        category = Category.objects.create(
            name="Phase 14",
            slug="phase-14",
        )


        self.product = Product.objects.create(
            category=category,
            name="Phase 14 Product",
            slug="phase-14-product",
            description="Test",
            sku="PHASE14-001",
            price=Decimal("100.00"),
            stock=20,
        )


    def _cart_with_item(
        self,
        *,
        user=None,
    ):

        cart = Cart.objects.create(
            user=user,
        )


        CartItem.objects.create(
            cart=cart,
            product=self.product,
            quantity=1,
        )


        return cart


    def test_cart_has_activity_timestamp(
        self,
    ):

        cart = Cart.objects.create(
            user=self.user
        )


        self.assertIsNotNone(
            cart.last_activity_at
        )


    def test_add_to_cart_updates_activity(
        self,
    ):

        self.client.force_login(
            self.user
        )


        cart = Cart.objects.create(
            user=self.user
        )


        old_time = (
            timezone.now()
            - timedelta(days=3)
        )


        Cart.objects.filter(
            pk=cart.pk
        ).update(
            last_activity_at=old_time
        )


        self.client.post(
            reverse(
                "add_to_cart",
                args=[self.product.pk],
            )
        )


        cart.refresh_from_db()


        self.assertGreater(
            cart.last_activity_at,
            old_time,
        )


    def test_cart_change_resets_checkout_marker(
        self,
    ):

        self.client.force_login(
            self.user
        )


        cart = self._cart_with_item(
            user=self.user
        )


        Cart.objects.filter(
            pk=cart.pk
        ).update(
            checkout_started_at=
                timezone.now(),
        )


        item = cart.items.get()


        self.client.post(
            reverse(
                "increase_quantity",
                args=[item.pk],
            )
        )


        cart.refresh_from_db()


        self.assertIsNone(
            cart.checkout_started_at
        )


    def test_new_cart_activity_resets_old_conversion(
        self,
    ):

        self.client.force_login(
            self.user
        )


        cart = Cart.objects.create(
            user=self.user,
            converted_at=timezone.now(),
        )


        self.client.post(
            reverse(
                "add_to_cart",
                args=[self.product.pk],
            )
        )


        cart.refresh_from_db()


        self.assertIsNone(
            cart.converted_at
        )


    def test_mark_checkout_started(
        self,
    ):

        cart = self._cart_with_item(
            user=self.user
        )


        CartActivityService.mark_checkout_started(
            cart
        )


        cart.refresh_from_db()


        self.assertIsNotNone(
            cart.checkout_started_at
        )


        self.assertIsNotNone(
            cart.last_activity_at
        )


    def test_mark_converted(
        self,
    ):

        cart = self._cart_with_item(
            user=self.user
        )


        CartActivityService.mark_converted(
            cart
        )


        cart.refresh_from_db()


        self.assertIsNotNone(
            cart.converted_at
        )


    def test_old_nonempty_unconverted_cart_is_abandoned(
        self,
    ):

        cart = self._cart_with_item(
            user=self.user
        )


        old_time = (
            timezone.now()
            - timedelta(hours=25)
        )


        Cart.objects.filter(
            pk=cart.pk
        ).update(
            last_activity_at=old_time
        )


        abandoned = (
            AbandonedCartSelector
            .abandoned()
        )


        self.assertIn(
            cart,
            abandoned,
        )


    def test_recent_cart_is_not_abandoned(
        self,
    ):

        cart = self._cart_with_item(
            user=self.user
        )


        abandoned = (
            AbandonedCartSelector
            .abandoned()
        )


        self.assertNotIn(
            cart,
            abandoned,
        )


    def test_converted_cart_is_not_abandoned(
        self,
    ):

        cart = self._cart_with_item(
            user=self.user
        )


        Cart.objects.filter(
            pk=cart.pk
        ).update(
            last_activity_at=(
                timezone.now()
                - timedelta(days=2)
            ),
            converted_at=timezone.now(),
        )


        abandoned = (
            AbandonedCartSelector
            .abandoned()
        )


        self.assertNotIn(
            cart,
            abandoned,
        )


    def test_empty_cart_is_not_abandoned(
        self,
    ):

        cart = Cart.objects.create(
            user=self.user
        )


        Cart.objects.filter(
            pk=cart.pk
        ).update(
            last_activity_at=(
                timezone.now()
                - timedelta(days=2)
            )
        )


        abandoned = (
            AbandonedCartSelector
            .abandoned()
        )


        self.assertNotIn(
            cart,
            abandoned,
        )


    def test_guest_cart_can_be_abandoned(
        self,
    ):

        cart = Cart.objects.create(
            session_key="phase14-guest-session"
        )


        CartItem.objects.create(
            cart=cart,
            product=self.product,
            quantity=1,
        )


        Cart.objects.filter(
            pk=cart.pk
        ).update(
            last_activity_at=(
                timezone.now()
                - timedelta(days=2)
            )
        )


        abandoned = (
            AbandonedCartSelector
            .abandoned()
        )


        self.assertIn(
            cart,
            abandoned,
        )
