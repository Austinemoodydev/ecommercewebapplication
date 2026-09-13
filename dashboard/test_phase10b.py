from accounts.store_roles import STORE_OWNER
from django.contrib.auth.models import Group
from decimal import Decimal

from django.contrib.auth import (
    get_user_model,
)

from django.core import mail

from django.test import TestCase

from django.urls import reverse

from categories.models import Category

from orders.models import (
    Order,
    OrderDocument,
    OrderItem,
)

from payments.models import (
    MpesaTransaction,
)

from products.models import Product


User = get_user_model()


class Phase10BImmutableDocumentTests(
    TestCase
):

    def setUp(self):

        self.customer = (
            User.objects.create_user(
                username="phase10bcustomer",
                password="pass12345",
                email="phase10b@example.com",
                role=User.CUSTOMER,
            )
        )

        self.other = (
            User.objects.create_user(
                username="phase10bother",
                password="pass12345",
                role=User.CUSTOMER,
            )
        )

        self.staff = (
            User.objects.create_user(
                username="phase10bstaff",
                password="pass12345",
                role=User.ADMIN,
                is_staff=True,
            )
        )

        store_owner_group, _ = Group.objects.get_or_create(
            name=STORE_OWNER,
        )

        self.staff.groups.add(
            store_owner_group
        )

        self.category = (
            Category.objects.create(
                name="Phase 10B",
                slug="phase-10b",
            )
        )

        self.product = (
            Product.objects.create(
                category=self.category,
                name="Original Laptop Name",
                slug="phase-10b-laptop",
                sku="P10B-001",
                price=Decimal(
                    "60000.00"
                ),
                cost_price=Decimal(
                    "45000.00"
                ),
                stock=10,
                reserved_stock=0,
                is_active=True,
            )
        )

        self.order = (
            Order.objects.create(
                user=self.customer,
                order_number="PHASE10B-001",
                full_name="Original Customer",
                phone="0712345678",
                email="customer@example.com",
                county="Nairobi",
                city="Nairobi",
                estate="CBD",
                house_number="10",
                subtotal=Decimal(
                    "60000.00"
                ),
                shipping_cost=Decimal(
                    "500.00"
                ),
                discount=Decimal(
                    "0.00"
                ),
                total_amount=Decimal(
                    "60500.00"
                ),
                status="delivered",
                payment_status="paid",
                inventory_status="consumed",
                payment_method="mpesa",
            )
        )

        self.item = (
            OrderItem.objects.create(
                order=self.order,
                product=self.product,
                product_name=(
                    "Original Laptop Name"
                ),
                price=Decimal(
                    "60000.00"
                ),
                unit_cost_at_sale=Decimal(
                    "45000.00"
                ),
                cost_subtotal_at_sale=Decimal(
                    "45000.00"
                ),
                quantity=1,
                subtotal=Decimal(
                    "60000.00"
                ),
            )
        )

        MpesaTransaction.objects.create(
            order=self.order,
            phone_number="254712345678",
            amount=Decimal("60500"),
            mpesa_receipt_number=(
                "P10B-MPESA"
            ),
            status="success",
        )


    def test_invoice_creates_persistent_document(
        self
    ):

        self.client.login(
            username="phase10bcustomer",
            password="pass12345",
        )

        response = self.client.get(
            reverse(
                "customer_order_invoice",
                args=[
                    self.order.order_number
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

        self.assertEqual(
            document.document_number,
            "INV-PHASE10B-001",
        )


    def test_second_view_reuses_same_document(
        self
    ):

        self.client.login(
            username="phase10bcustomer",
            password="pass12345",
        )

        url = reverse(
            "customer_order_invoice",
            args=[
                self.order.order_number
            ],
        )

        self.client.get(url)
        self.client.get(url)

        self.assertEqual(
            OrderDocument.objects
            .filter(
                order=self.order,
                document_type="invoice",
            )
            .count(),
            1,
        )


    def test_snapshot_does_not_change_after_order_edit(
        self
    ):

        self.client.login(
            username="phase10bcustomer",
            password="pass12345",
        )

        url = reverse(
            "customer_order_invoice",
            args=[
                self.order.order_number
            ],
        )

        self.client.get(url)

        self.order.full_name = (
            "Changed Customer"
        )

        self.order.total_amount = Decimal(
            "99999.00"
        )

        self.order.save()

        self.item.product_name = (
            "Changed Product Name"
        )

        self.item.save(
            update_fields=[
                "product_name",
            ]
        )

        response = self.client.get(
            url
        )

        self.assertContains(
            response,
            "Original Customer",
        )

        self.assertContains(
            response,
            "Original Laptop Name",
        )

        self.assertContains(
            response,
            "60,500",
        )

        self.assertNotContains(
            response,
            "Changed Customer",
        )

        self.assertNotContains(
            response,
            "Changed Product Name",
        )


    def test_receipt_snapshot_contains_mpesa_reference(
        self
    ):

        self.client.login(
            username="phase10bcustomer",
            password="pass12345",
        )

        response = self.client.get(
            reverse(
                "customer_order_receipt",
                args=[
                    self.order.order_number
                ],
            )
        )

        self.assertContains(
            response,
            "P10B-MPESA",
        )

        document = (
            OrderDocument.objects.get(
                order=self.order,
                document_type="receipt",
            )
        )

        self.assertEqual(
            document.snapshot[
                "payment"
            ][
                "mpesa_receipt_number"
            ],
            "P10B-MPESA",
        )


    def test_customer_cannot_access_other_document(
        self
    ):

        self.client.login(
            username="phase10bother",
            password="pass12345",
        )

        response = self.client.get(
            reverse(
                "customer_order_invoice",
                args=[
                    self.order.order_number
                ],
            )
        )

        self.assertEqual(
            response.status_code,
            404,
        )


    def test_customer_can_email_own_invoice(
        self
    ):

        self.client.login(
            username="phase10bcustomer",
            password="pass12345",
        )

        # Issue document first.
        self.client.get(
            reverse(
                "customer_order_invoice",
                args=[
                    self.order.order_number
                ],
            )
        )

        response = self.client.post(
            reverse(
                "customer_order_document_email",
                args=[
                    self.order.order_number,
                    "invoice",
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

        self.assertEqual(
            mail.outbox[0].to,
            [
                "customer@example.com"
            ],
        )

        document = (
            OrderDocument.objects.get(
                order=self.order,
                document_type="invoice",
            )
        )

        self.assertEqual(
            document.email_count,
            1,
        )

        self.assertIsNotNone(
            document.last_emailed_at,
        )
