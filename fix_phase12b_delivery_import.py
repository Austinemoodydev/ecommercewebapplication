from pathlib import Path
import shutil


path = Path("delivery/views.py")

if not path.exists():
    raise RuntimeError(
        "delivery/views.py not found."
    )


backup = Path(
    "delivery/views.py.phase12b-import-backup"
)

if not backup.exists():
    shutil.copy2(
        path,
        backup,
    )


text = path.read_text(
    encoding="utf-8-sig"
)


IMPORT = '''from orders.pricing import (
    total_from_order_snapshot,
)
'''


if "total_from_order_snapshot" not in text:

    # Insert safely before the first function/class definition.
    candidates = []

    for marker in [
        "\ndef ",
        "\n@",
        "\nclass ",
    ]:

        position = text.find(
            marker
        )

        if position != -1:
            candidates.append(
                position
            )


    if not candidates:

        raise RuntimeError(
            "Could not find safe import insertion point."
        )


    position = min(
        candidates
    )


    text = (
        text[:position]
        + "\n"
        + IMPORT
        + text[position:]
    )


path.write_text(
    text,
    encoding="utf-8",
)


print(
    "orders.pricing import added safely "
    "to delivery/views.py."
)
