from pathlib import Path
import subprocess
import sys

ROOT = Path.cwd()
TEST_FILE = ROOT / "accounts/tests.py"

if not TEST_FILE.exists():
    raise SystemExit("ERROR: accounts/tests.py not found.")

text = TEST_FILE.read_text(encoding="utf-8-sig")

old = '''self.assertEqual(settings.LOGIN_REDIRECT_URL, "/")'''
new = '''self.assertEqual(settings.LOGIN_REDIRECT_URL, "/shop/")'''

if old in text:
    text = text.replace(old, new, 1)
    TEST_FILE.write_text(text, encoding="utf-8")
    print("[FIXED] LoginRedirectTests now expects /shop/")
elif new in text:
    print("[OK] Test already expects /shop/")
else:
    raise SystemExit(
        "ERROR: Could not locate the old LOGIN_REDIRECT_URL assertion."
    )

commands = [
    [sys.executable, "manage.py", "check"],
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
]

for command in commands:
    print()
    print(">", " ".join(command))

    result = subprocess.run(command, cwd=ROOT)

    if result.returncode != 0:
        raise SystemExit(result.returncode)

print()
print("=" * 70)
print("AUTH REDIRECT TESTS PASSED")
print("=" * 70)
print("Customer login -> /shop/")
print("Staff login    -> /dashboard/admin/")
print("Superadmin     -> /admin/")
