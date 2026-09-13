from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from categories.models import Category

from products.models import Product

from orders.guest_access import (
    generate_guest_access_token,
    hash_guest_access_token,
)

from orders.models import (
    Order,
    OrderItem,
)

from payments.models import (
    RefundRequest,
    ReturnRequest,
    ReturnRequestItem,
)


class Phase13EGuestReturnsTests(
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
            order_number="GUEST-RET-001",
            full_name="Guest Customer",
            phone="0712345678",
            email="guest@example.com",
            county="Nairobi",
            city="Nairobi",
            estate="CBD",
            house_number="1",
            subtotal=Decimal("1000.00"),
            shipping_cost=Decimal("0.00"),
            total_amount=Decimal("1000.00"),
            payment_status="paid",
            status="delivered",
            inventory_status="consumed",
            delivery_pricing_status="fixed",
            currency_code_at_checkout="KES",
            currency_symbol_at_checkout="KSh",
        )


        category = Category.objects.create(
            name="Phase 13E",
            slug="phase-13e",
        )


        product = Product.objects.create(
            category=category,
            name="Guest Return Product",
            slug="guest-return-product",
            sku="GUEST-RET-PROD",
            description="Test",
            price=Decimal("500.00"),
            stock=10,
        )


        self.item = OrderItem.objects.create(
            order=self.order,
            product=product,
            product_name=product.name,
            price=Decimal("500.00"),
            quantity=2,
            subtotal=Decimal("1000.00"),
        )


    def test_guest_can_open_refund_form(
        self,
    ):

        response = self.client.get(
            reverse(
                "guest_request_refund",
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


    def test_wrong_token_cannot_open_refund(
        self,
    ):

        response = self.client.get(
            reverse(
                "guest_request_refund",
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


    def test_guest_can_submit_refund(
        self,
    ):

        response = self.client.post(
            reverse(
                "guest_request_refund",
                args=[
                    self.order.order_number,
                    self.token,
                ],
            ),
            {
                "amount": "300.00",
                "reason":
                    "Item did not meet expectations.",
            },
        )


        self.assertEqual(
            response.status_code,
            200,
        )


        refund = RefundRequest.objects.get(
            order=self.order
        )


        self.assertEqual(
            refund.amount,
            Decimal("300.00"),
        )


        event = refund.events.get()


        self.assertIsNone(
            event.created_by
        )


    def test_fully_refunded_order_cannot_request_another_refund(
        self,
    ):

        self.order.payment_status = "refunded"

        self.order.save(
            update_fields=[
                "payment_status"
            ]
        )


        response = self.client.get(
            reverse(
                "guest_request_refund",
                args=[
                    self.order.order_number,
                    self.token,
                ],
            )
        )


        self.assertEqual(
            response.status_code,
            400,
        )


    def test_guest_can_open_return_form(
        self,
    ):

        response = self.client.get(
            reverse(
                "guest_request_return",
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


    def test_guest_can_submit_item_return(
        self,
    ):

        response = self.client.post(
            reverse(
                "guest_request_return",
                args=[
                    self.order.order_number,
                    self.token,
                ],
            ),
            {
                "request_type": "return",
                "reason": "Wrong size.",
                f"quantity_{self.item.pk}":
                    "1",
            },
        )


        self.assertEqual(
            response.status_code,
            200,
        )


        request_obj = (
            ReturnRequest.objects.get(
                order=self.order
            )
        )


        line = (
            ReturnRequestItem.objects.get(
                return_request=request_obj
            )
        )


        self.assertEqual(
            line.order_item,
            self.item,
        )


        self.assertEqual(
            line.quantity,
            1,
        )


        self.assertIsNone(
            request_obj.events.get().created_by
        )


    def test_wrong_token_cannot_submit_return(
        self,
    ):

        response = self.client.post(
            reverse(
                "guest_request_return",
                args=[
                    self.order.order_number,
                    "wrong-token",
                ],
            ),
            {
                "request_type": "return",
                "reason": "Wrong size.",
                f"quantity_{self.item.pk}":
                    "1",
            },
        )


        self.assertEqual(
            response.status_code,
            404,
        )


        self.assertFalse(
            ReturnRequest.objects.filter(
                order=self.order
            ).exists()
        )


    def test_guest_cannot_return_more_than_purchased(
        self,
    ):

        response = self.client.post(
            reverse(
                "guest_request_return",
                args=[
                    self.order.order_number,
                    self.token,
                ],
            ),
            {
                "request_type": "return",
                "reason": "Test.",
                f"quantity_{self.item.pk}":
                    "3",
            },
        )


        self.assertEqual(
            response.status_code,
            200,
        )


        self.assertContains(
            response,
            "remain eligible for return",
        )


        self.assertFalse(
            ReturnRequest.objects.filter(
                order=self.order
            ).exists()
        )


    def test_guest_can_view_own_refund_status(
        self,
    ):

        refund = RefundRequest.objects.create(
            order=self.order,
            amount=Decimal("100.00"),
            reason="Test",
        )


        response = self.client.get(
            reverse(
                "guest_refund_detail",
                args=[
                    self.order.order_number,
                    self.token,
                    refund.pk,
                ],
            )
        )


        self.assertEqual(
            response.status_code,
            200,
        )


    def test_token_for_one_order_cannot_view_another_orders_refund(
        self,
    ):

        other_token = (
            generate_guest_access_token()
        )


        other = Order.objects.create(
            user=None,
            guest_checkout=True,
            guest_access_token_hash=(
                hash_guest_access_token(
                    other_token
                )
            ),
            order_number="GUEST-RET-002",
            full_name="Other Guest",
            phone="0700000000",
            email="other@example.com",
            county="Nairobi",
            city="Nairobi",
            estate="CBD",
            house_number="2",
            subtotal=Decimal("100.00"),
            total_amount=Decimal("100.00"),
            payment_status="paid",
            status="delivered",
        )


        refund = RefundRequest.objects.create(
            order=other,
            amount=Decimal("50.00"),
            reason="Other",
        )


        response = self.client.get(
            reverse(
                "guest_refund_detail",
                args=[
                    other.order_number,
                    self.token,
                    refund.pk,
                ],
            )
        )


        self.assertEqual(
            response.status_code,
            404,
        )
