from django.contrib.auth import get_user_model
from django.test import TestCase

from categories.models import Category
from products.models import Product

from .models import InventoryMovement

from .services import (
    InventoryAdjustmentError,
    adjust_product_stock,
)


class InventoryServiceTests(TestCase):

    def setUp(self):

        User = get_user_model()

        self.user = User.objects.create_user(
            username="inventorytester",
            password="testpass123",
        )

        self.category = Category.objects.create(
            name="Inventory Test",
            slug="inventory-test",
        )

        self.product = Product.objects.create(
            category=self.category,
            name="Inventory Product",
            slug="inventory-product",
            sku="INV-001",
            price="1000.00",
            stock=10,
            reserved_stock=2,
            is_active=True,
        )

    def test_restock_creates_movement(self):

        adjust_product_stock(
            product_id=self.product.pk,
            movement_type="restock",
            quantity=5,
            reference="INV-100",
            user=self.user,
        )

        self.product.refresh_from_db()

        self.assertEqual(
            self.product.stock,
            15,
        )

        movement = (
            InventoryMovement.objects.get()
        )

        self.assertEqual(
            movement.stock_before,
            10,
        )

        self.assertEqual(
            movement.stock_after,
            15,
        )

    def test_cannot_reduce_below_reserved(self):

        with self.assertRaises(
            InventoryAdjustmentError
        ):

            adjust_product_stock(
                product_id=self.product.pk,
                movement_type="damaged",
                quantity=9,
                user=self.user,
            )

        self.product.refresh_from_db()

        self.assertEqual(
            self.product.stock,
            10,
        )
