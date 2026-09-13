from accounts.store_roles import STORE_OWNER
from django.contrib.auth.models import Group
from decimal import Decimal
from datetime import timedelta

from django.contrib.auth import (
    get_user_model,
)

from django.test import TestCase

from django.urls import reverse

from django.utils import timezone

from categories.models import Category

from products.models import Product

from orders.models import (
    Order,
    OrderItem,
)

from payments.models import (
    RefundRequest,
    ReturnRequest,
    ReturnRequestItem,
)

from payments.returns_services import (
    remaining_refundable_amount,
    remaining_returnable_quantity,
)


User = get_user_model()


class Phase8BTests(TestCase):

    def setUp(self):

        self.customer = (
            User.objects.create_user(
                username="phase8bcustomer",
                password="pass12345",
                role=User.CUSTOMER,
            )
        )

        self.staff = (
            User.objects.create_user(
                username="phase8bstaff",
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
                name="Phase8B Category",
                slug="phase8b-category",
            )
        )

        self.product = (
            Product.objects.create(
                category=self.category,
                name="Phase8B Product",
                slug="phase8b-product",
                sku="P8B-001",
                price=Decimal("1000.00"),
                stock=10,
                reserved_stock=0,
                is_active=True,
            )
        )

        self.order = Order.objects.create(
            user=self.customer,
            order_number="PHASE8B-001",
            full_name="Phase 8B Customer",
            phone="0712345678",
            email="phase8b@example.com",
            county="Nairobi",
            city="Nairobi",
            estate="CBD",
            house_number="1",
            subtotal=Decimal("3000.00"),
            shipping_cost=Decimal("0.00"),
            discount=Decimal("0.00"),
            total_amount=Decimal("3000.00"),
            status="delivered",
            payment_status="paid",
            inventory_status="consumed",
        )

        self.item = (
            OrderItem.objects.create(
                order=self.order,
                product=self.product,
                product_name=self.product.name,
                price=Decimal("1000.00"),
                quantity=3,
                subtotal=Decimal("3000.00"),
            )
        )


    def test_duplicate_return_quantity_is_blocked(
        self
    ):

        first = ReturnRequest.objects.create(
            order=self.order,
            request_type="return",
            reason="First return",
            status="completed",
        )

        ReturnRequestItem.objects.create(
            return_request=first,
            order_item=self.item,
            quantity=2,
        )

        self.assertEqual(
            remaining_returnable_quantity(
                self.item
            ),
            1,
        )


    def test_pending_refund_reserves_balance(
        self
    ):

        RefundRequest.objects.create(
            order=self.order,
            amount=Decimal("1000.00"),
            reason="Pending refund",
            status="approved",
        )

        self.assertEqual(
            remaining_refundable_amount(
                self.order,
                include_pending=True,
            ),
            Decimal("2000.00"),
        )


    def test_partial_refund_sets_partial_status(
        self
    ):

        refund = RefundRequest.objects.create(
            order=self.order,
            amount=Decimal("1000.00"),
            reason="Partial refund",
            status="approved",
        )

        self.client.login(
            username="phase8bstaff",
            password="pass12345",
        )

        response = self.client.post(
            reverse(
                "admin_refund_process",
                kwargs={
                    "pk": refund.pk
                },
            ),
            {
                "external_reference": (
                    "TEST-REF-001"
                ),
            },
        )

        self.assertEqual(
            response.status_code,
            302,
        )

        self.order.refresh_from_db()

        self.assertEqual(
            self.order.payment_status,
            "partially_refunded",
        )


    def test_customer_cannot_view_other_return(
        self
    ):

        other = User.objects.create_user(
            username="other8b",
            password="pass12345",
            role=User.CUSTOMER,
        )

        obj = ReturnRequest.objects.create(
            order=self.order,
            request_type="return",
            reason="Test",
        )

        self.client.login(
            username="other8b",
            password="pass12345",
        )

        response = self.client.get(
            reverse(
                "customer_return_detail",
                kwargs={
                    "pk": obj.pk
                },
            )
        )

        self.assertEqual(
            response.status_code,
            404,
        )
