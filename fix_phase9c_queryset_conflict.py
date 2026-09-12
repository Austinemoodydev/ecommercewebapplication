from pathlib import Path
import shutil

path = Path(
    "dashboard/report_extensions.py"
)

backup = Path(
    "dashboard/report_extensions.py.phase9c-query-fix-backup"
)

if not backup.exists():
    shutil.copy2(
        path,
        backup,
    )


text = path.read_text(
    encoding="utf-8-sig"
)


old = '''    for order in (
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
'''


new = '''    for order in (
        paid_orders
        .order_by(
            "created_at"
        )
    ):
'''


if old not in text:

    if '''paid_orders
        .order_by(
            "created_at"
        )''' in text:

        print(
            "Phase 9C queryset repair "
            "already applied."
        )

        raise SystemExit(0)


    raise RuntimeError(
        "Could not locate the monthly "
        "paid_orders .only() block."
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
print("PHASE 9C QUERYSET REPAIR COMPLETE")
print("=" * 68)
print()
print(
    "Removed conflicting .only() from "
    "monthly sales aggregation."
)
