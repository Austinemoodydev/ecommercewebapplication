from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from accounts.models import CustomUser
from categories.models import Category
from cart.models import CartItem
from .models import Product, ProductVariant


class ProductVariantTests(TestCase):
	def test_customer_can_add_selected_variant_to_cart(self):
		user = CustomUser.objects.create_user(username="variant-user", password="test-password")
		category = Category.objects.create(name="Variant category", slug="variant-category")
		product = Product.objects.create(
			category=category,
			name="Variant product",
			slug="variant-product",
			description="Variant product description",
			sku="VARIANT-PRODUCT",
			price=Decimal("20.00"),
			stock=5,
		)
		variant = ProductVariant.objects.create(
			product=product,
			name="Large / Blue",
			sku="VARIANT-L-B",
			price=Decimal("25.00"),
			stock=2,
		)
		self.client.force_login(user)

		response = self.client.get(reverse("add_to_cart", args=[product.id]), {"variant": variant.id})

		self.assertEqual(response.status_code, 200)
		item = CartItem.objects.get(cart__user=user)
		self.assertEqual(item.variant, variant)
		self.assertEqual(item.subtotal, Decimal("25.00"))
