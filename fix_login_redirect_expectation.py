from pathlib import Path
import subprocess
import sys

ROOT = Path.cwd()
TEST_FILE = ROOT / "accounts/tests.py"

if not TEST_FILE.exists():
    raise SystemExit("ERROR: accounts/tests.py not found.")

text = TEST_FILE.read_text(encoding="utf-8-sig")

old_block = '''        self.assertEqual(settings.LOGIN_REDIRECT_URL, "/shop/")
        self.assertRedirects(response, reverse("home"))'''

new_block = '''        self.assertEqual(settings.LOGIN_REDIRECT_URL, "/shop/")
        self.assertRedirects(response, reverse("shop"))'''

if old_block in text:

    text = text.replace(
        old_block,
        new_block,
        1,
    )

    TEST_FILE.write_text(
        text,
        encoding="utf-8",
    )

    print("[FIXED] LoginRedirectTests now expects /shop/ correctly.")

elif 'self.assertRedirects(response, reverse("shop"))' in text:

    print("[OK] Test already expects the shop page.")

else:

    raise SystemExit(
        "ERROR: Could not safely locate the old redirect assertion."
    )


commands = [
    [
        sys.executable,
        "manage.py",
        "test",
        "accounts.tests.LoginRedirectTests",
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
        "accounts",
        "-v",
        "1",
    ],

    [
        sys.executable,
        "manage.py",
        "test",
        "-v",
        "1",
    ],
]


for command in commands:

    print()
    print("=" * 70)
    print(">", " ".join(command))
    print("=" * 70)

    result = subprocess.run(
        command,
        cwd=ROOT,
    )

    if result.returncode != 0:
        raise SystemExit(result.returncode)


print()
print("=" * 70)
print("AUTH REDIRECT TESTS PASSED")
print("=" * 70)

print()
print("Customer password login -> /shop/")
print("Customer Google login   -> /shop/")
print("Store staff login        -> /dashboard/admin/")
print("Superadmin login         -> /admin/")
