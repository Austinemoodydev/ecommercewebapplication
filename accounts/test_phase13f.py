from decimal import Decimal

from django.contrib.auth import (
    get_user_model,
)

from django.test import TestCase
from django.urls import reverse

from orders.guest_access import (
    generate_guest_access_token,
    hash_guest_access_token,
)

from orders.models import Order


User = get_user_model()


class Phase13FGuestOrderClaimTests(
    TestCase
):

    def setUp(self):

        self.token = (
            generate_guest_access_token()
        )


        self.order = Order.objects.create(
            user=None,
            guest_checkout=True,
            guest_access_token_hash=(
                hash_guest_access_token(
                    self.token
                )
            ),
            order_number="GUEST-CLAIM-001",
            full_name="Guest Buyer",
            phone="0712345678",
            email="guest@example.com",
            county="Nairobi",
            city="Nairobi",
            estate="CBD",
            house_number="1",
            subtotal=Decimal("500.00"),
            total_amount=Decimal("500.00"),
            payment_status="paid",
            status="confirmed",
            inventory_status="consumed",
            delivery_pricing_status="fixed",
        )


        self.user = (
            User.objects.create_user(
                username="verified-customer",
                email="different@example.com",
                password="pass12345",
                is_active=True,
                email_verified=True,
            )
        )


    def claim_url(
        self,
        token=None,
    ):

        return reverse(
            "claim_guest_order",
            args=[
                self.order.order_number,
                token or self.token,
            ],
        )


    def test_guest_order_page_has_link_account_button(
        self,
    ):

        response = self.client.get(
            reverse(
                "guest_order_detail",
                args=[
                    self.order.order_number,
                    self.token,
                ],
            )
        )


        self.assertEqual(
            response.status_code,
            200,
        )


        self.assertContains(
            response,
            self.claim_url(),
        )


    def test_wrong_token_cannot_open_claim_page(
        self,
    ):

        response = self.client.get(
            self.claim_url(
                "wrong-token"
            )
        )


        self.assertEqual(
            response.status_code,
            404,
        )


    def test_anonymous_user_can_open_claim_choice(
        self,
    ):

        response = self.client.get(
            self.claim_url()
        )


        self.assertEqual(
            response.status_code,
            200,
        )


        self.assertContains(
            response,
            "Create Account",
        )


    def test_authenticated_verified_user_can_claim_order(
        self,
    ):

        self.client.force_login(
            self.user
        )


        response = self.client.post(
            self.claim_url()
        )


        self.assertEqual(
            response.status_code,
            302,
        )


        self.order.refresh_from_db()


        self.assertEqual(
            self.order.user,
            self.user,
        )


        self.assertFalse(
            self.order.guest_checkout
        )


        self.assertEqual(
            self.order.guest_access_token_hash,
            "",
        )


    def test_email_does_not_need_to_match_order(
        self,
    ):

        # Ownership is proven by possession
        # of the high-entropy guest token,
        # not by email equality.

        self.assertNotEqual(
            self.user.email,
            self.order.email,
        )


        self.client.force_login(
            self.user
        )


        response = self.client.post(
            self.claim_url()
        )


        self.assertEqual(
            response.status_code,
            302,
        )


        self.order.refresh_from_db()


        self.assertEqual(
            self.order.user,
            self.user,
        )


    def test_unverified_account_cannot_claim(
        self,
    ):

        user = User.objects.create_user(
            username="unverified",
            email="guest@example.com",
            password="pass12345",
            is_active=True,
            email_verified=False,
        )


        self.client.force_login(
            user
        )


        response = self.client.post(
            self.claim_url()
        )


        self.assertEqual(
            response.status_code,
            403,
        )


        self.order.refresh_from_db()


        self.assertIsNone(
            self.order.user
        )


        self.assertTrue(
            self.order.guest_checkout
        )


    def test_old_guest_url_stops_working_after_claim(
        self,
    ):

        guest_url = reverse(
            "guest_order_detail",
            args=[
                self.order.order_number,
                self.token,
            ],
        )


        self.client.force_login(
            self.user
        )


        self.client.post(
            self.claim_url()
        )


        self.client.logout()


        response = self.client.get(
            guest_url
        )


        self.assertEqual(
            response.status_code,
            404,
        )


    def test_claim_cannot_be_repeated(
        self,
    ):

        self.client.force_login(
            self.user
        )


        self.client.post(
            self.claim_url()
        )


        response = self.client.post(
            self.claim_url()
        )


        self.assertEqual(
            response.status_code,
            404,
        )


    def test_second_account_cannot_take_claimed_order(
        self,
    ):

        second = User.objects.create_user(
            username="second-customer",
            email="second@example.com",
            password="pass12345",
            is_active=True,
            email_verified=True,
        )


        self.client.force_login(
            self.user
        )


        self.client.post(
            self.claim_url()
        )


        self.client.force_login(
            second
        )


        response = self.client.post(
            self.claim_url()
        )


        self.assertEqual(
            response.status_code,
            404,
        )


        self.order.refresh_from_db()


        self.assertEqual(
            self.order.user,
            self.user,
        )


    def test_claimed_order_is_available_through_customer_order_detail(
        self,
    ):

        self.client.force_login(
            self.user
        )


        self.client.post(
            self.claim_url()
        )


        response = self.client.get(
            reverse(
                "order_detail",
                args=[
                    self.order.order_number
                ],
            )
        )


        self.assertEqual(
            response.status_code,
            200,
        )


    def test_register_claim_parameters_are_validated_before_session_storage(
        self,
    ):

        response = self.client.get(
            reverse("register")
            + (
                "?claim_order="
                + self.order.order_number
                + "&claim_token=wrong-token"
            )
        )


        self.assertEqual(
            response.status_code,
            404,
        )


        self.assertNotIn(
            "pending_guest_order_claim",
            self.client.session,
        )


    def test_valid_register_claim_is_saved_in_session(
        self,
    ):

        response = self.client.get(
            reverse("register")
            + (
                "?claim_order="
                + self.order.order_number
                + "&claim_token="
                + self.token
            )
        )


        self.assertEqual(
            response.status_code,
            200,
        )


        pending = (
            self.client.session.get(
                "pending_guest_order_claim"
            )
        )


        self.assertIsNotNone(
            pending
        )


        self.assertEqual(
            pending["order_number"],
            self.order.order_number,
        )
