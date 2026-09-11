import json
from decimal import Decimal

from django.test import TestCase, override_settings
from django.urls import reverse
from django.core.exceptions import ValidationError

from accounts.models import CustomUser
from categories.models import Category
from orders.models import Order, OrderItem
from products.models import Product
from .models import MpesaTransaction, RefundRequest


@override_settings(MPESA_CALLBACK_SECRET="test-callback-secret")
class MpesaCallbackTests(TestCase):
	def setUp(self):
		user = CustomUser.objects.create_user(username="buyer", password="test-password")
		category = Category.objects.create(name="Test category", slug="test-category")
		product = Product.objects.create(
			category=category,
			name="Test product",
			slug="test-product",
			description="Test product description",
			sku="TEST-001",
			price=Decimal("10.00"),
			stock=3,
		)
		order = Order.objects.create(
			user=user,
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
			order=order,
			product=product,
			product_name=product.name,
			price=product.price,
			quantity=2,
			subtotal=Decimal("20.00"),
		)
		self.product = product
		self.order = order
		product.reserved_stock = 2
		product.save(update_fields=["reserved_stock"])
		self.transaction = MpesaTransaction.objects.create(
			order=order,
			phone_number="254712345678",
			amount=order.total_amount,
			checkout_request_id="ws_CO_123",
		)

	def callback_payload(self, amount=20):
		return {
			"Body": {
				"stkCallback": {
					"CheckoutRequestID": self.transaction.checkout_request_id,
					"ResultCode": 0,
					"ResultDesc": "The service request is processed successfully.",
					"CallbackMetadata": {
						"Item": [
							{"Name": "Amount", "Value": amount},
							{"Name": "MpesaReceiptNumber", "Value": "QAB123XYZ"},
						]
					},
				}
			}
		}

	def post_callback(self, payload):
		return self.client.post(
			reverse("mpesa_callback") + "?token=test-callback-secret",
			data=json.dumps(payload),
			content_type="application/json",
		)

	def test_successful_callback_confirms_order_and_decrements_stock(self):
		response = self.post_callback(self.callback_payload())

		self.assertEqual(response.status_code, 200)
		self.transaction.refresh_from_db()
		self.order.refresh_from_db()
		self.product.refresh_from_db()
		self.assertEqual(self.transaction.status, "success")
		self.assertEqual(self.order.payment_status, "paid")
		self.assertEqual(self.product.stock, 1)
		self.assertEqual(self.product.reserved_stock, 0)

	def test_duplicate_success_callback_does_not_decrement_stock_twice(self):
		self.post_callback(self.callback_payload())
		self.post_callback(self.callback_payload())

		self.product.refresh_from_db()
		self.assertEqual(self.product.stock, 1)

	def test_mismatched_amount_does_not_confirm_order_or_decrement_stock(self):
		response = self.post_callback(self.callback_payload(amount=19))

		self.assertEqual(response.status_code, 200)
		self.transaction.refresh_from_db()
		self.order.refresh_from_db()
		self.product.refresh_from_db()
		self.assertEqual(self.transaction.status, "failed")
		self.assertEqual(self.order.payment_status, "pending")
		self.assertEqual(self.product.stock, 3)

	def test_second_successful_stk_does_not_deduct_stock_twice(self):

		# First payment succeeds.
		self.post_callback(self.callback_payload())

		self.order.refresh_from_db()
		self.assertEqual(self.order.inventory_status, "consumed")

		# Create another STK transaction for the same order.
		second_transaction = MpesaTransaction.objects.create(
			order=self.order,
			phone_number="254712345678",
			amount=self.order.total_amount,
			checkout_request_id="ws_CO_SECOND",
		)

		second_payload = {
			"Body": {
				"stkCallback": {
					"CheckoutRequestID": second_transaction.checkout_request_id,
					"ResultCode": 0,
					"ResultDesc": "Success",
					"CallbackMetadata": {
						"Item": [
							{"Name": "Amount", "Value": 20},
							{"Name": "MpesaReceiptNumber", "Value": "SECOND123"},
						]
					},
				}
			}
		}

		self.post_callback(second_payload)

		self.product.refresh_from_db()

		self.assertEqual(self.product.stock, 1)


class RefundRequestTests(TestCase):
	def setUp(self):
		self.user = CustomUser.objects.create_user(username="refund-buyer", password="test-password")
		category = Category.objects.create(name="Refund category", slug="refund-category")
		product = Product.objects.create(
			category=category,
			name="Refund product",
			slug="refund-product",
			description="Refund product description",
			sku="REFUND-001",
			price=Decimal("25.00"),
			stock=1,
		)
		self.order = Order.objects.create(
			user=self.user,
			order_number="ORDER-REFUND",
			full_name="Refund Buyer",
			phone="0712345678",
			county="Nairobi",
			city="Nairobi",
			estate="Test Estate",
			house_number="1",
			subtotal=Decimal("25.00"),
			total_amount=Decimal("25.00"),
			status="delivered",
			payment_status="paid",
		)
		OrderItem.objects.create(
			order=self.order,
			product=product,
			product_name=product.name,
			price=product.price,
			quantity=1,
			subtotal=Decimal("25.00"),
		)

	def test_customer_can_submit_refund_request(self):
		self.client.force_login(self.user)

		response = self.client.post(reverse("request_refund", args=[self.order.order_number]), {
			"amount": "25.00",
			"reason": "The item arrived damaged.",
		})

		self.assertEqual(response.status_code, 200)
		refund = self.order.refund_requests.get()
		self.assertEqual(refund.status, "requested")

	def test_refund_request_requires_delivered_paid_order(self):
		self.order.status = "processing"
		self.order.save(update_fields=["status"])
		self.client.force_login(self.user)

		response = self.client.post(reverse("request_refund", args=[self.order.order_number]), {
			"amount": "25.00",
			"reason": "Changed my mind.",
		})

		self.assertEqual(response.status_code, 400)
		self.assertFalse(self.order.refund_requests.exists())

	def test_partial_refunds_cannot_exceed_order_total(self):
		RefundRequest.objects.create(order=self.order, amount=Decimal("20.00"), reason="Partial refund")
		refund = RefundRequest(order=self.order, amount=Decimal("10.00"), reason="Second partial refund")

		with self.assertRaises(ValidationError):
			refund.full_clean()

	def test_customer_can_request_replacement(self):
		self.client.force_login(self.user)

		response = self.client.post(reverse("request_return", args=[self.order.order_number]), {
			"request_type": "replacement",
			"reason": "The item is defective.",
		})

		self.assertEqual(response.status_code, 200)
		self.assertEqual(self.order.return_requests.get().request_type, "replacement")