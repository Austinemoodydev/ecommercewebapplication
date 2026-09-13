from pathlib import Path
from datetime import datetime
import shutil
import subprocess
import sys


ROOT = Path.cwd()

if not (ROOT / "manage.py").exists():
    raise SystemExit(
        "ERROR: Run this from the Django project root containing manage.py."
    )


# ============================================================
# BACKUP
# ============================================================

stamp = datetime.now().strftime("%Y%m%d-%H%M%S")

backup_dir = (
    ROOT
    / ".state_change_backups"
    / stamp
)

backup_dir.mkdir(
    parents=True,
    exist_ok=True,
)


def backup(path):

    if not path.exists():
        return

    destination = (
        backup_dir
        / path.relative_to(ROOT)
    )

    destination.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    shutil.copy2(
        path,
        destination,
    )


files = [
    ROOT / "cart" / "views.py",
    ROOT / "wishlist" / "views.py",
    ROOT / "orders" / "views.py",
    ROOT / "static" / "js" / "cart.js",
    ROOT / "static" / "js" / "wishlist.js",
    ROOT / "core" / "test_state_changing_get.py",
]

for path in files:
    backup(path)


# ============================================================
# 1. CART VIEWS -> POST ONLY
# ============================================================

cart_views = ROOT / "cart" / "views.py"

text = cart_views.read_text(
    encoding="utf-8-sig"
)


import_line = (
    "from django.views.decorators.http import require_POST"
)

if import_line not in text:

    marker = (
        "from django.shortcuts import "
        "get_object_or_404, render"
    )

    if marker not in text:
        raise SystemExit(
            "ERROR: cart/views.py import marker not found."
        )

    text = text.replace(
        marker,
        marker + "\n" + import_line,
        1,
    )


for function_name in [
    "add_to_cart",
    "increase_quantity",
    "decrease_quantity",
    "remove_from_cart",
]:

    marker = f"def {function_name}("

    if marker not in text:
        raise SystemExit(
            f"ERROR: cart view {function_name} not found."
        )

    decorator = (
        f"@require_POST\n"
        f"def {function_name}("
    )

    if decorator not in text:

        text = text.replace(
            marker,
            decorator,
            1,
        )


# Variant should now come from POST only.
text = text.replace(
    'variant_id = request.POST.get("variant") or request.GET.get("variant")',
    'variant_id = request.POST.get("variant")',
)


cart_views.write_text(
    text,
    encoding="utf-8",
)

print(
    "[PATCHED] Cart mutations are POST-only."
)


# ============================================================
# 2. WISHLIST TOGGLE -> POST ONLY
# ============================================================

wishlist_views = (
    ROOT
    / "wishlist"
    / "views.py"
)

text = wishlist_views.read_text(
    encoding="utf-8-sig"
)


if (
    "from django.views.decorators.http import require_POST"
    not in text
):

    marker = (
        "from django.shortcuts import "
        "get_object_or_404, render"
    )

    if marker not in text:
        raise SystemExit(
            "ERROR: wishlist/views.py import marker not found."
        )

    text = text.replace(
        marker,
        marker
        + "\n"
        + "from django.views.decorators.http import require_POST",
        1,
    )


old = '''@login_required
def toggle_wishlist(request, product_id):
'''

new = '''@login_required
@require_POST
def toggle_wishlist(request, product_id):
'''

if old in text:

    text = text.replace(
        old,
        new,
        1,
    )

elif (
    "@require_POST\n"
    "def toggle_wishlist"
    not in text
):

    raise SystemExit(
        "ERROR: Could not safely patch toggle_wishlist."
    )


wishlist_views.write_text(
    text,
    encoding="utf-8",
)

print(
    "[PATCHED] Wishlist toggle is POST-only."
)


# ============================================================
# 3. COUPON REMOVE -> POST ONLY
# ============================================================

orders_views = (
    ROOT
    / "orders"
    / "views.py"
)

text = orders_views.read_text(
    encoding="utf-8-sig"
)


if (
    "from django.views.decorators.http import require_POST"
    not in text
):

    marker = (
        "from django.contrib.auth.decorators "
        "import login_required"
    )

    if marker not in text:
        raise SystemExit(
            "ERROR: orders/views.py import marker not found."
        )

    text = text.replace(
        marker,
        marker
        + "\n"
        + "from django.views.decorators.http import require_POST",
        1,
    )


