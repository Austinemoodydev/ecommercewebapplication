from pathlib import Path
from datetime import datetime
import shutil
import subprocess
import sys

ROOT = Path.cwd()

if not (ROOT / "manage.py").exists():
    raise SystemExit(
        "ERROR: Run this inside the Django project root containing manage.py."
    )

FILES = [
    ROOT / "templates/includes/navbar.html",
    ROOT / "templates/dashboard/admin/base.html",
    ROOT / "templates/accounts/dashboard/dashboard.html",
]

for file in FILES:
    if not file.exists():
        raise SystemExit(f"Missing required file: {file}")

stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
BACKUP = ROOT / ".logout_fix_backups" / stamp
BACKUP.mkdir(parents=True, exist_ok=True)

print("=" * 72)
print("SECURE LOGOUT FIX")
print("=" * 72)


def backup(path):
    target = BACKUP / path.relative_to(ROOT)
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(path, target)


# ============================================================
# 1. MAIN CUSTOMER NAVBAR
# ============================================================

path = ROOT / "templates/includes/navbar.html"
backup(path)

text = path.read_text(encoding="utf-8-sig")

old = '''<li><a class="dropdown-item text-danger" href="{% url 'logout' %}">Log out</a></li>'''

new = '''<li>
<form method="post"
      action="{% url 'logout' %}"
      class="m-0">
    {% csrf_token %}
    <button type="submit"
            class="dropdown-item text-danger">
        <i class="bi bi-box-arrow-right me-2"></i>
        Log out
    </button>
</form>
</li>'''

if old in text:
    text = text.replace(old, new, 1)
    print("[FIXED] Customer navbar logout")
elif 'action="{% url \'logout\' %}"' in text:
    print("[OK] Customer navbar already uses POST logout")
else:
    raise RuntimeError(
        "Could not safely locate customer navbar logout link."
    )

path.write_text(text, encoding="utf-8")


# ============================================================
# 2. ADMIN DASHBOARD LOGOUT
# ============================================================

path = ROOT / "templates/dashboard/admin/base.html"
backup(path)

text = path.read_text(encoding="utf-8-sig")

old = '''                            <a
                                class="dropdown-item"
                                href="/accounts/logout/"
                            >

                                <i class="bi bi-box-arrow-right me-2"></i>

                                Logout

                            </a>'''

new = '''                            <form
                                method="post"
                                action="{% url 'logout' %}"
                                class="m-0"
                            >
                                {% csrf_token %}

                                <button
                                    type="submit"
                                    class="dropdown-item"
                                >
                                    <i class="bi bi-box-arrow-right me-2"></i>

                                    Logout
                                </button>

                            </form>'''

if old in text:
    text = text.replace(old, new, 1)
    print("[FIXED] Admin dashboard logout")
elif (
    'action="{% url \'logout\' %}"' in text
    and "bi-box-arrow-right" in text
):
    print("[OK] Admin dashboard already uses POST logout")
else:
    raise RuntimeError(
        "Could not safely locate admin dashboard logout link."
    )

path.write_text(text, encoding="utf-8")


# ============================================================
# 3. CUSTOMER DASHBOARD LOGOUT
# ============================================================

path = ROOT / "templates/accounts/dashboard/dashboard.html"
backup(path)

text = path.read_text(encoding="utf-8-sig")

old = '''<a href="{% url 'logout' %}">

Logout

</a>'''

new = '''<form method="post"
      action="{% url 'logout' %}"
      class="m-0">
    {% csrf_token %}

    <button type="submit"
            class="btn btn-link p-0 text-decoration-none">
        Logout
    </button>
</form>'''

if old in text:
    text = text.replace(old, new, 1)
    print("[FIXED] Customer dashboard logout")
elif 'action="{% url \'logout\' %}"' in text:
    print("[OK] Customer dashboard already uses POST logout")
else:
    raise RuntimeError(
        "Could not safely locate customer dashboard logout."
    )

path.write_text(text, encoding="utf-8")


# ============================================================
# 4. ADD LOGOUT TESTS
# ============================================================

test_path = ROOT / "accounts/test_logout_security.py"

tests = r'''from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse


User = get_user_model()


class LogoutSecurityTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username="logout-test-user",
            email="logout@example.com",
            password="StrongPass123!",
            is_active=True,
        )

    def test_logout_get_is_not_used_for_state_change(self):
        self.client.force_login(self.user)

        response = self.client.get(
            reverse("logout")
        )

        self.assertEqual(
            response.status_code,
            405,
        )

        self.assertIn(
            "_auth_user_id",
            self.client.session,
        )

    def test_logout_post_logs_user_out(self):
        self.client.force_login(self.user)

        response = self.client.post(
            reverse("logout"),
            follow=False,
        )

        self.assertEqual(
            response.status_code,
            302,
        )

        self.assertNotIn(
            "_auth_user_id",
            self.client.session,
        )

    def test_logout_redirects_home(self):
        self.client.force_login(self.user)

        response = self.client.post(
            reverse("logout"),
            follow=False,
        )

        self.assertEqual(
            response.url,
            reverse("home"),
        )
'''

if test_path.exists():
    backup(test_path)

test_path.write_text(
    tests,
    encoding="utf-8",
)

print("[CREATED] accounts/test_logout_security.py")


# ============================================================
# 5. CHECK ACTIVE TEMPLATES FOR BAD LOGOUT LINKS
# ============================================================

bad_patterns = [
    'href="{% url \'logout\' %}"',
    'href="/accounts/logout/"',
]

active_files = [
    ROOT / "templates/includes/navbar.html",
    ROOT / "templates/dashboard/admin/base.html",
    ROOT / "templates/accounts/dashboard/dashboard.html",
]

for file in active_files:
    content = file.read_text(encoding="utf-8")

    for bad in bad_patterns:
        if bad in content:
            raise RuntimeError(
                f"Unsafe GET logout link still exists in {file}: {bad}"
            )

print("[PASS] No active GET logout links remain.")


# ============================================================
# 6. VALIDATION
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
        "accounts.test_logout_security",
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

print()
print("=" * 72)
print("RUNNING LOGOUT VALIDATION")
print("=" * 72)

for command in commands:

    print()
    print(">", " ".join(command))

    result = subprocess.run(
        command,
        cwd=ROOT,
    )

    if result.returncode != 0:

        print()
        print("=" * 72)
        print("VALIDATION FAILED")
        print("=" * 72)

        print("Backups:")
        print(BACKUP)

        raise SystemExit(
            result.returncode
        )


print()
print("=" * 72)
print("LOGOUT FIX PASSED")
print("=" * 72)

print()
print("✓ /accounts/logout/ route exists")
print("✓ Logout now uses POST")
print("✓ CSRF protection included")
print("✓ Customer navbar fixed")
print("✓ Customer dashboard fixed")
print("✓ Admin dashboard fixed")
print("✓ GET cannot silently log a user out")
print("✓ Successful logout redirects to home")
print("✓ Account tests passed")

print()
print("Backup:")
print(BACKUP)
