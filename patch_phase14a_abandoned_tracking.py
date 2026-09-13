from pathlib import Path
import shutil


ROOT = Path.cwd()


FILES = [
    ROOT / "cart" / "models.py",
    ROOT / "cart" / "services" / "cart_service.py",
    ROOT / "orders" / "views.py",
    ROOT / "config" / "settings.py",
]


for path in FILES:

    if not path.exists():
        raise RuntimeError(
            f"Missing required file: {path}"
        )


for path in FILES:

    backup = Path(
        str(path) + ".phase14abackup"
    )

    if not backup.exists():
        shutil.copy2(
            path,
            backup,
        )


# ============================================================
# CART MODEL
# ============================================================

path = ROOT / "cart" / "models.py"

text = path.read_text(
    encoding="utf-8-sig"
)


old = '''    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
'''

new = '''    created_at = models.DateTimeField(auto_now_add=True)

    updated_at = models.DateTimeField(
        auto_now=True
    )

    # --------------------------------------------------------
    # ABANDONED CART LIFECYCLE
    # --------------------------------------------------------

    last_activity_at = models.DateTimeField(
        default=timezone.now,
        db_index=True,
    )

    checkout_started_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    converted_at = models.DateTimeField(
        null=True,
        blank=True,
        db_index=True,
    )
'''


if old not in text:

    if "last_activity_at" not in text:

        raise RuntimeError(
            "Could not locate Cart timestamps."
        )

else:

    text = text.replace(
        old,
        new,
        1,
    )


if "from django.utils import timezone" not in text:

    text = text.replace(
        "from django.db import models\n",
        (
            "from django.db import models\n"
            "from django.utils import timezone\n"
        ),
        1,
    )


path.write_text(
    text,
    encoding="utf-8",
)


# ============================================================
# CART ACTIVITY SERVICE
# ============================================================

activity_service = (
    ROOT
    / "cart"
    / "services"
    / "cart_activity_service.py"
)


activity_service.write_text(
r'''
from django.utils import timezone


class CartActivityService:

    @staticmethod
    def mark_activity(
        cart,
        *,
        reset_checkout=True,
        reset_conversion=False,
    ):

        now = timezone.now()

        fields = [
            "last_activity_at",
            "updated_at",
        ]

        cart.last_activity_at = now


        if reset_checkout:

            cart.checkout_started_at = None

            fields.append(
                "checkout_started_at"
            )


        if reset_conversion:

            cart.converted_at = None

            fields.append(
                "converted_at"
            )


        cart.save(
            update_fields=fields
        )


        return cart


    @staticmethod
    def mark_checkout_started(
        cart,
    ):

        now = timezone.now()

        cart.last_activity_at = now

        cart.checkout_started_at = now


        cart.save(
            update_fields=[
                "last_activity_at",
                "checkout_started_at",
                "updated_at",
            ]
        )


        return cart


    @staticmethod
    def mark_converted(
        cart,
    ):

        now = timezone.now()

        cart.last_activity_at = now

        cart.converted_at = now


        cart.save(
            update_fields=[
                "last_activity_at",
                "converted_at",
                "updated_at",
            ]
        )


        return cart
'''.strip() + "\n",
encoding="utf-8",
)


# ============================================================
# ABANDONED CART SELECTOR
# ============================================================

selector = (
    ROOT
    / "cart"
    / "selectors"
    / "abandoned_cart_selector.py"
)


selector.write_text(
r'''
from datetime import timedelta

from django.conf import settings
from django.utils import timezone

from cart.models import Cart


class AbandonedCartSelector:

    @staticmethod
    def cutoff():

        hours = getattr(
            settings,
            "CART_ABANDONED_AFTER_HOURS",
            24,
        )


        return (
            timezone.now()
            - timedelta(
                hours=hours
            )
        )


    @classmethod
    def abandoned(
        cls,
        *,
        cutoff=None,
    ):

        if cutoff is None:

            cutoff = cls.cutoff()


        return (
            Cart.objects
            .filter(
                converted_at__isnull=True,
                last_activity_at__lte=cutoff,
                items__isnull=False,
            )
            .select_related(
                "user"
            )
            .distinct()
            .order_by(
                "last_activity_at"
            )
        )
'''.strip() + "\n",
encoding="utf-8",
)


