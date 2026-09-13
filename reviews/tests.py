from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from categories.models import Category
from orders.models import Order, OrderItem
from products.models import Product
from reviews.models import Review


User = get_user_model()


class ReviewSecurityTests(TestCase):

    def setUp(self):

        self.user = User.objects.create_user(
            username="review-buyer",
            email="buyer@example.com",
            password="StrongPass123!",
            is_active=True,
            email_verified=True,
        )

        self.non_buyer = User.objects.create_user(
            username="review-nonbuyer",
            email="nonbuyer@example.com",
            password="StrongPass123!",
            is_active=True,
            email_verified=True,
        )

        self.category = Category.objects.create(
            name="Review Test",
            slug="review-test",
        )

        self.product = Product.objects.create(
            category=self.category,
            name="Gaming Laptop",
            slug="gaming-laptop-test",
            description="Test product",
            sku="REV-001",
            price=Decimal("100000.00"),
            stock=10,
            image="products/test.jpg",
            is_active=True,
        )

        self.order = Order.objects.create(
            user=self.user,
            order_number="REV-ORDER-001",

            full_name="Review Buyer",
            phone="0712345678",
            email="buyer@example.com",

            county="Nairobi",
            city="Nairobi",
            estate="CBD",
            house_number="1",

            subtotal=Decimal("100000.00"),
            shipping_cost=Decimal("0.00"),
            discount=Decimal("0.00"),
            total_amount=Decimal("100000.00"),

            payment_status="paid",
            status="confirmed",
            inventory_status="consumed",
        )

        OrderItem.objects.create(
            order=self.order,
            product=self.product,
            product_name=self.product.name,
            price=self.product.price,
            quantity=1,
            subtotal=self.product.price,
        )

    def test_non_buyer_cannot_review(self):

        self.client.force_login(
            self.non_buyer
        )

        response = self.client.post(
            reverse(
                "submit_review",
                args=[self.product.pk],
            ),
            {
                "rating": "5",
                "comment": "Trying to review.",
            },
        )

        self.assertEqual(
            response.status_code,
            302,
        )

        self.assertFalse(
            Review.objects.filter(
                product=self.product,
                user=self.non_buyer,
            ).exists()
        )

    def test_paid_buyer_can_review(self):

        self.client.force_login(
            self.user
        )

        response = self.client.post(
            reverse(
                "submit_review",
                args=[self.product.pk],
            ),
            {
                "rating": "5",
                "comment": "Excellent laptop.",
            },
        )

        self.assertEqual(
            response.status_code,
            302,
        )

        review = Review.objects.get(
            product=self.product,
            user=self.user,
        )

        self.assertEqual(
            review.rating,
            5,
        )

        self.assertTrue(
            review.verified_purchase
        )

    def test_review_submission_rejects_get(self):

        self.client.force_login(
            self.user
        )

        response = self.client.get(
            reverse(
                "submit_review",
                args=[self.product.pk],
            )
        )

        self.assertEqual(
            response.status_code,
            405,
        )

    def test_non_buyer_does_not_see_review_form(self):

        self.client.force_login(
            self.non_buyer
        )

        response = self.client.get(
            reverse(
                "product_detail",
                args=[self.product.slug],
            )
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertNotContains(
            response,
            "Submit Review",
        )

        self.assertContains(
            response,
            "Only customers who purchased this product",
        )

    def test_buyer_sees_review_form(self):

        self.client.force_login(
            self.user
        )

        response = self.client.get(
            reverse(
                "product_detail",
                args=[self.product.slug],
            )
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertContains(
            response,
            "Submit Review",
        )

    def test_product_page_uses_blue_brand_classes(self):

        response = self.client.get(
            reverse(
                "product_detail",
                args=[self.product.slug],
            )
        )

        self.assertContains(
            response,
            'class="text-primary"',
        )

        self.assertContains(
            response,
            'btn btn-primary add-to-cart-btn',
        )

        self.assertNotContains(
            response,
            'btn btn-success add-to-cart-btn',
        )
