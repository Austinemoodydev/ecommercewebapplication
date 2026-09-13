from pathlib import Path
import shutil


TEST_FILE = Path(
    "orders/test_phase13ab.py"
)


if not TEST_FILE.exists():

    raise RuntimeError(
        "orders/test_phase13ab.py not found."
    )


backup = Path(
    "orders/test_phase13ab.py."
    "phase13ab-fixture-backup"
)


if not backup.exists():

    shutil.copy2(
        TEST_FILE,
        backup,
    )


text = TEST_FILE.read_text(
    encoding="utf-8-sig"
)


old = '''                method="local_delivery",
'''

new = '''                method="door_delivery",
'''


if old in text:

    text = text.replace(
        old,
        new,
        1,
    )

elif new in text:

    print(
        "Delivery method fixture already repaired."
    )

else:

    raise RuntimeError(
        "Could not locate Phase 13AB "
        "DeliveryZone method fixture."
    )


TEST_FILE.write_text(
    text,
    encoding="utf-8",
)


print()
print("=" * 72)
print("PHASE 13A/B TEST FIXTURE REPAIRED")
print("=" * 72)
print()
print(
    'Changed method="local_delivery" '
    'to method="door_delivery".'
)
print()
print(
    "Production delivery code was NOT changed."
)
