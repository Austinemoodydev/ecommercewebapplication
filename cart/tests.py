from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from accounts.models import CustomUser
from categories.models import Category
from products.models import Product
from .models import Cart


class CartServiceTests(TestCase):
	def setUp(self):
		self.user = CustomUser.objects.create_user(username="cart-user", password="test-password")
		category = Category.objects.create(name="Cart category", slug="cart-category")
		self.product = Product.objects.create(
			category=category, name="Cart product", slug="cart-product",
			description="Cart product description", sku="CART-001",
			price=Decimal("10.00"), stock=1,
		)
		self.client.force_login(self.user)

	def test_cart_cannot_increase_beyond_available_stock(self):
		self.client.post(reverse("add_to_cart", args=[self.product.id]))
		cart = Cart.objects.get(user=self.user)

		self.client.post(reverse("increase_quantity", args=[cart.items.get().id]))

		self.assertEqual(cart.items.get().quantity, 1)
