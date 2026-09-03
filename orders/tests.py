from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from accounts.models import CustomUser
from categories.models import Category
from products.models import Product
from .models import Order, OrderItem
from .models import Coupon


class OrderCancellationTests(TestCase):
	def setUp(self):
		self.user = CustomUser.objects.create_user(username="buyer", password="test-password")
		category = Category.objects.create(name="Test category", slug="test-category")
		self.product = Product.objects.create(
			category=category,
			name="Test product",
			slug="test-product",
			description="Test product description",
			sku="TEST-001",
			price=Decimal("10.00"),
			stock=3,
			reserved_stock=2,
		)
		self.order = Order.objects.create(
			user=self.user,
			order_number="ORDER-001",
			full_name="Test Buyer",
			phone="0712345678",
			county="Nairobi",
			city="Nairobi",
			estate="Test Estate",
			house_number="1",
			subtotal=Decimal("20.00"),
			total_amount=Decimal("20.00"),
		)
		OrderItem.objects.create(
			order=self.order,
			product=self.product,
			product_name=self.product.name,
			price=self.product.price,
			quantity=2,
			subtotal=Decimal("20.00"),
		)

	def test_customer_can_cancel_unpaid_order_and_release_stock(self):
		self.client.force_login(self.user)

		response = self.client.post(reverse("cancel_order", args=[self.order.order_number]))

		self.assertRedirects(response, reverse("order_detail", args=[self.order.order_number]))
		self.order.refresh_from_db()
		self.product.refresh_from_db()
		self.assertEqual(self.order.status, "cancelled")
		self.assertEqual(self.product.reserved_stock, 0)

	def test_customer_cannot_cancel_paid_order(self):
		self.order.payment_status = "paid"
		self.order.status = "confirmed"
		self.order.save(update_fields=["payment_status", "status"])
		self.client.force_login(self.user)

		self.client.post(reverse("cancel_order", args=[self.order.order_number]))

		self.order.refresh_from_db()
		self.product.refresh_from_db()
		self.assertEqual(self.order.status, "confirmed")
		self.assertEqual(self.product.reserved_stock, 2)


class CouponTests(TestCase):
	def test_percentage_discount_is_capped_at_subtotal(self):
		coupon = Coupon.objects.create(code="HALF", discount_value=150)

		self.assertEqual(coupon.calculate_discount(Decimal("20.00")), Decimal("20.00"))
