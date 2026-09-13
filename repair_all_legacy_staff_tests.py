from pathlib import Path
import re
import subprocess
import sys

ROOT = Path.cwd()

if not (ROOT / "manage.py").exists():
    raise SystemExit("Run this from the folder containing manage.py.")

SKIP = {
    "venv", ".venv", ".git",
    ".staff_management_backups",
    ".ui_cleanup_backups",
    ".auth_ux_backups",
}

patched = []


def should_skip(path):
    return any(part in SKIP for part in path.parts)


for path in ROOT.rglob("test*.py"):

    if should_skip(path):
        continue

    text = path.read_text(encoding="utf-8-sig")

    # Only files containing a legacy self.staff fixture.
    if "self.staff" not in text or "is_staff=True" not in text:
        continue

    original = text

    # ---------------------------------------------------------
    # Add imports
    # ---------------------------------------------------------

    if "from django.contrib.auth.models import Group" not in text:

        text = (
            "from django.contrib.auth.models import Group\n"
            + text
        )

    if "from accounts.store_roles import STORE_OWNER" not in text:

        text = (
            "from accounts.store_roles import STORE_OWNER\n"
            + text
        )


    # ---------------------------------------------------------
    # Locate self.staff assignment blocks
    # ---------------------------------------------------------

    lines = text.splitlines()

    new_lines = []

    i = 0
    file_changed = False

    while i < len(lines):

        line = lines[i]

        new_lines.append(line)

        # Detect start of:
        # self.staff = ...
        if re.search(r"\bself\.staff\s*=", line):

            block_lines = [line]

            balance = line.count("(") - line.count(")")

            j = i

            while balance > 0 and j + 1 < len(lines):

                j += 1

                next_line = lines[j]

                block_lines.append(next_line)

                balance += (
                    next_line.count("(")
                    - next_line.count(")")
                )

                new_lines.append(next_line)

            block = "\n".join(block_lines)

            # Only modify staff accounts explicitly created
            # with is_staff=True.
            if "is_staff=True" in block:

                # Check nearby original text to avoid duplicates.
                nearby = "\n".join(
                    lines[
                        j + 1:
                        min(j + 12, len(lines))
                    ]
                )

                if (
                    "self.staff.groups.add" not in nearby
                    or "STORE_OWNER" not in nearby
                ):

                    indent = re.match(
                        r"^(\s*)",
                        line,
                    ).group(1)

                    new_lines.extend([
                        "",
                        indent + "store_owner_group, _ = Group.objects.get_or_create(",
                        indent + "    name=STORE_OWNER,",
                        indent + ")",
                        "",
                        indent + "self.staff.groups.add(",
                        indent + "    store_owner_group",
                        indent + ")",
                    ])

                    file_changed = True

            i = j + 1
            continue

        i += 1


    if file_changed:

        path.write_text(
            "\n".join(new_lines) + "\n",
            encoding="utf-8",
        )

        patched.append(
            str(path.relative_to(ROOT))
        )


print()
print("=" * 72)
print("LEGACY FULL-ACCESS STAFF FIXTURES")
print("=" * 72)

if patched:

    for filename in patched:
        print("[PATCHED]", filename)

else:
    print("[INFO] No remaining legacy self.staff fixtures required patching.")


# -------------------------------------------------------------
# Verify that known problem files now contain role assignment
# -------------------------------------------------------------

important_files = [
    "core/test_phase12a.py",
    "crm/tests.py",
    "dashboard/test_layout_isolation.py",
    "dashboard/test_phase9a.py",
    "dashboard/test_phase9b.py",
    "dashboard/test_phase9c.py",
    "dashboard/test_phase10.py",
    "dashboard/test_phase12d.py",
    "dashboard/test_phase14b.py",
    "dashboard/tests.py",
    "delivery/tests.py",
    "delivery/test_phase7c.py",
    "payments/test_admin_payments.py",
    "payments/test_phase8a.py",
    "payments/test_phase8b.py",
]

print()
print("=" * 72)
print("VERIFYING KNOWN LEGACY TEST FILES")
print("=" * 72)

problems = []

for rel in important_files:

    path = ROOT / rel

    if not path.exists():
        continue

    data = path.read_text(encoding="utf-8-sig")

    if (
        "self.staff" in data
        and "is_staff=True" in data
        and "self.staff.groups.add" not in data
    ):
        problems.append(rel)
        print("[MISSING ROLE]", rel)

    else:
        print("[OK]", rel)


if problems:

    print()
    raise SystemExit(
        "Some legacy staff fixtures still have no role: "
        + ", ".join(problems)
    )


# -------------------------------------------------------------
# Validation
# -------------------------------------------------------------

commands = [
    [
        sys.executable,
        "manage.py",
        "check",
    ],

    [
        sys.executable,
        "manage.py",
        "test",
        "core.test_phase12a",
        "crm.tests",
        "dashboard.test_layout_isolation",
        "dashboard.test_phase9a",
        "dashboard.test_phase9b",
        "dashboard.test_phase9c",
        "dashboard.test_phase10",
        "dashboard.test_phase12d",
        "dashboard.test_phase14b",
        "dashboard.tests",
        "delivery.tests",
        "delivery.test_phase7c",
        "payments.test_admin_payments",
        "payments.test_phase8a",
        "payments.test_phase8b",
        "-v",
        "1",
    ],
]


for command in commands:

    print()
    print("=" * 72)
    print(">", " ".join(command))
    print("=" * 72)

    result = subprocess.run(
        command,
        cwd=ROOT,
    )

    if result.returncode != 0:

        print()
        print("=" * 72)
        print("TARGETED VALIDATION FAILED")
        print("=" * 72)

        print(
            "Stop here. The remaining output is now useful "
            "for identifying a genuine permission-map issue."
        )

        raise SystemExit(result.returncode)


print()
print("=" * 72)
print("TARGETED LEGACY STAFF TESTS PASSED")
print("=" * 72)

print()
print("Now run:")
print("python manage.py test -v 1")

