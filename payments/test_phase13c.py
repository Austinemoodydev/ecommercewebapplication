from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from orders.guest_access import (
    generate_guest_access_token,
    hash_guest_access_token,
)

from orders.models import Order

from payments.models import MpesaTransaction


User = get_user_model()


@override_settings(
    MPESA_STK_ACTIVE_SECONDS=120,
    MPESA_PAYMENT_GRACE_MINUTES=10,
    ORDER_RESERVATION_MINUTES=15,
)
class Phase13CGuestPaymentTests(
    TestCase
):

    def setUp(self):

        self.token = (
            generate_guest_access_token()
        )


        self.guest_order = (
            Order.objects.create(
                user=None,
                guest_checkout=True,
                guest_access_token_hash=(
                    hash_guest_access_token(
                        self.token
                    )
                ),
                order_number="GUEST-PAY-001",
                full_name="Guest Buyer",
                phone="0712345678",
                email="guest@example.com",
                county="Nairobi",
                city="Nairobi",
                estate="CBD",
                house_number="1",
                subtotal=Decimal("1000.00"),
                shipping_cost=Decimal("200.00"),
                total_amount=Decimal("1200.00"),
                payment_status="pending",
                status="pending",
                inventory_status="reserved",
                delivery_pricing_status="fixed",
                currency_code_at_checkout="KES",
                currency_symbol_at_checkout="KSh",
            )
        )


    def test_guest_can_open_payment_page_with_correct_token(
        self,
    ):

        response = self.client.get(
            reverse(
                "guest_initiate_payment",
                args=[
                    self.guest_order.order_number,
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
            "Pay with M-PESA",
        )


        self.assertContains(
            response,
            "KSh",
        )


    def test_guest_payment_page_rejects_wrong_token(
        self,
    ):

        response = self.client.get(
            reverse(
                "guest_initiate_payment",
                args=[
                    self.guest_order.order_number,
                    "wrong-private-token",
                ],
            )
        )


        self.assertEqual(
            response.status_code,
            404,
        )


    def test_normal_payment_route_still_requires_login(
        self,
    ):

        response = self.client.get(
            reverse(
                "initiate_payment",
                args=[
                    self.guest_order.order_number
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


    @patch(
        "payments.views.stk_push"
    )
    def test_guest_can_start_stk_push(
        self,
        mocked_stk_push,
    ):

        mocked_stk_push.return_value = {
            "ResponseCode": "0",
            "MerchantRequestID":
                "MERCHANT-GUEST-001",
            "CheckoutRequestID":
                "CHECKOUT-GUEST-001",
        }


        response = self.client.post(
            reverse(
                "guest_initiate_payment",
                args=[
                    self.guest_order.order_number,
                    self.token,
                ],
            ),
            {
                "phone_number":
                    "0712345678",
            },
        )


        self.assertEqual(
            response.status_code,
            200,
        )


        payload = response.json()


        self.assertTrue(
            payload["success"]
        )


        transaction = (
            MpesaTransaction.objects.get(
                order=self.guest_order
            )
        )


        self.assertEqual(
            transaction.checkout_request_id,
            "CHECKOUT-GUEST-001",
        )


        self.assertEqual(
            transaction.amount,
            Decimal("1200.00"),
        )


        mocked_stk_push.assert_called_once()


    @patch(
        "payments.views.stk_push"
    )
    def test_wrong_guest_token_cannot_start_stk(
        self,
        mocked_stk_push,
    ):

        response = self.client.post(
            reverse(
                "guest_initiate_payment",
                args=[
                    self.guest_order.order_number,
                    "wrong-token",
                ],
            ),
            {
                "phone_number":
                    "0712345678",
            },
        )


        self.assertEqual(
            response.status_code,
            404,
        )


        mocked_stk_push.assert_not_called()


        self.assertFalse(
            MpesaTransaction.objects.filter(
                order=self.guest_order
            ).exists()
        )


    def test_guest_can_check_own_payment_status(
        self,
    ):

        MpesaTransaction.objects.create(
            order=self.guest_order,
            phone_number="254712345678",
            amount=Decimal("1200.00"),
            checkout_request_id=(
                "CHECKOUT-STATUS-001"
            ),
            status="success",
            mpesa_receipt_number=(
                "ABC123XYZ"
            ),
        )


        response = self.client.get(
            reverse(
                "guest_check_payment_status",
                args=[
                    self.guest_order.order_number,
                    self.token,
                ],
            )
        )


        self.assertEqual(
            response.status_code,
            200,
        )


        payload = response.json()


        self.assertEqual(
            payload["status"],
            "success",
        )


        self.assertEqual(
            payload["receipt"],
            "ABC123XYZ",
        )


    def test_wrong_token_cannot_check_payment_status(
        self,
    ):

        response = self.client.get(
            reverse(
                "guest_check_payment_status",
                args=[
                    self.guest_order.order_number,
                    "wrong-token",
                ],
            )
        )


        self.assertEqual(
            response.status_code,
            404,
        )


    def test_authenticated_payment_route_still_works(
        self,
    ):

        user = User.objects.create_user(
            username="phase13c-member",
            password="pass12345",
            email="member@example.com",
        )


        order = Order.objects.create(
            user=user,
            guest_checkout=False,
            order_number="MEMBER-PAY-001",
            full_name="Member Buyer",
            phone="0712345678",
            email="member@example.com",
            county="Nairobi",
            city="Nairobi",
            estate="CBD",
            house_number="1",
            subtotal=Decimal("500.00"),
            total_amount=Decimal("500.00"),
            payment_status="pending",
            inventory_status="reserved",
            delivery_pricing_status="fixed",
        )


        self.client.force_login(
            user
        )


        response = self.client.get(
            reverse(
                "initiate_payment",
                args=[
                    order.order_number
                ],
            )
        )


        self.assertEqual(
            response.status_code,
            200,
        )


    def test_logged_in_customer_cannot_use_normal_route_for_guest_order(
        self,
    ):

        user = User.objects.create_user(
            username="random-member",
            password="pass12345",
        )


        self.client.force_login(
            user
        )


        response = self.client.get(
            reverse(
                "initiate_payment",
                args=[
                    self.guest_order.order_number
                ],
            )
        )


        self.assertEqual(
            response.status_code,
            404,
        )
