from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from delivery.models import (
    Delivery,
    DeliveryEvent,
)

from orders.guest_access import (
    generate_guest_access_token,
    hash_guest_access_token,
)

from orders.models import (
    Order,
    OrderDocument,
)


class Phase13DGuestDocumentsTrackingTests(
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
            order_number="GUEST-DOC-001",
            full_name="Guest Customer",
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
            status="confirmed",
            inventory_status="reserved",
            delivery_pricing_status="fixed",
            currency_code_at_checkout="KES",
            currency_symbol_at_checkout="KSh",
        )


    def test_guest_can_view_invoice_with_valid_token(
        self,
    ):

        response = self.client.get(
            reverse(
                "guest_order_invoice",
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


        self.assertEqual(
            OrderDocument.objects.filter(
                order=self.order,
                document_type="invoice",
            ).count(),
            1,
        )


    def test_wrong_token_cannot_view_invoice(
        self,
    ):

        response = self.client.get(
            reverse(
                "guest_order_invoice",
                args=[
                    self.order.order_number,
                    "wrong-token",
                ],
            )
        )


        self.assertEqual(
            response.status_code,
            404,
        )


    def test_unpaid_guest_cannot_view_receipt(
        self,
    ):

        response = self.client.get(
            reverse(
                "guest_order_receipt",
                args=[
                    self.order.order_number,
                    self.token,
                ],
            )
        )


        self.assertEqual(
            response.status_code,
            404,
        )


    def test_paid_guest_can_view_receipt(
        self,
    ):

        self.order.payment_status = "paid"

        self.order.save(
            update_fields=[
                "payment_status"
            ]
        )


        response = self.client.get(
            reverse(
                "guest_order_receipt",
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


        self.assertEqual(
            OrderDocument.objects.filter(
                order=self.order,
                document_type="receipt",
            ).count(),
            1,
        )


    def test_guest_document_does_not_require_user_account(
        self,
    ):

        response = self.client.get(
            reverse(
                "guest_order_invoice",
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


        document = (
            OrderDocument.objects.get(
                order=self.order,
                document_type="invoice",
            )
        )


        self.assertIsNone(
            document.issued_by
        )


    def test_guest_can_track_delivery_with_valid_token(
        self,
    ):

        delivery = Delivery.objects.create(
            order=self.order,
            management_type="external",
            method="local_door",
            status="in_transit",
            destination="Nairobi CBD",
            customer_delivery_fee=Decimal(
                "200.00"
            ),
        )


        DeliveryEvent.objects.create(
            delivery=delivery,
            status="in_transit",
            message="Parcel is on the way.",
        )


        response = self.client.get(
            reverse(
                "guest_delivery_tracking",
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
            "Parcel is on the way.",
        )


    def test_wrong_token_cannot_track_delivery(
        self,
    ):

        Delivery.objects.create(
            order=self.order,
            management_type="external",
            method="local_door",
            status="pending",
            destination="Nairobi CBD",
        )


        response = self.client.get(
            reverse(
                "guest_delivery_tracking",
                args=[
                    self.order.order_number,
                    "wrong-token",
                ],
            )
        )


        self.assertEqual(
            response.status_code,
            404,
        )


    def test_order_number_without_token_does_not_open_guest_tracking(
        self,
    ):

        response = self.client.get(
            reverse(
                "customer_delivery_tracking",
                args=[
                    self.order.order_number
                ],
            )
        )


        self.assertEqual(
            response.status_code,
            302,
        )


    def test_guest_order_page_exposes_secure_invoice_link(
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


        expected = reverse(
            "guest_order_invoice",
            args=[
                self.order.order_number,
                self.token,
            ],
        )


        self.assertContains(
            response,
            expected,
        )
