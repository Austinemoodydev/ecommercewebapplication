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
    RefundRequest,
)

from products.models import Product


User = get_user_model()


class Phase9AReportsTests(
    TestCase
):

    def setUp(self):

        self.staff = (
            User.objects.create_user(
                username="reportstaff",
                password="pass12345",
                role=User.ADMIN,
                is_staff=True,
            )
        )

        self.customer = (
            User.objects.create_user(
                username="reportcustomer",
                password="pass12345",
                role=User.CUSTOMER,
            )
        )

        self.category = (
            Category.objects.create(
                name="Reports Category",
                slug="reports-category",
            )
        )

        self.product = (
            Product.objects.create(
                category=self.category,
                name="Reports Product",
                slug="reports-product",
                sku="RPT-001",
                price=Decimal("2000.00"),
                cost_price=Decimal("1000.00"),
                stock=10,
                reserved_stock=0,
                is_active=True,
            )
        )

        self.order = (
            Order.objects.create(
                user=self.customer,
                order_number="REPORT-001",
                full_name="Report Customer",
                phone="0712345678",
                email="report@example.com",
                county="Nairobi",
                city="Nairobi",
                estate="CBD",
                house_number="1",
                subtotal=Decimal("4000.00"),
                shipping_cost=Decimal("300.00"),
                discount=Decimal("0.00"),
                total_amount=Decimal("4300.00"),
                status="delivered",
                payment_status="paid",
                inventory_status="consumed",
            )
        )

        OrderItem.objects.create(
            order=self.order,
            product=self.product,
            product_name=self.product.name,
            price=Decimal("2000.00"),
            quantity=2,
            subtotal=Decimal("4000.00"),
        )


    def test_staff_can_view_report(
        self
    ):

        self.client.login(
            username="reportstaff",
            password="pass12345",
        )

        response = self.client.get(
            reverse(
                "admin_sales_reports"
            )
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertContains(
            response,
            "Sales & Business Analytics",
        )

        self.assertContains(
            response,
            "4300.00",
        )


    def test_non_staff_cannot_view_report(
        self
    ):

        self.client.login(
            username="reportcustomer",
            password="pass12345",
        )

        response = self.client.get(
            reverse(
                "admin_sales_reports"
            )
        )

        self.assertNotEqual(
            response.status_code,
            200,
        )


    def test_processed_refund_reduces_net_revenue(
        self
    ):

        RefundRequest.objects.create(
            order=self.order,
            amount=Decimal("500.00"),
            reason="Report test refund",
            status="processed",
        )

        self.client.login(
            username="reportstaff",
            password="pass12345",
        )

        response = self.client.get(
            reverse(
                "admin_sales_reports"
            )
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertEqual(
            response.context[
                "gross_revenue"
            ],
            Decimal("4300.00"),
        )

        self.assertEqual(
            response.context[
                "processed_refunds"
            ],
            Decimal("500.00"),
        )

        self.assertEqual(
            response.context[
                "net_revenue"
            ],
            Decimal("3800.00"),
        )


    def test_csv_export(
        self
    ):

        self.client.login(
            username="reportstaff",
            password="pass12345",
        )

        response = self.client.get(
            reverse(
                "admin_sales_reports_csv"
            )
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertEqual(
            response[
                "Content-Type"
            ],
            "text/csv; charset=utf-8",
        )

        self.assertIn(
            "Sales Report",
            response.content.decode(
                "utf-8"
            ),
        )