# ============================================================
# CART SERVICE
# ============================================================

path = (
    ROOT
    / "cart"
    / "services"
    / "cart_service.py"
)

text = path.read_text(
    encoding="utf-8-sig"
)


if "CartActivityService" not in text:

    text = text.replace(
        '''from cart.selectors.cart_selector import CartSelector
''',
        '''from cart.selectors.cart_selector import CartSelector
from cart.services.cart_activity_service import CartActivityService
''',
        1,
    )


# ------------------------------------------------------------
# ADD
# ------------------------------------------------------------

old = '''        if not created:
            available_stock = variant.available_stock if variant else product.available_stock
            if item.quantity < available_stock:
                item.quantity += 1
                item.save()

        return cart
'''

new = '''        if not created:
            available_stock = variant.available_stock if variant else product.available_stock
            if item.quantity < available_stock:
                item.quantity += 1
                item.save()


        CartActivityService.mark_activity(
            cart,
            reset_checkout=True,
            reset_conversion=True,
        )


        return cart
'''

if old in text:

    text = text.replace(
        old,
        new,
        1,
    )


# ------------------------------------------------------------
# INCREASE
# ------------------------------------------------------------

old = '''        if item and item.quantity < available_stock:
            item.quantity += 1
            item.save()

        return cart
'''

new = '''        if item and item.quantity < available_stock:
            item.quantity += 1
            item.save()


        CartActivityService.mark_activity(
            cart,
            reset_checkout=True,
            reset_conversion=True,
        )


        return cart
'''

if old in text:

    text = text.replace(
        old,
        new,
        1,
    )


# ------------------------------------------------------------
# DECREASE
# ------------------------------------------------------------

old = '''        if item:
            if item.quantity > 1:
                item.quantity -= 1
                item.save()
            else:
                item.delete()

        return cart
'''

new = '''        if item:
            if item.quantity > 1:
                item.quantity -= 1
                item.save()
            else:
                item.delete()


        CartActivityService.mark_activity(
            cart,
            reset_checkout=True,
            reset_conversion=True,
        )


        return cart
'''

if old in text:

    text = text.replace(
        old,
        new,
        1,
    )


# ------------------------------------------------------------
# REMOVE
# ------------------------------------------------------------

old = '''        cart.items.filter(id=item_id).delete()

        return cart
'''

new = '''        cart.items.filter(
            id=item_id
        ).delete()


        CartActivityService.mark_activity(
            cart,
            reset_checkout=True,
            reset_conversion=True,
        )


        return cart
'''

if old in text:

    text = text.replace(
        old,
        new,
        1,
    )


# ------------------------------------------------------------
# MERGE
# ------------------------------------------------------------

old = '''        session_cart.delete()
'''

new = '''        CartActivityService.mark_activity(
            user_cart,
            reset_checkout=True,
            reset_conversion=True,
        )


        session_cart.delete()
'''

if (
    old in text
    and
    "CartActivityService.mark_activity(\n            user_cart" not in text
):

    text = text.replace(
        old,
        new,
        1,
    )


path.write_text(
    text,
    encoding="utf-8",
)


# ============================================================
# CHECKOUT TRACKING
# ============================================================

path = ROOT / "orders" / "views.py"

text = path.read_text(
    encoding="utf-8-sig"
)


if "CartActivityService" not in text:

    text = text.replace(
        '''from cart.selectors.cart_selector import CartSelector
''',
        '''from cart.selectors.cart_selector import CartSelector
from cart.services.cart_activity_service import CartActivityService
''',
        1,
    )


# Mark checkout only after confirming cart has products.
old = '''    if not items.exists():
        return redirect("cart")


    # ---------------------------------------------------------
    # STORE-WIDE CHECKOUT CONTROLS
'''

new = '''    if not items.exists():
        return redirect("cart")


    # A genuine checkout visit counts as cart activity.
    # Mini-cart/background requests do not.
    CartActivityService.mark_checkout_started(
        cart
    )


    # ---------------------------------------------------------
    # STORE-WIDE CHECKOUT CONTROLS
'''

if old in text:

    text = text.replace(
        old,
        new,
        1,
    )


# Successful checkout converts the cart before its items
# are cleared.
old = '''                cart.items.all().delete()

            if order.guest_checkout:
'''

