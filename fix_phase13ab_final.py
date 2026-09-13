from pathlib import Path
import shutil

path = Path("orders/test_phase13ab.py")

if not path.exists():
    raise RuntimeError("orders/test_phase13ab.py not found.")

backup = Path(
    "orders/test_phase13ab.py.phase13ab-final-fixture-backup"
)

if not backup.exists():
    shutil.copy2(path, backup)

text = path.read_text(
    encoding="utf-8-sig"
)

text = text.replace(
    'method="door_delivery",',
    'method="local_door",',
)

text = text.replace(
    'method="local_delivery",',
    'method="local_door",',
)

path.write_text(
    text,
    encoding="utf-8",
)

print("=" * 72)
print("PHASE 13A/B FIXED")
print("=" * 72)
print('Delivery test method is now: "local_door"')
print("No production delivery model was changed.")
