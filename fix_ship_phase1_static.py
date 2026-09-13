from pathlib import Path
import shutil

path = Path("config/settings.py")

if not path.exists():
    raise RuntimeError("config/settings.py not found.")

backup = Path("config/settings.py.shipphase1backup")

if not backup.exists():
    shutil.copy2(path, backup)

text = path.read_text(encoding="utf-8-sig")

if "STATIC_ROOT =" in text:
    print("STATIC_ROOT already exists.")
else:
    marker = 'STATIC_URL = "static/"'

    if marker not in text:
        marker = "STATIC_URL = 'static/'"

    if marker not in text:
        raise RuntimeError(
            "Could not locate STATIC_URL safely. "
            "No changes were made."
        )

    replacement = marker + """

# Directory populated by `python manage.py collectstatic`.
# Source static files remain in the normal app/static directories.
STATIC_ROOT = BASE_DIR / "staticfiles"
"""

    text = text.replace(
        marker,
        replacement,
        1,
    )

    path.write_text(
        text,
        encoding="utf-8",
    )

    print("STATIC_ROOT configured successfully.")

print()
print("STATIC_ROOT = BASE_DIR / 'staticfiles'")
