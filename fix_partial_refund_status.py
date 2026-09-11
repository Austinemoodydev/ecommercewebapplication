from pathlib import Path
import shutil
import re

ROOT = Path.cwd()

PATH = (
    ROOT
    / "payments"
    / "returns_admin_views.py"
)

backup = Path(
    str(PATH)
    + ".partialrefundfixbackup"
)

if not backup.exists():
    shutil.copy2(
        PATH,
        backup,
    )


text = PATH.read_text(
    encoding="utf-8-sig"
)


# ============================================================
# FIND REFUND PROCESS FUNCTION
# ============================================================

match = re.search(
    r'''
    (
        def\s+admin_refund_process
        \s*\(
        .*?
    )
    (?=
        \ndef\s+
        |
        \n@staff_member_required
        |
        \Z
    )
    ''',
    text,
    flags=re.S | re.X,
)

if not match:

    raise RuntimeError(
        "Could not locate "
        "admin_refund_process()."
    )


block = match.group(1)


# ============================================================
# REMOVE PREMATURE PAYMENT STATUS CALCULATION
# ============================================================

pattern = re.compile(
    r'''
    \n
    \s*processed_total\s*=\s*\(
        \s*processed_refund_total\(
            \s*refund\.order
        \s*\)
    \s*\)

    \s*if\s*\(
        \s*processed_total
        \s*>=
        \s*refund\.order\.total_amount
    \s*\):

        \s*refund\.order\.payment_status
        \s*=\s*\(
            \s*"refunded"
        \s*\)

    \s*elif\s+
        processed_total
        \s*>\s*0
    \s*:

        \s*refund\.order\.payment_status
        \s*=\s*\(
            \s*"partially_refunded"
        \s*\)

    \s*refund\.order\.save\(
        \s*update_fields=\[
            \s*"payment_status",
            \s*"updated_at",
        \s*\]
    \s*\)
    ''',
    flags=re.S | re.X,
)


block, removed = pattern.subn(
    "\n",
    block,
    count=1,
)


if removed != 1:

    raise RuntimeError(
        "Could not locate the existing "
        "partial-refund status block."
    )


# ============================================================
# FIND REFUND SAVE
# ============================================================

save_pattern = re.compile(
    r'''
    (
        refund\.save\(
            .*?
        \)
    )
    ''',
    flags=re.S | re.X,
)

save_match = save_pattern.search(
    block
)

if not save_match:

    raise RuntimeError(
        "Could not locate refund.save() "
        "inside admin_refund_process()."
    )


status_update = r'''

    # ========================================================
    # REFRESH PAYMENT STATUS AFTER CURRENT REFUND IS PROCESSED
    # ========================================================

    processed_total = (
        processed_refund_total(
            refund.order
        )
    )

    if (
        processed_total
        >= refund.order.total_amount
    ):

        refund.order.payment_status = (
            "refunded"
        )

    elif processed_total > 0:

        refund.order.payment_status = (
            "partially_refunded"
        )

    else:

        refund.order.payment_status = (
            "paid"
        )


    refund.order.save(
        update_fields=[
            "payment_status",
            "updated_at",
        ]
    )
'''


insert_at = save_match.end()

block = (
    block[:insert_at]
    + status_update
    + block[insert_at:]
)


# ============================================================
# WRITE FUNCTION BACK
# ============================================================

text = (
    text[:match.start()]
    + block
    + text[match.end():]
)

PATH.write_text(
    text,
    encoding="utf-8",
)


print()
print("=" * 70)
print("PARTIAL REFUND STATUS FIX APPLIED")
print("=" * 70)
print()
print(
    "Refund is now counted only after "
    "it has been saved as processed."
)
