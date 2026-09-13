from pathlib import Path
from datetime import datetime
import shutil
import subprocess
import sys

ROOT = Path.cwd()

if not (ROOT / "manage.py").exists():
    raise SystemExit(
        "ERROR: Run this command from the Django project root containing manage.py."
    )

FILE = ROOT / "templates/dashboard/admin/dashboard.html"

if not FILE.exists():
    raise SystemExit(
        f"ERROR: File not found: {FILE}"
    )


# ============================================================
# BACKUP
# ============================================================

stamp = datetime.now().strftime("%Y%m%d-%H%M%S")

backup_dir = (
    ROOT
    / ".dashboard_fix_backups"
    / stamp
)

backup_dir.mkdir(
    parents=True,
    exist_ok=True,
)

backup_file = (
    backup_dir
    / "dashboard.html"
)

shutil.copy2(
    FILE,
    backup_file,
)

print("=" * 72)
print("ADMIN DASHBOARD ORDER LINK FIX")
print("=" * 72)
print()
print("Backup:")
print(backup_file)
print()


# ============================================================
# FIX MALFORMED ORDER LINK
# ============================================================

text = FILE.read_text(
    encoding="utf-8-sig"
)


broken = '''                        <td>
                            

    href="{% url 'admin_order_detail' order.order_number %}"
    class="text-decoration-none fw-bold"
>
    {{ order.order_number }}
</a>
                            <small class="d-block text-muted">
                                {{ order.created_at|date:"d M Y H:i" }}
                            </small>
                        </td>'''


fixed = '''                        <td>

                            <a
                                href="{% url 'admin_order_detail' order.order_number %}"
                                class="text-decoration-none fw-bold"
                            >
                                {{ order.order_number }}
                            </a>

                            <small class="d-block text-muted">
                                {{ order.created_at|date:"d M Y H:i" }}
                            </small>

                        </td>'''


if broken in text:

    text = text.replace(
        broken,
        fixed,
        1,
    )

    print(
        "[FIXED] Missing <a> tag on Recent Orders."
    )

elif '''<a
                                href="{% url 'admin_order_detail' order.order_number %}"''' in text:

    print(
        "[OK] Order link is already correctly wrapped in <a>."
    )

else:

    # More flexible repair in case whitespace differs slightly.

    broken_fragment = '''href="{% url 'admin_order_detail' order.order_number %}"
    class="text-decoration-none fw-bold"
>'''

    if broken_fragment in text:

        text = text.replace(
            broken_fragment,
            '''<a
                                href="{% url 'admin_order_detail' order.order_number %}"
                                class="text-decoration-none fw-bold"
                            >''',
            1,
        )

        print(
            "[FIXED] Missing <a> opening tag repaired."
        )

    else:

        raise RuntimeError(
            "Could not safely locate the malformed Recent Orders link."
        )


FILE.write_text(
    text,
    encoding="utf-8",
)


# ============================================================
# VERIFY THE BAD TEXT CANNOT REMAIN
# ============================================================

updated = FILE.read_text(
    encoding="utf-8"
)

if '''
    href="{% url 'admin_order_detail' order.order_number %}"
    class="text-decoration-none fw-bold"
>''' in updated and '''<a
                                href="{% url 'admin_order_detail' order.order_number %}"''' not in updated:

    raise RuntimeError(
        "The malformed href is still present."
    )


print()
print("[PASS] Dashboard template repaired.")


# ============================================================
# DJANGO VALIDATION
# ============================================================

commands = [

    [
        sys.executable,
        "manage.py",
        "check",
    ],

    [
        sys.executable,
        "manage.py",
        "makemigrations",
        "--check",
        "--dry-run",
    ],

    [
        sys.executable,
        "manage.py",
        "test",
        "dashboard",
        "-v",
        "1",
    ],

]


print()
print("=" * 72)
print("RUNNING VALIDATION")
print("=" * 72)


for command in commands:

    print()
    print(
        ">",
        " ".join(command),
    )

    result = subprocess.run(
        command,
        cwd=ROOT,
    )

    if result.returncode != 0:

        print()
        print("=" * 72)
        print("VALIDATION FAILED")
        print("=" * 72)

        print()
        print("Your original template is backed up here:")
        print(backup_file)

        raise SystemExit(
            result.returncode
        )


print()
print("=" * 72)
print("ADMIN DASHBOARD FIX PASSED")
print("=" * 72)

print()
print("✓ Raw href text removed")
print("✓ Order number remains clickable")
print("✓ Order date remains underneath")
print("✓ Customer details unchanged")
print("✓ Status unchanged")
print("✓ Payment status unchanged")
print("✓ Order totals unchanged")
print("✓ No Django model changes")
print("✓ Dashboard tests passed")

print()
print("Backup:")
print(backup_file)

print()
print(
    "Refresh /dashboard/admin/ with Ctrl+F5."
)