old = '''@login_required
def remove_coupon(request):
'''

new = '''@login_required
@require_POST
def remove_coupon(request):
'''

if old in text:

    text = text.replace(
        old,
        new,
        1,
    )

elif (
    "@require_POST\n"
    "def remove_coupon"
    not in text
):

    raise SystemExit(
        "ERROR: Could not safely patch remove_coupon."
    )


orders_views.write_text(
    text,
    encoding="utf-8",
)

print(
    "[PATCHED] Coupon removal is POST-only."
)


# ============================================================
# 4. CART JAVASCRIPT -> CSRF POST
# ============================================================

cart_js = (
    ROOT
    / "static"
    / "js"
    / "cart.js"
)

text = cart_js.read_text(
    encoding="utf-8-sig"
)


old = '''        fetch(`/cart/${action}/${itemId}/`, {
            headers: { "X-Requested-With": "XMLHttpRequest" }
        })
'''

new = '''        fetch(`/cart/${action}/${itemId}/`, {
            method: "POST",
            headers: {
                "X-Requested-With": "XMLHttpRequest",
                "X-CSRFToken": csrfToken()
            }
        })
'''

if old in text:

    text = text.replace(
        old,
        new,
        1,
    )


old = '''        fetch(`/cart/remove/${itemId}/`, {
            headers: { "X-Requested-With": "XMLHttpRequest" }
        })
'''

new = '''        fetch(`/cart/remove/${itemId}/`, {
            method: "POST",
            headers: {
                "X-Requested-With": "XMLHttpRequest",
                "X-CSRFToken": csrfToken()
            }
        })
'''

if old in text:

    text = text.replace(
        old,
        new,
        1,
    )


old = '''        const variantQuery = variantSelect && variantSelect.value ? `?variant=${encodeURIComponent(variantSelect.value)}` : "";

        fetch(`/cart/add/${productId}/${variantQuery}`, {
            headers: { "X-Requested-With": "XMLHttpRequest" }
        })
'''

new = '''        const body = new URLSearchParams();

        if (variantSelect && variantSelect.value) {
            body.append(
                "variant",
                variantSelect.value
            );
        }

        fetch(`/cart/add/${productId}/`, {
            method: "POST",
            headers: {
                "X-Requested-With": "XMLHttpRequest",
                "X-CSRFToken": csrfToken(),
                "Content-Type":
                    "application/x-www-form-urlencoded"
            },
            body: body.toString()
        })
'''

if old in text:

    text = text.replace(
        old,
        new,
        1,
    )


# Verify unsafe mutation fetches are gone.
unsafe_cart_patterns = [
    '''fetch(`/cart/${action}/${itemId}/`, {
            headers:''',
    '''fetch(`/cart/remove/${itemId}/`, {
            headers:''',
    '''fetch(`/cart/add/${productId}/${variantQuery}`,''',
]

for pattern in unsafe_cart_patterns:

    if pattern in text:

        raise SystemExit(
            "ERROR: Unsafe cart GET fetch remains."
        )


cart_js.write_text(
    text,
    encoding="utf-8",
)

print(
    "[PATCHED] Cart JavaScript uses CSRF-protected POST."
)


# ============================================================
# 5. WISHLIST JAVASCRIPT -> CSRF POST
# ============================================================

wishlist_js = (
    ROOT
    / "static"
    / "js"
    / "wishlist.js"
)

text = wishlist_js.read_text(
    encoding="utf-8-sig"
)


# Add local CSRF helper if absent.
if "function wishlistCsrfToken()" not in text:

    text = '''function wishlistCsrfToken() {

    const match = document.cookie.match(
        /csrftoken=([^;]+)/
    );

    return match
        ? match[1]
        : "";
}

''' + text


old = '''        fetch(`/wishlist/toggle/${productId}/`, {

            headers: {
                "X-Requested-With": "XMLHttpRequest"
            }

        })
'''

new = '''        fetch(`/wishlist/toggle/${productId}/`, {

            method: "POST",

            headers: {
                "X-Requested-With": "XMLHttpRequest",
                "X-CSRFToken": wishlistCsrfToken()
            }

        })
'''

if old in text:

    text = text.replace(
        old,
        new,
        1,
    )

elif (
    'method: "POST"'
    not in text
):

    raise SystemExit(
        "ERROR: Could not safely patch wishlist JavaScript."
    )


