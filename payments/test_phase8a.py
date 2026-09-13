from accounts.store_roles import STORE_OWNER
from django.contrib.auth.models import Group
from decimal import Decimal

from django.contrib.auth import (
    get_user_model,
)

from django.test import TestCase

from django.urls import reverse

from orders.models import (
    Order,
    OrderItem,
)

from categories.models import Category
from products.models import Product

from payments.models import (
    RefundRequest,
    ReturnRequest,
    ReturnRequestItem,
)


User = get_user_model()


class Phase8ATests(TestCase):

    def setUp(self):

        self.customer = (
            User.objects.create_user(
                username="returncustomer",
                password="pass12345",
                role=User.CUSTOMER,
            )
        )

        self.staff = (
            User.objects.create_user(
                username="returnstaff",
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
                name="Returns Test Category",
                slug="returns-test-category",
            )
        )

        self.product = (
            Product.objects.create(
                category=self.category,

                name="Return Test Product",
                slug="return-test-product",
                sku="RET-001",
                price=Decimal("1000.00"),
                stock=10,
                reserved_stock=0,
                is_active=True,
            )
        )

        self.order = Order.objects.create(
            user=self.customer,
            order_number="RETURN-ORDER-001",
            full_name="Return Customer",
            phone="0712345678",
            email="return@example.com",
            county="Nairobi",
            city="Nairobi",
            estate="CBD",
            house_number="1",
            subtotal=Decimal("2000.00"),
            shipping_cost=Decimal("0.00"),
            discount=Decimal("0.00"),
            total_amount=Decimal("2000.00"),
            status="delivered",
            payment_status="paid",
            inventory_status="consumed",
        )

        self.item = OrderItem.objects.create(
            order=self.order,
            product=self.product,
            product_name=self.product.name,
            price=Decimal("1000.00"),
            quantity=2,
            subtotal=Decimal("2000.00"),
        )


    def test_customer_can_request_item_return(
        self
    ):

        self.client.login(
            username="returncustomer",
            password="pass12345",
        )

        response = self.client.post(
            reverse(
                "request_return",
                kwargs={
                    "order_number": (
                        self.order.order_number
                    )
                },
            ),
            {
                "request_type": "return",
                "reason": "Item not suitable",
                f"quantity_{self.item.pk}": "1",
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
            line.quantity,
            1,
        )


    def test_staff_can_approve_return(
        self
    ):

        request_obj = (
            ReturnRequest.objects.create(
                order=self.order,
                request_type="return",
                reason="Test",
            )
        )

        ReturnRequestItem.objects.create(
            return_request=request_obj,
            order_item=self.item,
            quantity=1,
        )

        self.client.login(
            username="returnstaff",
            password="pass12345",
        )

        response = self.client.post(
            reverse(
                "admin_return_review",
                kwargs={
                    "pk": request_obj.pk
                },
            ),
            {
                "action": "approve",
                "staff_note": "Approved",
            },
        )

        self.assertEqual(
            response.status_code,
            302,
        )

        request_obj.refresh_from_db()

        self.assertEqual(
            request_obj.status,
            "approved",
        )


    def test_refund_requires_real_reference(
        self
    ):

        refund = RefundRequest.objects.create(
            order=self.order,
            amount=Decimal("500.00"),
            reason="Test refund",
            status="approved",
        )

        self.client.login(
            username="returnstaff",
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
                "external_reference": "",
            },
        )

        self.assertEqual(
            response.status_code,
            302,
        )

        refund.refresh_from_db()

        self.assertEqual(
            refund.status,
            "approved",
        )
