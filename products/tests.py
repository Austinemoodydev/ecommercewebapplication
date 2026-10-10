from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from django.db import IntegrityError, transaction

from accounts.models import CustomUser
from categories.models import Category
from cart.models import CartItem
from .models import Brand, Product, ProductOption, ProductOptionValue, ProductVariant


class ProductVariantTests(TestCase):
	def test_product_sku_is_generated_once_and_remains_stable(self):
		category = Category.objects.create(name="Electronics", slug="electronics-sku")
		brand = Brand.objects.create(name="Samsung", slug="samsung-sku")
		product = Product.objects.create(
			category=category, brand=brand, name="Galaxy Phone",
			slug="galaxy-phone", description="Phone", price=Decimal("50000"),
		)
		expected = f"ELE-SAM-{product.pk:04d}"
		self.assertEqual(product.sku, expected)

		product.name = "Renamed Galaxy Phone"
		product.save()
		self.assertEqual(product.sku, expected)

	def test_variant_sku_is_generated_from_product_sku(self):
		category = Category.objects.create(name="Fashion", slug="fashion-sku")
		product = Product.objects.create(
			category=category, name="Jacket", slug="jacket-sku",
			description="Jacket", price=Decimal("5000"),
		)
		variant = ProductVariant.objects.create(product=product, name="Large", stock=2)
		self.assertEqual(variant.sku, f"{product.sku}-V{variant.pk:02d}")

	def test_manual_sku_is_normalized_and_duplicate_is_rejected(self):
		category = Category.objects.create(name="Appliances", slug="appliances-sku")
		first = Product.objects.create(
			category=category, name="Kettle", slug="kettle-sku",
			description="Kettle", price=Decimal("2000"), sku="  app-ket-9001  ",
		)
		self.assertEqual(first.sku, "APP-KET-9001")

		with self.assertRaises(IntegrityError), transaction.atomic():
			Product.objects.create(
				category=category, name="Second Kettle", slug="second-kettle-sku",
				description="Kettle", price=Decimal("2500"), sku="app-ket-9001",
			)

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

		response = self.client.post(reverse("add_to_cart", args=[product.id]), {"variant": variant.id})

		self.assertEqual(response.status_code, 200)
		item = CartItem.objects.get(cart__user=user)
		self.assertEqual(item.variant, variant)
		self.assertEqual(item.subtotal, Decimal("25.00"))

	def test_variant_display_name_includes_colour(self):
		category = Category.objects.create(name="Displays", slug="displays")
		product = Product.objects.create(
			category=category, name="Monitor", slug="monitor",
			description="Monitor", sku="MONITOR", price=Decimal("10000"), stock=0,
		)
		variant = ProductVariant.objects.create(
			product=product, name="27 inch", colour="Black",
			sku="MONITOR-27-BLK", stock=4,
		)

		self.assertEqual(variant.display_name, "27 inch — Black")

	def test_product_with_variants_requires_a_selection(self):
		category = Category.objects.create(name="Colours", slug="colours")
		product = Product.objects.create(
			category=category, name="T-shirt", slug="t-shirt",
			description="T-shirt", sku="TSHIRT", price=Decimal("1000"), stock=5,
		)
		ProductVariant.objects.create(
			product=product, name="Red", colour="Red", colour_code="#ff0000",
			sku="TSHIRT-RED", stock=2,
		)

		response = self.client.post(reverse("add_to_cart", args=[product.id]))

		self.assertEqual(response.status_code, 400)
		self.assertEqual(response.json()["error"], "Please choose an available product option.")

	def test_out_of_stock_variant_cannot_be_added(self):
		category = Category.objects.create(name="Shoes", slug="shoes")
		product = Product.objects.create(
			category=category, name="Runner", slug="runner",
			description="Runner", sku="RUNNER", price=Decimal("3000"), stock=5,
		)
		variant = ProductVariant.objects.create(
			product=product, name="Blue", colour="Blue", sku="RUNNER-BLUE", stock=0,
		)

		response = self.client.post(
			reverse("add_to_cart", args=[product.id]), {"variant": variant.id}
		)

		self.assertEqual(response.status_code, 400)
		self.assertEqual(response.json()["error"], "That option is currently out of stock.")

	def test_product_page_contains_live_variant_data(self):
		category = Category.objects.create(name="Phones", slug="phones")
		product = Product.objects.create(
			category=category, name="Phone", slug="phone",
			description="Phone", sku="PHONE", price=Decimal("20000"), stock=0,
			image="products/test-phone.jpg",
		)
		ProductVariant.objects.create(
			product=product, name="128 GB", colour="Black", colour_code="#000000",
			sku="PHONE-BLK", price=Decimal("22000"), stock=3,
		)

		response = self.client.get(reverse("product_detail", args=[product.slug]))

		self.assertContains(response, 'data-colour="Black"')
		self.assertContains(response, 'data-stock="3"')
		self.assertContains(response, "Choose an option")

	def test_structured_options_are_rendered_and_identify_exact_variant(self):
		category = Category.objects.create(name="Clothing", slug="clothing")
		product = Product.objects.create(
			category=category, name="T-shirt", slug="structured-shirt",
			description="Shirt", sku="SHIRT", price=Decimal("1500"), stock=0,
			image="products/test-shirt.jpg",
		)
		size = ProductOption.objects.create(product=product, name="Size", position=0)
		colour = ProductOption.objects.create(product=product, name="Colour", position=1)
		medium = ProductOptionValue.objects.create(option=size, value="Medium")
		black = ProductOptionValue.objects.create(option=colour, value="Black")
		variant = ProductVariant.objects.create(
			product=product, name="Medium Black", sku="SHIRT-M-BLK", stock=5,
		)
		variant.option_values.set([medium, black])

		response = self.client.get(reverse("product_detail", args=[product.slug]))

		self.assertContains(response, "Select size")
		self.assertContains(response, "Select colour")
		self.assertContains(response, f'data-values="{medium.id},{black.id}"')
		self.assertEqual(variant.display_name, "Size: Medium / Colour: Black")
