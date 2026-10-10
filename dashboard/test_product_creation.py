import shutil
import tempfile
from io import BytesIO

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from PIL import Image

from categories.models import Category
from products.models import Product


TEST_MEDIA_ROOT = tempfile.mkdtemp(prefix="product-create-tests-")


def product_image():
    stream = BytesIO()
    Image.new("RGB", (40, 40), "#2563eb").save(stream, format="PNG")
    return SimpleUploadedFile(
        "product.png", stream.getvalue(), content_type="image/png"
    )


@override_settings(MEDIA_ROOT=TEST_MEDIA_ROOT, MFA_STAFF_ENFORCEMENT=False)
class AdminProductCreationTests(TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEST_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.admin = get_user_model().objects.create_superuser(
            username="catalog-admin",
            email="catalog@example.com",
            password="StrongPass123!",
        )
        self.category = Category.objects.create(
            name="Electronics", slug="electronics"
        )
        self.client.force_login(self.admin)

    def valid_data(self):
        return {
            "name": "Test Camera",
            "sku": "",
            "category": self.category.pk,
            "brand": "",
            "description": "A clear product description.",
            "price": "12000",
            "cost_price": "8000",
            "stock": "14",
            "low_stock_threshold": "3",
            "discount_price": "10000",
            "featured": "on",
            "is_active": "on",
        }

    def test_valid_product_is_created_and_reports_success(self):
        data = self.valid_data()
        data["image"] = product_image()
        response = self.client.post(
            reverse("admin_product_create"), data, follow=True
        )

        product = Product.objects.get(name="Test Camera")
        self.assertEqual(
            response.redirect_chain,
            [(reverse("admin_product_detail", args=[product.pk]), 302)],
        )
        self.assertEqual(product.stock, 14)
        self.assertEqual(product.low_stock_threshold, 3)
        self.assertTrue(product.sku.startswith("ELE-GEN-"))

        self.assertContains(response, "Product added successfully")
        self.assertContains(response, product.sku)

    def test_invalid_product_displays_clear_error_summary(self):
        response = self.client.post(
            reverse("admin_product_create"), self.valid_data()
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(Product.objects.filter(name="Test Camera").exists())
        self.assertContains(response, "Product could not be saved")
        self.assertContains(response, "Primary image")
        self.assertContains(response, "This field is required")

