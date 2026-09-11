from pathlib import Path
import shutil

path = Path("payments/returns_admin_views.py")

backup = Path(
    "payments/returns_admin_views.py.partial-refund-backup"
)

if not backup.exists():
    shutil.copy2(path, backup)

text = path.read_text(
    encoding="utf-8-sig"
)


old = '''    if (
        processed_total
        >= refund.order.total_amount
    ):

        refund.order.payment_status = (
            "refunded"
        )

        refund.order.save(
            update_fields=[
                "payment_status",
                "updated_at",
            ]
        )
'''


new = '''    if (
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


    refund.order.save(
        update_fields=[
            "payment_status",
            "updated_at",
        ]
    )
'''


if old not in text:

    if '"partially_refunded"' in text:
        print(
            "Partial refund logic already exists."
        )
        raise SystemExit(0)

    raise RuntimeError(
        "Expected refund status block "
        "was not found. File left unchanged."
    )


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
print("=" * 68)
print("PARTIAL REFUND STATUS REPAIRED")
print("=" * 68)
print()
print("processed_total < order total")
print("        -> partially_refunded")
print()
print("processed_total >= order total")
print("        -> refunded")