wishlist_js.write_text(
    text,
    encoding="utf-8",
)

print(
    "[PATCHED] Wishlist JavaScript uses CSRF-protected POST."
)


# ============================================================
# 6. SECURITY REGRESSION TESTS
# ============================================================

test_file = (
    ROOT
    / "core"
    / "test_state_changing_get.py"
)


test_file.write_text(
r'''from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from accounts.models import (
    Address,
    CustomUser,
)
from cart.models import Cart
from categories.models import Category
from products.models import Product
from wishlist.models import Wishlist


class StateChangingGetSecurityTests(TestCase):

    def setUp(self):

        self.user = (
            CustomUser.objects.create_user(
                username="state-get-user",
                email="state-get@example.com",
                password="StrongPass123!",
            )
        )

        self.client.force_login(
            self.user
        )

        self.category = (
            Category.objects.create(
                name="Security category",
                slug="security-category",
            )
        )

        self.product = (
            Product.objects.create(
                category=self.category,
                name="Security product",
                slug="security-product",
                description="Security test product",
                sku="SEC-GET-001",
                price=Decimal("100.00"),
                stock=10,
            )
        )


    # ========================================================
    # CART
    # ========================================================

    def test_get_cannot_add_item_to_cart(self):

        response = self.client.get(
            reverse(
                "add_to_cart",
                args=[self.product.id],
            )
        )

        self.assertEqual(
            response.status_code,
            405,
        )

        cart = Cart.objects.filter(
            user=self.user
        ).first()

        if cart is not None:

            self.assertFalse(
                cart.items.exists()
            )


    def test_cart_quantity_and_remove_gets_do_not_mutate(self):

        self.client.post(
            reverse(
                "add_to_cart",
                args=[self.product.id],
            )
        )

        cart = Cart.objects.get(
            user=self.user
        )

        item = cart.items.get()

        original_quantity = (
            item.quantity
        )


        response = self.client.get(
            reverse(
                "increase_quantity",
                args=[item.id],
            )
        )

        self.assertEqual(
            response.status_code,
            405,
        )

        item.refresh_from_db()

        self.assertEqual(
            item.quantity,
            original_quantity,
        )


        response = self.client.get(
            reverse(
                "decrease_quantity",
                args=[item.id],
            )
        )

        self.assertEqual(
            response.status_code,
            405,
        )

        item.refresh_from_db()

        self.assertEqual(
            item.quantity,
            original_quantity,
        )


        response = self.client.get(
            reverse(
                "remove_from_cart",
                args=[item.id],
            )
        )

        self.assertEqual(
            response.status_code,
            405,
        )

        self.assertTrue(
            cart.items.filter(
                id=item.id
            ).exists()
        )


    def test_cart_post_still_mutates(self):

        response = self.client.post(
            reverse(
                "add_to_cart",
                args=[self.product.id],
            )
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        cart = Cart.objects.get(
            user=self.user
        )

        self.assertEqual(
            cart.items.count(),
            1,
        )


    # ========================================================
    # WISHLIST
    # ========================================================

    def test_get_cannot_toggle_wishlist(self):

        response = self.client.get(
            reverse(
                "toggle_wishlist",
                args=[self.product.id],
            )
        )

        self.assertEqual(
            response.status_code,
            405,
        )

        self.assertFalse(
            Wishlist.objects.filter(
                user=self.user,
                product=self.product,
            ).exists()
        )


    def test_wishlist_post_still_works(self):

        response = self.client.post(
            reverse(
                "toggle_wishlist",
                args=[self.product.id],
            )
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertTrue(
            Wishlist.objects.filter(
                user=self.user,
                product=self.product,
            ).exists()
        )


    # ========================================================
    # COUPON SESSION
    # ========================================================

    def test_get_cannot_remove_coupon_from_session(self):

        session = self.client.session

        session[
            "coupon_code"
        ] = "TESTCOUPON"

        session.save()


        response = self.client.get(
            reverse(
                "remove_coupon"
            )
        )

        self.assertEqual(
            response.status_code,
            405,
        )


        session = self.client.session

        self.assertEqual(
            session.get(
                "coupon_code"
            ),
            "TESTCOUPON",
        )


    def test_coupon_removal_post_still_works(self):

        session = self.client.session

        session[
            "coupon_code"
        ] = "TESTCOUPON"

        session.save()


        response = self.client.post(
            reverse(
                "remove_coupon"
            )
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertNotIn(
            "coupon_code",
            self.client.session,
        )


    # ========================================================
    # ADDRESS ACTIONS ALREADY HARDENED
    # ========================================================

    def test_address_delete_get_is_still_blocked(self):

        address = Address.objects.create(
            user=self.user,
            full_name="Security User",
            phone="0712345678",
            county="Nairobi",
            city="Nairobi",
            estate="Test Estate",
            house_number="1",
        )

        response = self.client.get(
            reverse(
                "delete_address",
                args=[address.id],
            )
        )

        self.assertEqual(
            response.status_code,
            405,
        )

        self.assertTrue(
            Address.objects.filter(
                id=address.id
            ).exists()
        )


    def test_address_default_get_is_still_blocked(self):

        first = Address.objects.create(
            user=self.user,
            full_name="First",
            phone="0711111111",
            county="Nairobi",
            city="Nairobi",
            estate="Estate",
            house_number="1",
            is_default=True,
        )

        second = Address.objects.create(
            user=self.user,
            full_name="Second",
            phone="0722222222",
            county="Nairobi",
            city="Nairobi",
            estate="Estate",
            house_number="2",
            is_default=False,
        )


        response = self.client.get(
            reverse(
                "set_default_address",
                args=[second.id],
            )
        )

        self.assertEqual(
            response.status_code,
            405,
        )


        first.refresh_from_db()
        second.refresh_from_db()

        self.assertTrue(
            first.is_default
        )

        self.assertFalse(
            second.is_default
        )


    # ========================================================
    # LOGOUT ALREADY HARDENED BY DJANGO LOGOUTVIEW
    # ========================================================

    def test_logout_get_does_not_log_user_out(self):

        response = self.client.get(
            reverse(
                "logout"
            )
        )

        self.assertEqual(
            response.status_code,
            405,
        )

        self.assertIn(
            "_auth_user_id",
            self.client.session,
        )
''',
    encoding="utf-8",
)