new = '''                CartActivityService.mark_converted(
                    cart
                )

                cart.items.all().delete()

            if order.guest_checkout:
'''

if old in text:

    text = text.replace(
        old,
        new,
        1,
    )

elif "CartActivityService.mark_converted" not in text:

    raise RuntimeError(
        "Could not locate successful cart clearing."
    )


path.write_text(
    text,
    encoding="utf-8",
)


# ============================================================
# SETTINGS
# ============================================================

path = ROOT / "config" / "settings.py"

text = path.read_text(
    encoding="utf-8-sig"
)


if "CART_ABANDONED_AFTER_HOURS" not in text:

    text += '''

# ============================================================
# ABANDONED CARTS
# ============================================================

# A cart is considered abandoned only when it still contains
# products, has not produced an order, and has had no genuine
# cart/checkout activity for this many hours.
CART_ABANDONED_AFTER_HOURS = int(
    os.environ.get(
        "CART_ABANDONED_AFTER_HOURS",
        "24",
    )
)
'''


path.write_text(
    text,
    encoding="utf-8",
)


# ============================================================
# MIGRATION
# ============================================================

migration = (
    ROOT
    / "cart"
    / "migrations"
    / "0004_cart_abandonment_tracking.py"
)


if not migration.exists():

    migration.write_text(
r'''
from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        (
            "cart",
            "0003_cartitem_variant",
        ),
    ]


    operations = [

        migrations.AddField(
            model_name="cart",
            name="last_activity_at",
            field=models.DateTimeField(
                db_index=True,
                default=django.utils.timezone.now,
            ),
        ),

        migrations.AddField(
            model_name="cart",
            name="checkout_started_at",
            field=models.DateTimeField(
                blank=True,
                null=True,
            ),
        ),

        migrations.AddField(
            model_name="cart",
            name="converted_at",
            field=models.DateTimeField(
                blank=True,
                db_index=True,
                null=True,
            ),
        ),
    ]
'''.strip() + "\n",
encoding="utf-8",
    )


# ============================================================
# TESTS
# ============================================================

test_file = (
    ROOT
    / "cart"
    / "test_phase14a.py"
)


