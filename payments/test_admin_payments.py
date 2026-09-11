from decimal import Decimal

from django.contrib.auth import (
    get_user_model,
)

from django.test import TestCase

from django.urls import reverse

from orders.models import Order

from payments.models import (
    MpesaTransaction,
)


User = get_user_model()


class AdminPaymentTests(TestCase):

    def setUp(self):

        self.staff = (
            User.objects.create_user(
                username="paymentadmin",
                password="testpass123",
                role=User.ADMIN,
                is_staff=True,
                is_active=True,
            )
        )

        self.customer = (
            User.objects.create_user(
                username="paymentbuyer",
                password="testpass123",
                email="buyer@example.com",
                phone="0712345678",
                role=User.CUSTOMER,
            )
        )

        self.order = (
            Order.objects.create(
                user=self.customer,
                order_number="PAY-TEST-001",
                full_name="Payment Buyer",
                phone="0712345678",
                email="buyer@example.com",
                county="Nairobi",
                city="Nairobi",
                estate="CBD",
                house_number="1",
                subtotal=Decimal(
                    "2500.00"
                ),
                shipping_cost=Decimal(
                    "0.00"
                ),
                discount=Decimal(
                    "0.00"
                ),
                total_amount=Decimal(
                    "2500.00"
                ),
                payment_status="paid",
                inventory_status="consumed",
                status="confirmed",
                payment_review_required=True,
                payment_review_reason=(
                    "Possible duplicate payment."
                ),
            )
        )

        self.payment = (
            MpesaTransaction.objects.create(
                order=self.order,
                phone_number="0712345678",
                amount=Decimal(
                    "2500.00"
                ),
                merchant_request_id=(
                    "MERCHANT-TEST"
                ),
                checkout_request_id=(
                    "CHECKOUT-TEST"
                ),
                mpesa_receipt_number=(
                    "TESTRECEIPT"
                ),
                status="success",
                result_code="0",
                result_description=(
                    "Processed successfully"
                ),
            )
        )

    def test_payment_list_requires_staff(
        self
    ):

        response = self.client.get(
            reverse(
                "admin_payment_list"
            )
        )

        self.assertNotEqual(
            response.status_code,
            200,
        )

        self.client.login(
            username="paymentadmin",
            password="testpass123",
        )

        response = self.client.get(
            reverse(
                "admin_payment_list"
            )
        )

        self.assertEqual(
            response.status_code,
            200,
        )

    def test_payment_detail(
        self
    ):

        self.client.login(
            username="paymentadmin",
            password="testpass123",
        )

        response = self.client.get(
            reverse(
                "admin_payment_detail",
                kwargs={
                    "pk": self.payment.pk
                },
            )
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertContains(
            response,
            "TESTRECEIPT",
        )

    def test_payment_review_resolution(
        self
    ):

        self.client.login(
            username="paymentadmin",
            password="testpass123",
        )

        response = self.client.post(
            reverse(
                "admin_payment_review_resolve",
                kwargs={
                    "pk": self.payment.pk
                },
            ),
            {
                "resolution": (
                    "Verified duplicate payment "
                    "and escalated for refund."
                ),
            },
        )

        self.assertEqual(
            response.status_code,
            302,
        )

        self.order.refresh_from_db()

        self.assertFalse(
            self.order.payment_review_required
        )

        self.assertTrue(
            self.order.payment_review_resolution
        )

        self.assertEqual(
            self.order.payment_review_resolved_by,
            self.staff,
        )
