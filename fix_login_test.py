from pathlib import Path
import subprocess
import sys

ROOT = Path.cwd()
TEST_FILE = ROOT / "accounts/tests.py"

if not TEST_FILE.exists():
    raise SystemExit("ERROR: accounts/tests.py not found.")

text = TEST_FILE.read_text(encoding="utf-8-sig")

old = 'self.assertRedirects(response, reverse("home"))'
new = 'self.assertRedirects(response, reverse("shop"))'

count = text.count(old)

if count == 0:
    raise SystemExit(
        'ERROR: Could not find self.assertRedirects(response, reverse("home"))'
    )

if count > 1:
    print(f"NOTICE: Found {count} matching lines; replacing only the one after LOGIN_REDIRECT_URL.")

    marker = 'self.assertEqual(settings.LOGIN_REDIRECT_URL, "/shop/")'
    pos = text.find(marker)

    if pos == -1:
        raise SystemExit("ERROR: LOGIN_REDIRECT_URL test marker not found.")

    after = text.find(old, pos)

    if after == -1:
        raise SystemExit("ERROR: Redirect assertion not found after marker.")

    text = (
        text[:after]
        + new
        + text[after + len(old):]
    )

else:
    text = text.replace(old, new, 1)

TEST_FILE.write_text(
    text,
    encoding="utf-8",
)

print("[FIXED] Customer login test now expects /shop/")

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
]

for command in commands:
    print()
    print(">", " ".join(command))

    result = subprocess.run(
        command,
        cwd=ROOT,
    )

    if result.returncode != 0:
        raise SystemExit(result.returncode)

print()
print("AUTH LOGIN REDIRECT TESTS PASSED")
print("Customer -> /shop/")
print("Staff    -> /dashboard/admin/")
print("Admin    -> /admin/")
