from pathlib import Path
import subprocess
import sys

ROOT = Path.cwd()

TEST_FILE = ROOT / "accounts/test_auth_separation.py"

if not TEST_FILE.exists():
    raise SystemExit(
        "ERROR: accounts/test_auth_separation.py not found."
    )

text = TEST_FILE.read_text(
    encoding="utf-8-sig"
)


# ------------------------------------------------------------
# 1. ADD GROUP IMPORT
# ------------------------------------------------------------

old_import = '''from django.contrib.auth import get_user_model
'''

new_import = '''from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
'''

if "from django.contrib.auth.models import Group" not in text:

    if old_import not in text:
        raise SystemExit(
            "ERROR: Could not locate auth import."
        )

    text = text.replace(
        old_import,
        new_import,
        1,
    )


# ------------------------------------------------------------
# 2. ASSIGN STORE MANAGER ROLE TO LEGACY TEST STAFF
# ------------------------------------------------------------

old_staff_block = '''        self.staff = User.objects.create_user(
            username="staff-auth-test",
            email="staff-auth@example.com",
            password="StrongPass123!",
            is_active=True,
            is_staff=True,
            role="admin",
        )

        self.superuser = (
'''

new_staff_block = '''        self.staff = User.objects.create_user(
            username="staff-auth-test",
            email="staff-auth@example.com",
            password="StrongPass123!",
            is_active=True,
            is_staff=True,
            role="admin",
        )

        store_manager_group, _ = (
            Group.objects.get_or_create(
                name="Store Manager"
            )
        )

        self.staff.groups.add(
            store_manager_group
        )

        self.superuser = (
'''

if old_staff_block in text:

    text = text.replace(
        old_staff_block,
        new_staff_block,
        1,
    )

elif 'name="Store Manager"' in text:

    print(
        "[OK] Legacy staff test already has Store Manager role."
    )

else:

    raise SystemExit(
        "ERROR: Could not safely locate legacy staff setup block."
    )


TEST_FILE.write_text(
    text,
    encoding="utf-8",
)

print(
    "[FIXED] test_auth_separation staff now has Store Manager role."
)


# ------------------------------------------------------------
# 3. RUN ROLE SETUP
# ------------------------------------------------------------

commands = [

    [
        sys.executable,
        "manage.py",
        "setup_store_roles",
    ],

    [
        sys.executable,
        "manage.py",
        "test",
        (
            "accounts.test_auth_separation."
            "AuthenticationSeparationTests."
            "test_staff_login_accepts_staff"
        ),
        "-v",
        "2",
    ],

    [
        sys.executable,
        "manage.py",
        "test",
        "accounts.test_auth_separation",
        "-v",
        "2",
    ],

    [
        sys.executable,
        "manage.py",
        "test",
        "accounts.test_staff_management",
        "-v",
        "2",
    ],

    [
        sys.executable,
        "manage.py",
        "test",
        "accounts",
        "-v",
        "1",
    ],
]


for command in commands:

    print()
    print("=" * 70)
    print(
        ">",
        " ".join(command),
    )
    print("=" * 70)

    result = subprocess.run(
        command,
        cwd=ROOT,
    )

    if result.returncode != 0:

        print()
        print(
            "VALIDATION FAILED"
        )

        raise SystemExit(
            result.returncode
        )


print()
print("=" * 70)
print("STAFF AUTH TESTS PASSED")
print("=" * 70)

print()
print(
    "Staff login now requires BOTH:"
)

print(
    "  1. is_staff=True"
)

print(
    "  2. Authorized store role"
)

print()
print(
    "Old is_staff-only behavior is no longer accepted."
)

