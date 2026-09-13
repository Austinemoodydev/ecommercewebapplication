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
    Order,
    OrderItem,
)

from payments.models import (
    MpesaTransaction,
    RefundRequest,
)

from products.models import Product


User = get_user_model()


class Phase10DocumentTests(
    TestCase
):

    def setUp(self):

        self.customer = (
            User.objects.create_user(
                username="phase10customer",
                password="pass12345",
                role=User.CUSTOMER,
            )
        )


        self.other_customer = (
            User.objects.create_user(
                username="phase10other",
                password="pass12345",
                role=User.CUSTOMER,
            )
        )


        self.staff = (
            User.objects.create_user(
                username="phase10staff",
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
                name="Phase 10",
                slug="phase-10",
            )
        )


        self.product = (
            Product.objects.create(
                category=self.category,
                name="Receipt Laptop",
                slug="receipt-laptop",
                sku="P10-001",
                price=Decimal(
                    "50000.00"
                ),
                cost_price=Decimal(
                    "40000.00"
                ),
                stock=10,
                reserved_stock=0,
                is_active=True,
            )
        )


        self.order = (
            Order.objects.create(
                user=self.customer,
                order_number="PHASE10-001",
                full_name="Phase Ten Customer",
                phone="0712345678",
                email="phase10@example.com",
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
                payment_status="paid",
                inventory_status="consumed",
                payment_method="mpesa",
            )
        )


        OrderItem.objects.create(
            order=self.order,
            product=self.product,
            product_name=self.product.name,
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


        MpesaTransaction.objects.create(
            order=self.order,
            phone_number="254712345678",
            amount=Decimal(
                "50500.00"
            ),
            mpesa_receipt_number="TESTP10MPESA",
            status="success",
        )


    def test_customer_can_view_own_invoice(
        self
    ):

        self.client.login(
            username="phase10customer",
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

        self.assertContains(
            response,
            "INV-PHASE10-001",
        )

        self.assertContains(
            response,
            "Receipt Laptop",
        )


    def test_customer_cannot_view_another_customer_invoice(
        self
    ):

        self.client.login(
            username="phase10other",
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


    def test_customer_receipt_contains_mpesa_reference(
        self
    ):

        self.client.login(
            username="phase10customer",
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


        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertContains(
            response,
            "TESTP10MPESA",
        )


    def test_unpaid_order_has_no_receipt(
        self
    ):

        self.order.payment_status = (
            "pending"
        )

        self.order.save(
            update_fields=[
                "payment_status",
                "updated_at",
            ]
        )


        self.client.login(
            username="phase10customer",
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


        self.assertEqual(
            response.status_code,
            404,
        )


    def test_staff_can_view_admin_invoice(
        self
    ):

        self.client.login(
            username="phase10staff",
            password="pass12345",
        )


        response = self.client.get(
            reverse(
                "admin_order_invoice",
                args=[
                    self.order.order_number
                ],
            )
        )


        self.assertEqual(
            response.status_code,
            200,
        )


    def test_receipt_shows_processed_refund(
        self
    ):

        RefundRequest.objects.create(
            order=self.order,
            amount=Decimal(
                "5000.00"
            ),
            reason="Test refund",
            status="processed",
            external_reference="REF-P10-001",
            processed_by=self.staff,
        )


        self.order.payment_status = (
            "partially_refunded"
        )

        self.order.save(
            update_fields=[
                "payment_status",
                "updated_at",
            ]
        )


        self.client.login(
            username="phase10customer",
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


        self.assertEqual(
            response.status_code,
            200,
        )


        self.assertContains(
            response,
            "REF-P10-001",
        )

        self.assertContains(
            response,
            "45,500",
        )
