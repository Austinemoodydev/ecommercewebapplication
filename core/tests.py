from decimal import Decimal

from django.test import TestCase, override_settings
from django.urls import reverse

from categories.models import Category
from products.models import Product


@override_settings(SITE_URL="https://shop.example.com")
class IndexingTests(TestCase):
	def setUp(self):
		category = Category.objects.create(name="SEO category", slug="seo-category")
		Product.objects.create(
			category=category,
			name="SEO product",
			slug="seo-product",
			description="A product for indexing tests.",
			sku="SEO-001",
			price=Decimal("20.00"),
			stock=2,
		)

	def test_robots_txt_advertises_sitemap_and_blocks_private_sections(self):
		response = self.client.get(reverse("robots"))

		self.assertEqual(response.status_code, 200)
		content = response.content.decode()
		self.assertIn("Sitemap: https://shop.example.com/sitemap.xml", content)
		self.assertIn("Disallow: /checkout/", content)
		self.assertIn("Disallow: /payments/", content)

	def test_sitemap_contains_public_product_and_category_urls(self):
		response = self.client.get(reverse("sitemap"))

		self.assertEqual(response.status_code, 200)
		content = response.content.decode()
		self.assertIn("/shop/seo-product/", content)
		self.assertIn("/categories/seo-category/", content)
from django.test import TestCase

# Create your tests here.
