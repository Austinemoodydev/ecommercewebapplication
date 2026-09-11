from pathlib import Path
import shutil

ROOT = Path.cwd()

FILES = {
    "dashboard": ROOT / "dashboard" / "views.py",
    "payments": ROOT / "payments" / "views.py",
    "returns": ROOT / "payments" / "customer_returns.py",
    "delivery": ROOT / "delivery" / "services.py",
}

for path in FILES.values():

    if not path.exists():
        raise RuntimeError(
            f"Missing required file: {path}"
        )

    backup = Path(
        str(path) + ".phase8b1backup"
    )

    if not backup.exists():
        shutil.copy2(path, backup)


# ============================================================
# 1. FIX ANALYTICS TIMEZONE WARNINGS
# ============================================================

path = FILES["dashboard"]

text = path.read_text(
    encoding="utf-8-sig"
)


old = '''def _paid_orders(start_date, end_date):
    return Order.objects.filter(
        payment_status="paid",
        created_at__gte=start_date,
        created_at__lt=end_date + timedelta(days=1),
    )
'''


new = '''def _report_datetime_range(
    start_date,
    end_date,
):
    """
    Convert report dates to timezone-aware datetime boundaries.
    """

    tz = timezone.get_current_timezone()

    start_dt = timezone.make_aware(
        timezone.datetime.combine(
            start_date,
            timezone.datetime.min.time(),
        ),
        tz,
    )

    end_dt = timezone.make_aware(
        timezone.datetime.combine(
            end_date + timedelta(days=1),
            timezone.datetime.min.time(),
        ),
        tz,
    )

    return start_dt, end_dt


def _paid_orders(start_date, end_date):

    start_dt, end_dt = (
        _report_datetime_range(
            start_date,
            end_date,
        )
    )

    return Order.objects.filter(
        payment_status__in=[
            "paid",
            "partially_refunded",
            "refunded",
        ],
        created_at__gte=start_dt,
        created_at__lt=end_dt,
    )
'''


if old not in text:

    if "def _report_datetime_range(" not in text:

        raise RuntimeError(
            "Could not locate _paid_orders() "
            "in dashboard/views.py"
        )

else:

    text = text.replace(
        old,
        new,
        1,
    )


# ------------------------------------------------------------
# admin_analytics() also used date objects directly
# ------------------------------------------------------------

old = '''    report_end = end_date + timedelta(days=1)
    daily_orders = Order.objects.filter(created_at__gte=start_date, created_at__lt=report_end)
'''


new = '''    start_dt, report_end = (
        _report_datetime_range(
            start_date,
            end_date,
        )
    )

    daily_orders = Order.objects.filter(
        created_at__gte=start_dt,
        created_at__lt=report_end,
    )
'''


if old in text:

    text = text.replace(
        old,
        new,
        1,
    )


path.write_text(
    text,
    encoding="utf-8",
)

print(
    "Analytics timezone boundaries repaired."
)


# ============================================================
# 2. M-PESA PAYMENT SAFETY
# ============================================================

path = FILES["payments"]

text = path.read_text(
    encoding="utf-8-sig"
)


# Add a single shared definition to this module.
if "SETTLED_PAYMENT_STATUSES =" not in text:

    marker = "from "

    # Insert just before first view/decorator rather than depending
    # on the exact import list.
    positions = [
        x
        for x in [
            text.find("@login_required"),
            text.find("@csrf_exempt"),
            text.find("def initiate"),
        ]
        if x >= 0
    ]

    if not positions:
        raise RuntimeError(
            "Could not locate start of payments views."
        )

    pos = min(positions)

    helper = '''

# ============================================================
# PAYMENT STATE HELPERS
# ============================================================

SETTLED_PAYMENT_STATUSES = {
    "paid",
    "partially_refunded",
    "refunded",
}


def _payment_is_settled(order):
    return (
        order.payment_status
        in SETTLED_PAYMENT_STATUSES
    )


'''

    text = (
        text[:pos]
        + helper
        + text[pos:]
    )