print(
    "[CREATED] core/test_state_changing_get.py"
)


# ============================================================
# 7. IGNORE LOCAL BACKUPS
# ============================================================

gitignore = ROOT / ".gitignore"

if gitignore.exists():

    text = gitignore.read_text(
        encoding="utf-8-sig"
    )

    entry = ".state_change_backups/"

    if entry not in text:

        if not text.endswith("\n"):
            text += "\n"

        text += (
            "\n# State-change security backups\n"
            + entry
            + "\n"
        )

        gitignore.write_text(
            text,
            encoding="utf-8",
        )


# ============================================================
# 8. VALIDATION
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
        "core.test_state_changing_get",
        "-v",
        "2",
    ],

    [
        sys.executable,
        "manage.py",
        "test",
        "cart",
        "wishlist",
        "orders",
        "accounts",
        "-v",
        "1",
    ],
]


for command in commands:

    print()
    print("=" * 72)
    print(
        ">",
        " ".join(command)
    )
    print("=" * 72)

    result = subprocess.run(
        command,
        cwd=ROOT,
    )

    if result.returncode != 0:

        print()
        print("=" * 72)
        print(
            "STATE-CHANGE SECURITY VALIDATION FAILED"
        )
        print("=" * 72)

        print()
        print(
            "Do not switch the endpoints back to GET."
        )

        print(
            "Send the exact failing output."
        )

        print()
        print(
            "Backup directory:"
        )

        print(
            backup_dir
        )

        raise SystemExit(
            result.returncode
        )


print()
print("=" * 72)
print(
    "STATE-CHANGING GET SECURITY PASSED"
)
print("=" * 72)

print()
print(
    "POST-only mutations:"
)

print(
    "  - cart add"
)

print(
    "  - cart increase"
)

print(
    "  - cart decrease"
)

print(
    "  - cart remove"
)

print(
    "  - wishlist toggle"
)

print(
    "  - coupon removal"
)

print(
    "  - address delete"
)

print(
    "  - address set-default"
)

print(
    "  - logout"
)

print()
print(
    "GET requests can no longer change those states."
)

print()
print(
    "Backup directory:"
)

print(
    backup_dir
)

print()
print(
    "FINAL PROJECT GATE:"
)

print(
    "python manage.py test -v 1"
)

