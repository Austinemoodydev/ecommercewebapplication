from decimal import Decimal

from django.contrib.auth import (
    get_user_model,
)

from django.core import mail

from django.test import TestCase

from django.urls import reverse

from categories.models import Category

from orders.models import (
    CreditNoteDocument,
    Order,
    OrderDocument,
    OrderItem,
)

from payments.models import (
    RefundRequest,
)

from products.models import Product


User = get_user_model()


class Phase10CCreditNoteTests(
    TestCase
):

    def setUp(self):

        self.customer = (
            User.objects.create_user(
                username="phase10ccustomer",
                password="pass12345",
                role=User.CUSTOMER,
            )
        )


        self.other = (
            User.objects.create_user(
                username="phase10cother",
                password="pass12345",
                role=User.CUSTOMER,
            )
        )


        self.staff = (
            User.objects.create_user(
                username="phase10cstaff",
                password="pass12345",
                role=User.ADMIN,
                is_staff=True,
            )
        )


        self.category = (
            Category.objects.create(
                name="Phase 10C",
                slug="phase-10c",
            )
        )


        self.product = (
            Product.objects.create(
                category=self.category,
                name="Refund Laptop",
                slug="refund-laptop",
                sku="P10C-001",
                price=Decimal(
                    "50000.00"
                ),
                cost_price=Decimal(
                    "40000.00"
                ),
                stock=5,
                reserved_stock=0,
                is_active=True,
            )
        )


        self.order = (
            Order.objects.create(
                user=self.customer,
                order_number="PHASE10C-001",
                full_name="Refund Customer",
                phone="0712345678",
                email="refund@example.com",
                county="Nairobi",
                city="Nairobi",
                estate="CBD",
                house_number="10",
                subtotal=Decimal(
                    "50000.00"
                ),
                shipping_cost=Decimal(
                    "500.00"
                ),
                discount=Decimal(
                    "0.00"
                ),
                total_amount=Decimal(
                    "50500.00"
                ),
                status="delivered",
                payment_status=(
                    "partially_refunded"
                ),
                inventory_status="consumed",
                payment_method="mpesa",
            )
        )


        OrderItem.objects.create(
            order=self.order,
            product=self.product,
            product_name="Refund Laptop",
            price=Decimal(
                "50000.00"
            ),
            unit_cost_at_sale=Decimal(
                "40000.00"
            ),
            cost_subtotal_at_sale=Decimal(
                "40000.00"
            ),
            quantity=1,
            subtotal=Decimal(
                "50000.00"
            ),
        )


        self.refund = (
            RefundRequest.objects.create(
                order=self.order,
                amount=Decimal(
                    "5000.00"
                ),
                reason="Partial return",
                status="processed",
                external_reference=(
                    "REFUND-P10C-001"
                ),
                processed_by=self.staff,
            )
        )


    def test_processed_refund_can_issue_credit_note(
        self
    ):

        self.client.login(
            username="phase10ccustomer",
            password="pass12345",
        )


        response = self.client.get(
            reverse(
                "customer_credit_note",
                args=[
                    self.refund.pk
                ],
            )
        )


        self.assertEqual(
            response.status_code,
            200,
        )


        document = (
            CreditNoteDocument.objects.get(
                refund_request=self.refund
            )
        )


        self.assertEqual(
            document.snapshot[
                "refund"
            ][
                "amount"
            ],
            "5000.00",
        )


    def test_credit_note_is_idempotent(
        self
    ):

        self.client.login(
            username="phase10ccustomer",
            password="pass12345",
        )


        url = reverse(
            "customer_credit_note",
            args=[
                self.refund.pk
            ],
        )


        self.client.get(url)
        self.client.get(url)


        self.assertEqual(
            CreditNoteDocument.objects
            .filter(
                refund_request=self.refund
            )
            .count(),
            1,
        )


    def test_other_customer_cannot_view_credit_note(
        self
    ):

        self.client.login(
            username="phase10cother",
            password="pass12345",
        )


        response = self.client.get(
            reverse(
                "customer_credit_note",
                args=[
                    self.refund.pk
                ],
            )
        )


        self.assertEqual(
            response.status_code,
            404,
        )


    def test_unprocessed_refund_has_no_credit_note(
        self
    ):

        pending = (
            RefundRequest.objects.create(
                order=self.order,
                amount=Decimal(
                    "1000.00"
                ),
                reason="Pending refund",
                status="requested",
            )
        )


        self.client.login(
            username="phase10ccustomer",
            password="pass12345",
        )


        response = self.client.get(
            reverse(
                "customer_credit_note",
                args=[
                    pending.pk
                ],
            )
        )


        self.assertEqual(
            response.status_code,
            404,
        )


    def test_credit_note_email(
        self
    ):

        self.client.login(
            username="phase10ccustomer",
            password="pass12345",
        )


        response = self.client.post(
            reverse(
                "customer_credit_note_email",
                args=[
                    self.refund.pk
                ],
            )
        )


        self.assertEqual(
            response.status_code,
            302,
        )


        self.assertEqual(
            len(
                mail.outbox
            ),
            1,
        )


        document = (
            CreditNoteDocument.objects.get(
                refund_request=self.refund
            )
        )


        document.refresh_from_db()


        self.assertEqual(
            document.email_count,
            1,
        )


    def test_existing_receipt_snapshot_is_not_rewritten(
        self
    ):

        receipt = (
            OrderDocument.objects.create(
                order=self.order,
                document_type="receipt",
                document_number=(
                    "RCP-PHASE10C-001"
                ),
                snapshot={
                    "refund_total": "0.00",
                    "net_amount": "50500.00",
                },
                issued_by=self.customer,
            )
        )


        self.client.login(
            username="phase10ccustomer",
            password="pass12345",
        )


        self.client.get(
            reverse(
                "customer_credit_note",
                args=[
                    self.refund.pk
                ],
            )
        )


        receipt.refresh_from_db()


        self.assertEqual(
            receipt.snapshot[
                "refund_total"
            ],
            "0.00",
        )

        self.assertEqual(
            receipt.snapshot[
                "net_amount"
            ],
            "50500.00",
        )
