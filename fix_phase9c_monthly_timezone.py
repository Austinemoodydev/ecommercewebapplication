from pathlib import Path
import shutil

path = Path(
    "dashboard/report_extensions.py"
)

backup = Path(
    "dashboard/report_extensions.py.phase9c-month-fix-backup"
)

if not backup.exists():
    shutil.copy2(
        path,
        backup,
    )

text = path.read_text(
    encoding="utf-8-sig"
)


# ============================================================
# 1. ADD TIMEZONE IMPORT
# ============================================================

if "from django.utils import timezone" not in text:

    marker = "from django.db.models.functions import ("

    pos = text.find(marker)

    if pos == -1:
        raise RuntimeError(
            "Could not locate Django imports."
        )

    text = (
        text[:pos]
        + "from django.utils import timezone\n\n"
        + text[pos:]
    )


# ============================================================
# 2. REMOVE TRUNCMONTH IMPORT
# ============================================================

text = text.replace(
    '''from django.db.models.functions import (
    TruncMonth,
)

''',
    "",
)


# ============================================================
# 3. REPLACE MYSQL-DEPENDENT MONTHLY AGGREGATION
# ============================================================

old = '''    monthly_sales = list(
        paid_orders
        .annotate(
            month=TruncMonth(
                "created_at"
            )
        )
        .values(
            "month"
        )
        .annotate(
            order_count=Count(
                "id"
            ),
            revenue=Sum(
                "total_amount"
            ),
        )
        .order_by(
            "month"
        )
    )


    for row in monthly_sales:

        row[
            "revenue"
        ] = _money(
            row[
                "revenue"
            ]
        )
'''


new = '''    # ====================================================
    # MONTHLY SALES
    #
    # Do NOT use TruncMonth here.
    #
    # MySQL installations without populated timezone tables
    # can fail when Django asks the database to perform
    # timezone-aware datetime truncation.
    #
    # We already have the correct filtered QuerySet, so group
    # the relatively small report result in Python using
    # Django's active timezone.
    # ====================================================

    monthly_map = {}


    for order in (
        paid_orders
        .only(
            "id",
            "created_at",
            "total_amount",
        )
        .order_by(
            "created_at"
        )
    ):

        created_at = order.created_at


        if timezone.is_aware(
            created_at
        ):

            created_at = (
                timezone.localtime(
                    created_at
                )
            )


        month_key = (
            created_at.year,
            created_at.month,
        )


        if month_key not in monthly_map:

            month_start = (
                created_at.replace(
                    day=1,
                    hour=0,
                    minute=0,
                    second=0,
                    microsecond=0,
                )
            )


            monthly_map[
                month_key
            ] = {
                "month": month_start,
                "order_count": 0,
                "revenue": ZERO,
            }


        monthly_map[
            month_key
        ][
            "order_count"
        ] += 1


        monthly_map[
            month_key
        ][
            "revenue"
        ] += _money(
            order.total_amount
        )


    monthly_sales = [
        monthly_map[key]
        for key
        in sorted(
            monthly_map
        )
    ]
'''


if old not in text:

    if "monthly_map = {}" in text:

        print(
            "Monthly sales repair already applied."
        )

    else:

        raise RuntimeError(
            "Could not locate existing "
            "Phase 9C monthly_sales block."
        )

else:

    text = text.replace(
        old,
        new,
        1,
    )


path.write_text(
    text,
    encoding="utf-8",
)


print()
print("=" * 72)
print("PHASE 9C MONTHLY SALES TIMEZONE FIX COMPLETE")
print("=" * 72)
print()
print(
    "Monthly aggregation now uses Django/Python "
    "instead of MySQL TruncMonth."
)