replacements = [

    (
        'if order.payment_status == "paid":',
        'if _payment_is_settled(order):',
    ),

    (
        'if order.payment_status != "paid":',
        'if not _payment_is_settled(order):',
    ),

]


for old, new in replacements:

    text = text.replace(
        old,
        new,
    )


path.write_text(
    text,
    encoding="utf-8",
)

print(
    "M-PESA settled-payment guards repaired."
)


# ============================================================
# 3. CUSTOMER RETURNS / REFUNDS
# ============================================================

path = FILES["returns"]

text = path.read_text(
    encoding="utf-8-sig"
)


if "SETTLED_RETURN_PAYMENT_STATUSES =" not in text:

    positions = [
        x
        for x in [
            text.find("@login_required"),
            text.find("def request_refund"),
        ]
        if x >= 0
    ]

    if not positions:

        raise RuntimeError(
            "Could not locate customer return views."
        )

    pos = min(positions)

    helper = '''

SETTLED_RETURN_PAYMENT_STATUSES = {
    "paid",
    "partially_refunded",
    "refunded",
}


'''

    text = (
        text[:pos]
        + helper
        + text[pos:]
    )


text = text.replace(
    'order.payment_status != "paid"',
    (
        "order.payment_status "
        "not in SETTLED_RETURN_PAYMENT_STATUSES"
    ),
)


path.write_text(
    text,
    encoding="utf-8",
)

print(
    "Returns/refunds payment guards repaired."
)


# ============================================================
# 4. DELIVERY PAYMENT SAFETY
# ============================================================

path = FILES["delivery"]

text = path.read_text(
    encoding="utf-8-sig"
)


if "SETTLED_DELIVERY_PAYMENT_STATUSES =" not in text:

    positions = [
        x
        for x in [
            text.find("def "),
        ]
        if x >= 0
    ]

    if not positions:

        raise RuntimeError(
            "Could not locate delivery services."
        )

    pos = min(positions)

    helper = '''

SETTLED_DELIVERY_PAYMENT_STATUSES = {
    "paid",
    "partially_refunded",
    "refunded",
}


'''

    text = (
        text[:pos]
        + helper
        + text[pos:]
    )


text = text.replace(
    'order.payment_status != "paid"',
    (
        "order.payment_status "
        "not in SETTLED_DELIVERY_PAYMENT_STATUSES"
    ),
)


path.write_text(
    text,
    encoding="utf-8",
)

print(
    "Delivery settled-payment guard repaired."
)


# ============================================================
# 5. ADMIN ORDER STATUS PAYMENT SAFETY
# ============================================================

path = FILES["dashboard"]

text = path.read_text(
    encoding="utf-8-sig"
)


if "ORDER_SETTLED_PAYMENT_STATUSES =" not in text:

    marker = "def _allowed_order_transitions(order):"

    if marker not in text:
        raise RuntimeError(
            "Could not locate admin order transitions."
        )

    text = text.replace(
        marker,
        '''ORDER_SETTLED_PAYMENT_STATUSES = {
    "paid",
    "partially_refunded",
    "refunded",
}


def _allowed_order_transitions(order):''',
        1,
    )


text = text.replace(
    'if order.payment_status != "paid":',
    (
        "if order.payment_status "
        "not in ORDER_SETTLED_PAYMENT_STATUSES:"
    ),
)


path.write_text(
    text,
    encoding="utf-8",
)


print(
    "Admin order payment guards repaired."
)


# ============================================================
# FINISH
# ============================================================

print()
print("=" * 72)
print("PHASE 8B.1 PAYMENT + TIMEZONE SAFETY COMPLETE")
print("=" * 72)
print()
print("Fixed:")
print("  - analytics timezone-aware date boundaries")
print("  - duplicate M-PESA protection")
print("  - partially-refunded order protection")
print("  - refund / return eligibility")
print("  - delivery payment checks")
print("  - admin order payment checks")
