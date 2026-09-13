from accounts.store_roles import STORE_OWNER
from django.contrib.auth.models import Group
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import CustomUser
from categories.models import Category
from orders.models import Order, OrderItem
from products.models import Product


class AdminReportingTests(TestCase):
	def setUp(self):
		self.staff = CustomUser.objects.create_user(
			username="staff", password="test-password", is_staff=True
		)

		store_owner_group, _ = Group.objects.get_or_create(
		    name=STORE_OWNER,
		)

		self.staff.groups.add(
		    store_owner_group
		)
		self.customer = CustomUser.objects.create_user(
			username="customer", password="test-password"
		)
		category = Category.objects.create(name="Report category", slug="report-category")
		product = Product.objects.create(
			category=category,
			name="Report product",
			slug="report-product",
			description="Report product description",
			sku="REPORT-001",
			price=Decimal("30.00"),
			stock=4,
		)
		order = Order.objects.create(
			user=self.customer,
			order_number="ORDER-REPORT",
			full_name="Report Customer",
			phone="0712345678",
			county="Nairobi",
			city="Nairobi",
			estate="Test Estate",
			house_number="1",
			subtotal=Decimal("30.00"),
			total_amount=Decimal("30.00"),
			payment_status="paid",
		)
		self.order = order
		OrderItem.objects.create(
			order=order,
			product=product,
			product_name=product.name,
			price=product.price,
			quantity=1,
			subtotal=Decimal("30.00"),
		)

	def test_non_staff_cannot_view_sales_export(self):
		self.client.force_login(self.customer)

		response = self.client.get(reverse("admin_sales_export"))

		self.assertEqual(response.status_code, 302)

	def test_staff_can_export_paid_sales(self):
		self.client.force_login(self.staff)
		report_date = timezone.localtime(self.order.created_at).date().isoformat()

		response = self.client.get(reverse("admin_sales_export"), {
			"start": report_date,
			"end": report_date,
		})

		self.assertEqual(response.status_code, 200)
		self.assertEqual(response["Content-Type"], "text/csv")
		content = response.content.decode()
		self.assertIn("Order number,Date,Customer,Status,Payment status,Total", content)
		self.assertIn("ORDER-REPORT", content)
		self.assertIn("30.00", content)

	def test_customer_cannot_view_another_customers_order(self):
		other = CustomUser.objects.create_user(username="other", password="test-password")
		self.client.force_login(other)

		response = self.client.get(reverse("order_detail", args=[self.order.order_number]))

		self.assertEqual(response.status_code, 404)
