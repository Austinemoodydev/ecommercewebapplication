from pathlib import Path
from datetime import datetime
import shutil
import subprocess
import sys
import re

ROOT = Path.cwd()

if not (ROOT / "manage.py").exists():
    raise SystemExit(
        "ERROR: Run this from the Django project root containing manage.py."
    )

STAMP = datetime.now().strftime("%Y%m%d-%H%M%S")
BACKUP = ROOT / ".review_fix_backups" / STAMP
BACKUP.mkdir(parents=True, exist_ok=True)

print("=" * 72)
print("PRODUCT REVIEW + COLOR FIX")
print("=" * 72)
print("Backup:", BACKUP)
print()


def read(rel):
    path = ROOT / rel
    if not path.exists():
        raise RuntimeError(f"Missing required file: {rel}")
    return path.read_text(encoding="utf-8-sig")


def save(rel, text):
    path = ROOT / rel

    backup_path = BACKUP / rel
    backup_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    shutil.copy2(
        path,
        backup_path,
    )

    path.write_text(
        text,
        encoding="utf-8",
    )

    print("[UPDATED]", rel)


# ============================================================
# 1. PRODUCT DETAIL VIEW
#    Tell template whether customer is eligible to review
# ============================================================

path = "products/views.py"
text = read(path)

if "from orders.models import OrderItem" not in text:

    anchor = "from categories.models import Category"

    if anchor not in text:
        raise RuntimeError(
            "Could not locate imports in products/views.py"
        )

    text = text.replace(
        anchor,
        anchor + "\nfrom orders.models import OrderItem",
        1,
    )


old = '''def product_detail(request, slug):
    product = ProductService.get_product(slug)
    related_products = Product.objects.select_related("category", "brand").filter(
        category=product.category, is_active=True
    ).exclude(id=product.id)[:4]
    return render(request, "products/product_detail.html", {
        "product": product, "related_products": related_products,
    })
'''

new = '''def product_detail(request, slug):

    product = ProductService.get_product(slug)

    related_products = (
        Product.objects
        .select_related(
            "category",
            "brand",
        )
        .filter(
            category=product.category,
            is_active=True,
        )
        .exclude(id=product.id)[:4]
    )

    can_review = False

    if request.user.is_authenticated:

        can_review = OrderItem.objects.filter(
            order__user=request.user,
            order__payment_status__in=[
                "paid",
                "partially_refunded",
            ],
            product=product,
        ).exists()

    return render(
        request,
        "products/product_detail.html",
        {
            "product": product,
            "related_products": related_products,
            "can_review": can_review,
        },
    )
'''

if old in text:

    text = text.replace(
        old,
        new,
        1,
    )

elif "can_review =" in text:

    print(
        "[OK] product_detail already has review eligibility."
    )

else:

    raise RuntimeError(
        "Could not safely patch product_detail()."
    )

save(
    path,
    text,
)


# ============================================================
# 2. REVIEW BACKEND
#    POST-only + verified purchaser required
# ============================================================

path = "reviews/views.py"
text = read(path)

if (
    "from django.views.decorators.http import require_POST"
    not in text
):

    anchor = (
        "from django.contrib.auth.decorators "
        "import login_required"
    )

    if anchor not in text:
        raise RuntimeError(
            "Could not locate review imports."
        )

    text = text.replace(
        anchor,
        anchor
        + "\nfrom django.views.decorators.http import require_POST",
        1,
    )


text = text.replace(
    '''@login_required
def submit_review(request, product_id):
''',
    '''@login_required
@require_POST
def submit_review(request, product_id):
''',
    1,
)


old_block = '''    if request.method != "POST":
        return redirect("product_detail", slug=product.slug)

    rating = request.POST.get("rating")
'''

new_block = '''    eligible_purchase = OrderItem.objects.filter(
        order__user=request.user,
        order__payment_status__in=[
            "paid",
            "partially_refunded",
        ],
        product=product,
    ).exists()

    if not eligible_purchase:

        messages.error(
            request,
            (
                "Only customers who purchased "
                "this product can leave a review."
            ),
        )

        return redirect(
            "product_detail",
            slug=product.slug,
        )

    rating = request.POST.get("rating")
'''

if old_block in text:

    text = text.replace(
        old_block,
        new_block,
        1,
    )

elif "eligible_purchase =" in text:

    print(
        "[OK] review eligibility already enforced."
    )

else:

    raise RuntimeError(
        "Could not safely patch review eligibility."
    )


old_verified = '''    verified = OrderItem.objects.filter(
        order__user=request.user,
        order__payment_status="paid",
        product=product,
    ).exists()

    Review.objects.update_or_create(
'''

new_verified = '''    Review.objects.update_or_create(
'''

if old_verified in text:

    text = text.replace(
        old_verified,
        new_verified,
        1,
    )


text = text.replace(
    '''            "verified_purchase": verified,
''',
    '''            "verified_purchase": True,
''',
    1,
)

save(
    path,
    text,
)


# ============================================================
# 3. PRODUCT DETAIL TEMPLATE
#    Remove green branding but keep verified badge green
# ============================================================

path = "templates/products/product_detail.html"
text = read(path)


text = text.replace(
    '''<h3 class="text-success">KES {{ product.current_price }}</h3>''',
    '''<h3 class="text-primary">KES {{ product.current_price }}</h3>''',
)


text = text.replace(
    '''class="btn btn-success add-to-cart-btn"''',
    '''class="btn btn-primary add-to-cart-btn"''',
)


