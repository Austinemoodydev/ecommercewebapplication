from accounts.store_roles import STORE_OWNER
from django.contrib.auth.models import Group
from decimal import Decimal

from django.contrib.auth import (
    get_user_model,
)

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


class Phase10DAutomaticDocumentTests(
    TestCase
):

    def setUp(self):

        self.customer = (
            User.objects.create_user(
                username="phase10dcustomer",
                password="pass12345",
                email="phase10d@example.com",
                role=User.CUSTOMER,
            )
        )


        self.staff = (
            User.objects.create_user(
                username="phase10dstaff",
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
                name="Phase 10D",
                slug="phase-10d",
            )
        )


        self.product = (
            Product.objects.create(
                category=self.category,
                name="Phase 10D Laptop",
                slug="phase-10d-laptop",
                sku="P10D-001",
                price=Decimal(
                    "70000.00"
                ),
                cost_price=Decimal(
                    "50000.00"
                ),
                stock=10,
                reserved_stock=0,
                is_active=True,
            )
        )


        self.order = (
            Order.objects.create(
                user=self.customer,
                order_number="PHASE10D-001",
                full_name="Phase 10D Customer",
                phone="0712345678",
                email="phase10d@example.com",
                county="Nairobi",
                city="Nairobi",
                estate="CBD",
                house_number="10",
                subtotal=Decimal(
                    "70000.00"
                ),
                shipping_cost=Decimal(
                    "500.00"
                ),
                discount=Decimal(
                    "0.00"
                ),
                total_amount=Decimal(
                    "70500.00"
                ),
                status="delivered",
                payment_status="paid",
                inventory_status="consumed",
                payment_method="mpesa",
            )
        )


        OrderItem.objects.create(
            order=self.order,
            product=self.product,
            product_name=(
                "Phase 10D Laptop"
            ),
            price=Decimal(
                "70000.00"
            ),
            unit_cost_at_sale=Decimal(
                "50000.00"
            ),
            cost_subtotal_at_sale=Decimal(
                "50000.00"
            ),
            quantity=1,
            subtotal=Decimal(
                "70000.00"
            ),
        )


    def test_processed_refund_automatically_creates_credit_note(
        self
    ):

        refund = (
            RefundRequest.objects.create(
                order=self.order,
                amount=Decimal(
                    "5000.00"
                ),
                reason="Automatic refund",
                status="processed",
                external_reference=(
                    "AUTO-REF-001"
                ),
                processed_by=self.staff,
            )
        )


        self.assertTrue(
            CreditNoteDocument.objects
            .filter(
                refund_request=refund
            )
            .exists()
        )


    def test_requested_refund_does_not_create_credit_note(
        self
    ):

        refund = (
            RefundRequest.objects.create(
                order=self.order,
                amount=Decimal(
                    "5000.00"
                ),
                reason="Not processed",
                status="requested",
            )
        )


        self.assertFalse(
            CreditNoteDocument.objects
            .filter(
                refund_request=refund
            )
            .exists()
        )


    def test_processed_without_reference_does_not_create_credit_note(
        self
    ):

        refund = (
            RefundRequest.objects.create(
                order=self.order,
                amount=Decimal(
                    "5000.00"
                ),
                reason="Missing reference",
                status="processed",
                external_reference="",
                processed_by=self.staff,
            )
        )


        self.assertFalse(
            CreditNoteDocument.objects
            .filter(
                refund_request=refund
            )
            .exists()
        )


    def test_credit_note_created_when_reference_added_later(
        self
    ):

        refund = (
            RefundRequest.objects.create(
                order=self.order,
                amount=Decimal(
                    "5000.00"
                ),
                reason="Reference later",
                status="processed",
                external_reference="",
                processed_by=self.staff,
            )
        )


        self.assertFalse(
            CreditNoteDocument.objects
            .filter(
                refund_request=refund
            )
            .exists()
        )


        refund.external_reference = (
            "LATE-REF-001"
        )

        refund.save(
            update_fields=[
                "external_reference",
                "updated_at",
            ]
        )


        self.assertTrue(
            CreditNoteDocument.objects
            .filter(
                refund_request=refund
            )
            .exists()
        )


    def test_repeated_processed_save_does_not_duplicate_credit_note(
        self
    ):

        refund = (
            RefundRequest.objects.create(
                order=self.order,
                amount=Decimal(
                    "5000.00"
                ),
                reason="Repeated save",
                status="processed",
                external_reference=(
                    "AUTO-REF-002"
                ),
                processed_by=self.staff,
            )
        )


        refund.staff_note = (
            "Updated after processing"
        )

        refund.save(
            update_fields=[
                "staff_note",
                "updated_at",
            ]
        )


        self.assertEqual(
            CreditNoteDocument.objects
            .filter(
                refund_request=refund
            )
            .count(),
            1,
        )


    def test_customer_order_page_lists_documents(
        self
    ):

        OrderDocument.objects.create(
            order=self.order,
            document_type="invoice",
            document_number=(
                "INV-PHASE10D-001"
            ),
            snapshot={
                "order": {
                    "order_number":
                        "PHASE10D-001"
                }
            },
            issued_by=self.customer,
        )


        refund = (
            RefundRequest.objects.create(
                order=self.order,
                amount=Decimal(
                    "5000.00"
                ),
                reason="History test",
                status="processed",
                external_reference=(
                    "HISTORY-REF-001"
                ),
                processed_by=self.staff,
            )
        )


        credit_note = (
            CreditNoteDocument.objects.get(
                refund_request=refund
            )
        )


        self.client.login(
            username="phase10dcustomer",
            password="pass12345",
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


        self.assertContains(
            response,
            "My Financial Documents",
        )


        self.assertContains(
            response,
            "INV-PHASE10D-001",
        )


        self.assertContains(
            response,
            credit_note.document_number,
        )