test_file.write_text(
r'''
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from categories.models import Category
from products.models import Product

from cart.models import (
    Cart,
    CartItem,
)

from cart.selectors.abandoned_cart_selector import (
    AbandonedCartSelector,
)

from cart.services.cart_activity_service import (
    CartActivityService,
)


User = get_user_model()


class Phase14AAbandonedCartTests(
    TestCase
):

    def setUp(self):

        self.user = (
            User.objects.create_user(
                username="phase14-user",
                email="phase14@example.com",
                password="pass12345",
            )
        )


        category = Category.objects.create(
            name="Phase 14",
            slug="phase-14",
        )


        self.product = Product.objects.create(
            category=category,
            name="Phase 14 Product",
            slug="phase-14-product",
            description="Test",
            sku="PHASE14-001",
            price=Decimal("100.00"),
            stock=20,
        )


    def _cart_with_item(
        self,
        *,
        user=None,
    ):

        cart = Cart.objects.create(
            user=user,
        )


        CartItem.objects.create(
            cart=cart,
            product=self.product,
            quantity=1,
        )


        return cart


    def test_cart_has_activity_timestamp(
        self,
    ):

        cart = Cart.objects.create(
            user=self.user
        )


        self.assertIsNotNone(
            cart.last_activity_at
        )


    def test_add_to_cart_updates_activity(
        self,
    ):

        self.client.force_login(
            self.user
        )


        cart = Cart.objects.create(
            user=self.user
        )


        old_time = (
            timezone.now()
            - timedelta(days=3)
        )


        Cart.objects.filter(
            pk=cart.pk
        ).update(
            last_activity_at=old_time
        )


        self.client.post(
            reverse(
                "add_to_cart",
                args=[self.product.pk],
            )
        )


        cart.refresh_from_db()


        self.assertGreater(
            cart.last_activity_at,
            old_time,
        )


    def test_cart_change_resets_checkout_marker(
        self,
    ):

        self.client.force_login(
            self.user
        )


        cart = self._cart_with_item(
            user=self.user
        )


        Cart.objects.filter(
            pk=cart.pk
        ).update(
            checkout_started_at=
                timezone.now(),
        )


        item = cart.items.get()


        self.client.post(
            reverse(
                "increase_quantity",
                args=[item.pk],
            )
        )


        cart.refresh_from_db()


        self.assertIsNone(
            cart.checkout_started_at
        )


    def test_new_cart_activity_resets_old_conversion(
        self,
    ):

        self.client.force_login(
            self.user
        )


        cart = Cart.objects.create(
            user=self.user,
            converted_at=timezone.now(),
        )


        self.client.post(
            reverse(
                "add_to_cart",
                args=[self.product.pk],
            )
        )


        cart.refresh_from_db()


        self.assertIsNone(
            cart.converted_at
        )


    def test_mark_checkout_started(
        self,
    ):

        cart = self._cart_with_item(
            user=self.user
        )


        CartActivityService.mark_checkout_started(
            cart
        )


        cart.refresh_from_db()


        self.assertIsNotNone(
            cart.checkout_started_at
        )


        self.assertIsNotNone(
            cart.last_activity_at
        )


    def test_mark_converted(
        self,
    ):

        cart = self._cart_with_item(
            user=self.user
        )


        CartActivityService.mark_converted(
            cart
        )


        cart.refresh_from_db()


        self.assertIsNotNone(
            cart.converted_at
        )


    def test_old_nonempty_unconverted_cart_is_abandoned(
        self,
    ):

        cart = self._cart_with_item(
            user=self.user
        )


        old_time = (
            timezone.now()
            - timedelta(hours=25)
        )


        Cart.objects.filter(
            pk=cart.pk
        ).update(
            last_activity_at=old_time
        )


        abandoned = (
            AbandonedCartSelector
            .abandoned()
        )


        self.assertIn(
            cart,
            abandoned,
        )


    def test_recent_cart_is_not_abandoned(
        self,
    ):

        cart = self._cart_with_item(
            user=self.user
        )


        abandoned = (
            AbandonedCartSelector
            .abandoned()
        )


        self.assertNotIn(
            cart,
            abandoned,
        )


    def test_converted_cart_is_not_abandoned(
        self,
    ):

        cart = self._cart_with_item(
            user=self.user
        )


        Cart.objects.filter(
            pk=cart.pk
        ).update(
            last_activity_at=(
                timezone.now()
                - timedelta(days=2)
            ),
            converted_at=timezone.now(),
        )


        abandoned = (
            AbandonedCartSelector
            .abandoned()
        )


        self.assertNotIn(
            cart,
            abandoned,
        )


    def test_empty_cart_is_not_abandoned(
        self,
    ):

        cart = Cart.objects.create(
            user=self.user
        )


        Cart.objects.filter(
            pk=cart.pk
        ).update(
            last_activity_at=(
                timezone.now()
                - timedelta(days=2)
            )
        )


        abandoned = (
            AbandonedCartSelector
            .abandoned()
        )


        self.assertNotIn(
            cart,
            abandoned,
        )


    def test_guest_cart_can_be_abandoned(
        self,
    ):

        cart = Cart.objects.create(
            session_key="phase14-guest-session"
        )


        CartItem.objects.create(
            cart=cart,
            product=self.product,
            quantity=1,
        )


        Cart.objects.filter(
            pk=cart.pk
        ).update(
            last_activity_at=(
                timezone.now()
                - timedelta(days=2)
            )
        )


        abandoned = (
            AbandonedCartSelector
            .abandoned()
        )


        self.assertIn(
            cart,
            abandoned,
        )
'''.strip() + "\n",
encoding="utf-8",
)


print()
print("=" * 72)
print("PHASE 14A INSTALLED")
print("=" * 72)
print()
print("Added:")
print("  cart.last_activity_at")
print("  cart.checkout_started_at")
print("  cart.converted_at")
print("  explicit cart activity tracking")
print("  checkout-start tracking")
print("  successful conversion tracking")
print("  abandoned-cart selector")
print("  24-hour configurable abandonment threshold")
print("  guest + registered cart support")
print()
print("No recovery email/SMS is sent in Phase 14A.")
print()
print("Migration:")
print("  cart.0004_cart_abandonment_tracking")