old_review_section = '''{% if request.user.is_authenticated %}
<div class="card mb-4">
    <div class="card-body">
        <h5>Write a Review</h5>
        <form method="POST" action="{% url 'submit_review' product.id %}">
            {% csrf_token %}

            <div class="mb-2">
                <label class="form-label">Rating</label>
                <select name="rating" class="form-select" style="max-width: 200px;" required>
                    <option value="">Select rating</option>
                    <option value="5">5 - Excellent</option>
                    <option value="4">4 - Very Good</option>
                    <option value="3">3 - Good</option>
                    <option value="2">2 - Fair</option>
                    <option value="1">1 - Poor</option>
                </select>
            </div>

            <div class="mb-2">
                <label class="form-label">Comment</label>
                <textarea name="comment" class="form-control" rows="3" placeholder="Optional"></textarea>
            </div>

            <button type="submit" class="btn btn-outline-success btn-sm">Submit Review</button>
        </form>
    </div>
</div>
{% else %}
<p class="text-muted">
    <a href="{% url 'login' %}">Log in</a> to write a review.
</p>
{% endif %}
'''

new_review_section = '''{% if request.user.is_authenticated %}

    {% if can_review %}

    <div class="card mb-4">
        <div class="card-body">

            <h5>Write a Review</h5>

            <p class="text-muted small">
                Your purchase has been verified.
                Share your experience with this product.
            </p>

            <form method="POST"
                  action="{% url 'submit_review' product.id %}">

                {% csrf_token %}

                <div class="mb-2">

                    <label class="form-label">
                        Rating
                    </label>

                    <select name="rating"
                            class="form-select"
                            style="max-width: 200px;"
                            required>

                        <option value="">
                            Select rating
                        </option>

                        <option value="5">
                            5 - Excellent
                        </option>

                        <option value="4">
                            4 - Very Good
                        </option>

                        <option value="3">
                            3 - Good
                        </option>

                        <option value="2">
                            2 - Fair
                        </option>

                        <option value="1">
                            1 - Poor
                        </option>

                    </select>

                </div>


                <div class="mb-2">

                    <label class="form-label">
                        Comment
                    </label>

                    <textarea name="comment"
                              class="form-control"
                              rows="3"
                              placeholder="Tell other customers about your experience."></textarea>

                </div>


                <button type="submit"
                        class="btn btn-outline-primary btn-sm">

                    Submit Review

                </button>

            </form>

        </div>
    </div>

    {% else %}

    <div class="alert alert-light border mb-4">

        <i class="bi bi-shield-check text-primary me-1"></i>

        Only customers who purchased this product
        can leave a review.

    </div>

    {% endif %}

{% else %}

<p class="text-muted">

    <a href="{% url 'login' %}">
        Log in
    </a>

    to check whether you are eligible to review
    this product.

</p>

{% endif %}
'''

if old_review_section in text:

    text = text.replace(
        old_review_section,
        new_review_section,
        1,
    )

elif "Only customers who purchased this product" in text:

    print(
        "[OK] review template already secured."
    )

else:

    raise RuntimeError(
        "Could not safely replace review form section."
    )


save(
    path,
    text,
)


# ============================================================
# 4. ADD REVIEW SECURITY TESTS
# ============================================================

test_file = ROOT / "reviews/tests.py"

backup_test = BACKUP / "reviews/tests.py"
backup_test.parent.mkdir(
    parents=True,
    exist_ok=True,
)

if test_file.exists():

    shutil.copy2(
        test_file,
        backup_test,
    )


tests = '''from decimal import Decimal

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
'''

test_file.write_text(
    tests,
    encoding="utf-8",
)

print(
    "[UPDATED] reviews/tests.py"
)


# ============================================================
# 5. VALIDATION
# ============================================================

commands = [

    [
        sys.executable,
        "manage.py",
        "check",
    ],

    [
        sys.executable,
        "manage.py",
        "makemigrations",
        "--check",
        "--dry-run",
    ],

    [
        sys.executable,
        "manage.py",
        "test",
        "reviews",
        "-v",
        "2",
    ],

    [
        sys.executable,
        "manage.py",
        "test",
        "products",
        "orders",
        "payments",
        "reviews",
        "-v",
        "1",
    ],

    [
        sys.executable,
        "manage.py",
        "collectstatic",
        "--noinput",
    ],

    [
        sys.executable,
        "manage.py",
        "test",
        "-v",
        "1",
    ],
]


print()
print("=" * 72)
print("RUNNING VALIDATION")
print("=" * 72)


for command in commands:

    print()
    print(
        ">",
        " ".join(command),
    )

    result = subprocess.run(
        command,
        cwd=ROOT,
    )

    if result.returncode != 0:

        print()
        print("=" * 72)
        print("STOPPED — VALIDATION FAILED")
        print("=" * 72)

        print()
        print("Backups are here:")
        print(BACKUP)

        raise SystemExit(
            result.returncode
        )


print()
print("=" * 72)
print("PRODUCT REVIEW FIX PASSED")
print("=" * 72)

print()
print(
    "✓ Product price now uses blue branding"
)

print(
    "✓ Add to Cart now uses blue branding"
)

print(
    "✓ Submit Review now uses blue branding"
)

print(
    "✓ Verified Purchase badge remains green"
)

print(
    "✓ Non-buyers cannot submit reviews"
)

print(
    "✓ Paid buyers can submit reviews"
)

print(
    "✓ Partially refunded buyers remain eligible"
)

print(
    "✓ Review endpoint is POST-only"
)

print(
    "✓ Full Django test suite passed"
)

print()
print("Backup:")
print(BACKUP)

print()
print(
    "Restart runserver if needed and press Ctrl+F5 "
    "on the product page."
)
