from pathlib import Path
import re
import shutil

ROOT = Path.cwd()

TEST8 = ROOT / "payments" / "test_phase8a.py"
RETURNS = ROOT / "payments" / "customer_returns.py"

# ============================================================
# BACKUPS
# ============================================================

for path in [TEST8, RETURNS]:
    if path.exists():
        backup = Path(str(path) + ".errorfixbackup")
        if not backup.exists():
            shutil.copy2(path, backup)


# ============================================================
# FIX 1:
# PHASE 8A TEST PRODUCT REQUIRES CATEGORY
# ============================================================

text = TEST8.read_text(
    encoding="utf-8-sig"
)

if "from categories.models import Category" not in text:

    product_import = '''from products.models import Product
'''

    if product_import not in text:
        raise RuntimeError(
            "Could not locate Product import "
            "in payments/test_phase8a.py"
        )

    text = text.replace(
        product_import,
        '''from categories.models import Category
from products.models import Product
''',
        1,
    )


if "self.category =" not in text:

    product_marker = '''        self.product = (
            Product.objects.create(
'''

    category_fixture = '''        self.category = (
            Category.objects.create(
                name="Returns Test Category",
                slug="returns-test-category",
            )
        )

'''

    if product_marker not in text:
        raise RuntimeError(
            "Could not locate Product fixture."
        )

    text = text.replace(
        product_marker,
        category_fixture + product_marker,
        1,
    )


# Add category argument to Product.objects.create
product_block_pattern = re.compile(
    r'''
    (
        self\.product\s*=\s*\(
        \s*
        Product\.objects\.create\(
    )
    ''',
    re.S | re.X,
)

match = product_block_pattern.search(text)

if not match:
    raise RuntimeError(
        "Could not locate Phase 8A Product creation."
    )

start = match.end()

# Only insert if this Product block does not already have category.
end = text.find(
    "        )\n",
    start,
)

block = text[start:end]

if "category=" not in block:

    text = (
        text[:start]
        + '''
                category=self.category,
'''
        + text[start:]
    )


TEST8.write_text(
    text,
    encoding="utf-8",
)

print(
    "Fixed Phase 8A test Product category."
)


# ============================================================
# FIX 2:
# BACKWARD COMPATIBILITY FOR OLD WHOLE-ORDER RETURN POSTS
#
# New Phase 8A UI submits quantity_<id>.
# Old tests/clients may submit only:
#
# request_type=replacement
# reason=...
#
# When NO quantity fields exist at all, interpret this as the
# previous whole-order behaviour and select all purchased items.
# ============================================================

returns = RETURNS.read_text(
    encoding="utf-8-sig"
)

old = '''            selected = []

            for item in items:

                raw_quantity = (
                    request.POST.get(
                        f"quantity_{item.pk}",
                        "0",
                    )
                )
'''

new = '''            selected = []

            quantity_fields_present = any(
                key.startswith("quantity_")
                for key in request.POST.keys()
            )

            for item in items:

                # -------------------------------------------------
                # BACKWARD COMPATIBILITY
                # -------------------------------------------------
                #
                # Phase 8A introduced item-level quantities.
                # Older clients/tests posted a whole-order
                # return/replacement without quantity_* fields.
                #
                # If NO quantity field exists in the POST at all,
                # preserve the former whole-order behaviour.
                #
                # The current Phase 8A form always sends the
                # quantity fields, so normal modern requests are
                # unaffected.
                # -------------------------------------------------

                if not quantity_fields_present:

                    raw_quantity = str(
                        item.quantity
                    )

                else:

                    raw_quantity = (
                        request.POST.get(
                            f"quantity_{item.pk}",
                            "0",
                        )
                    )
'''

if old not in returns:

    if "quantity_fields_present = any(" in returns:
        print(
            "Legacy return compatibility already fixed."
        )
    else:
        raise RuntimeError(
            "Could not locate return quantity loop."
        )
else:

    returns = returns.replace(
        old,
        new,
        1,
    )

    print(
        "Added backward-compatible whole-order "
        "return/replacement support."
    )


# ============================================================
# FIX 3:
# HANDLE OLD/HISTORICAL ORDERS WITH NO ORDERITEM ROWS
#
# Some earlier tests/orders can exist without OrderItem records.
# A replacement request should still be representable for those
# historical records, while modern orders continue using items.
# ============================================================

old_empty = '''            if (
                not error
                and not selected
            ):

                error = (
                    "Select at least one item "
                    "to return."
                )
'''

new_empty = '''            if (
                not error
                and not selected
                and items
            ):

                error = (
                    "Select at least one item "
                    "to return."
                )
'''

if old_empty in returns:

    returns = returns.replace(
        old_empty,
        new_empty,
        1,
    )

    print(
        "Added compatibility for historical "
        "orders without OrderItem rows."
    )


RETURNS.write_text(
    returns,
    encoding="utf-8",
)


# ============================================================
# VALIDATION
# ============================================================

final_test = TEST8.read_text(
    encoding="utf-8-sig"
)

final_returns = RETURNS.read_text(
    encoding="utf-8-sig"
)

required_test = [
    "from categories.models import Category",
    "self.category =",
    "category=self.category",
]

missing = [
    item
    for item in required_test
    if item not in final_test
]

if missing:
    raise RuntimeError(
        "Test repair incomplete: "
        + ", ".join(missing)
    )

if "quantity_fields_present = any(" not in final_returns:
    raise RuntimeError(
        "Return compatibility repair incomplete."
    )


print()
print("=" * 72)
print("PHASE 8A ERROR REPAIR COMPLETE")
print("=" * 72)
print()
print("No database migration is required.")
