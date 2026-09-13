from pathlib import Path
from datetime import datetime
import shutil
import subprocess
import sys


ROOT = Path.cwd()

if not (ROOT / "manage.py").exists():
    raise SystemExit(
        "ERROR: Run this from the Django project root containing manage.py."
    )


# ============================================================
# BACKUP
# ============================================================

stamp = datetime.now().strftime("%Y%m%d-%H%M%S")

backup_dir = (
    ROOT
    / ".system_admin_backups"
    / stamp
)

backup_dir.mkdir(
    parents=True,
    exist_ok=True,
)


def backup(path):

    if not path.exists():
        return

    destination = (
        backup_dir
        / path.relative_to(ROOT)
    )

    destination.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    shutil.copy2(
        path,
        destination,
    )


urls_file = ROOT / "config" / "urls.py"
views_file = ROOT / "accounts" / "views.py"
base_file = ROOT / "templates" / "dashboard" / "admin" / "base.html"
system_admin_file = ROOT / "accounts" / "system_admin.py"
test_file = ROOT / "accounts" / "test_system_admin_separation.py"


for path in [
    urls_file,
    views_file,
    base_file,
    system_admin_file,
    test_file,
]:
    backup(path)


# ============================================================
# 1. CREATE STRICT DJANGO ADMIN CONFIGURATION
# ============================================================

system_admin_file.write_text(
r'''from django.contrib import admin
from django.contrib.admin.forms import AdminAuthenticationForm
from django.core.exceptions import ValidationError


class SuperuserOnlyAdminAuthenticationForm(
    AdminAuthenticationForm
):

    def confirm_login_allowed(self, user):

        super().confirm_login_allowed(user)

        if not user.is_superuser:

            raise ValidationError(
                (
                    "System administrator access only. "
                    "Store staff must use the Store Staff Login."
                ),
                code="not_system_administrator",
            )


def system_admin_has_permission(request):

    user = request.user

    return bool(
        user.is_authenticated
        and user.is_active
        and user.is_superuser
    )


def configure_system_admin_site():

    # Django normally allows any active is_staff user.
    # This project separates Store Staff from System Admin.
    admin.site.has_permission = (
        system_admin_has_permission
    )

    admin.site.login_form = (
        SuperuserOnlyAdminAuthenticationForm
    )
''',
    encoding="utf-8",
)

print(
    "[CREATED] accounts/system_admin.py"
)


# ============================================================
# 2. LOAD STRICT ADMIN CONFIG BEFORE admin.site.urls
# ============================================================

urls_text = urls_file.read_text(
    encoding="utf-8-sig"
)

import_line = (
    "from accounts.system_admin "
    "import configure_system_admin_site"
)

if import_line not in urls_text:

    marker = (
        "from core.sitemaps import sitemaps"
    )

    if marker not in urls_text:

        raise SystemExit(
            "ERROR: Could not locate config/urls.py import marker."
        )

    urls_text = urls_text.replace(
        marker,
        (
            marker
            + "\n"
            + import_line
        ),
        1,
    )


setup_call = "configure_system_admin_site()"

if setup_call not in urls_text:

    marker = "urlpatterns = ["

    if marker not in urls_text:

        raise SystemExit(
            "ERROR: Could not locate urlpatterns in config/urls.py."
        )

    urls_text = urls_text.replace(
        marker,
        (
            "configure_system_admin_site()\n\n\n"
            + marker
        ),
        1,
    )


urls_file.write_text(
    urls_text,
    encoding="utf-8",
)

print(
    "[PATCHED] config/urls.py"
)


# ============================================================
# 3. REJECT SUPERUSERS FROM STORE STAFF LOGIN
# ============================================================

views_text = views_file.read_text(
    encoding="utf-8-sig"
)


old = '''        user = form.get_user()

        if not can_access_store_management(user):
'''


new = '''        user = form.get_user()

        if user.is_superuser:

            form.add_error(
                None,
                (
                    "System administrators must use "
                    "the System Admin login."
                ),
            )

            return self.form_invalid(form)

        if not can_access_store_management(user):
'''


# Only patch inside StoreStaffLoginView.
class_marker = "class StoreStaffLoginView(LoginView):"

if class_marker not in views_text:

    raise SystemExit(
        "ERROR: StoreStaffLoginView was not found."
    )


before, staff_section = views_text.split(
    class_marker,
    1,
)


if (
    "System administrators must use"
    not in staff_section
):

    if old not in staff_section:

        raise SystemExit(
            "ERROR: Could not safely locate StoreStaffLoginView form_valid."
        )

    staff_section = staff_section.replace(
        old,
        new,
        1,
    )


views_text = (
    before
    + class_marker
    + staff_section
)


views_file.write_text(
    views_text,
    encoding="utf-8",
)

print(
    "[PATCHED] Superusers cannot log in through /staff/login/."
)


# ============================================================
# 4. HIDE DJANGO ADMIN LINK FROM ORDINARY STORE STAFF
# ============================================================

base_text = base_file.read_text(
    encoding="utf-8-sig"
)


admin_link = '''                        <li>

                            <a
                                class="dropdown-item"
                                href="{% url 'admin:index' %}"
                            >

                                <i class="bi bi-tools me-2"></i>

                                Django Admin

                            </a>

                        </li>


                        <li>

                            <hr class="dropdown-divider">

                        </li>
'''


protected_admin_link = '''                        {% if request.user.is_superuser %}

                        <li>

                            <a
                                class="dropdown-item"
                                href="{% url 'admin:index' %}"
                            >

                                <i class="bi bi-tools me-2"></i>

                                Django Admin

                            </a>

                        </li>


                        <li>

                            <hr class="dropdown-divider">

                        </li>

                        {% endif %}
'''


if (
    "{% if request.user.is_superuser %}"
    not in base_text
    or "Django Admin" not in base_text
):

    if admin_link not in base_text:

        raise SystemExit(
            "ERROR: Could not safely locate Django Admin topbar link."
        )

    base_text = base_text.replace(
        admin_link,
        protected_admin_link,
        1,
    )


base_file.write_text(
    base_text,
    encoding="utf-8",
)

print(
    "[PATCHED] Django Admin link is now superuser-only."
)


# ============================================================
# 5. CREATE SECURITY REGRESSION TESTS
# ============================================================

test_file.write_text(
r'''from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from accounts.store_roles import (
    STORE_OWNER,
)


User = get_user_model()


class SystemAdminSeparationTests(TestCase):

    @classmethod
    def setUpTestData(cls):

        call_command(
            "setup_store_roles"
        )

        cls.store_owner = (
            User.objects.create_user(
                username="store-owner-separation",
                email="store-owner-separation@example.com",
                password="StrongPass123!",
                is_active=True,
                is_staff=True,
                role="admin",
            )
        )

        cls.store_owner.groups.add(
            Group.objects.get(
                name=STORE_OWNER
            )
        )


        cls.regular_staff = (
            User.objects.create_user(
                username="regular-staff-separation",
                email="regular-staff-separation@example.com",
                password="StrongPass123!",
                is_active=True,
                is_staff=True,
                role="admin",
            )
        )


        cls.superuser = (
            User.objects.create_superuser(
                username="system-admin-separation",
                email="system-admin-separation@example.com",
                password="StrongPass123!",
            )
        )


    # ========================================================
    # DJANGO ADMIN
    # ========================================================

    def test_anonymous_can_open_system_admin_login(self):

        response = self.client.get(
            reverse(
                "admin:login"
            )
        )

        self.assertEqual(
            response.status_code,
            200,
        )


    def test_store_owner_cannot_open_django_admin(self):

        self.client.force_login(
            self.store_owner
        )

        response = self.client.get(
            reverse(
                "admin:index"
            )
        )

        self.assertEqual(
            response.status_code,
            302,
        )

        self.assertTrue(
            response.url.startswith(
                reverse(
                    "admin:login"
                )
            )
        )


    def test_plain_is_staff_cannot_open_django_admin(self):

        self.client.force_login(
            self.regular_staff
        )

        response = self.client.get(
            reverse(
                "admin:index"
            )
        )

        self.assertEqual(
            response.status_code,
            302,
        )

        self.assertTrue(
            response.url.startswith(
                reverse(
                    "admin:login"
                )
            )
        )


    def test_store_owner_credentials_rejected_by_admin_login(
        self
    ):

        response = self.client.post(
            reverse(
                "admin:login"
            ),
            {
                "username":
                    self.store_owner.username,

                "password":
                    "StrongPass123!",

                "next":
                    reverse(
                        "admin:index"
                    ),
            },
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertNotIn(
            "_auth_user_id",
            self.client.session,
        )

        self.assertContains(
            response,
            "System administrator access only",
        )


    def test_superuser_can_open_django_admin(self):

        self.client.force_login(
            self.superuser
        )

        response = self.client.get(
            reverse(
                "admin:index"
            )
        )

        self.assertEqual(
            response.status_code,
            200,
        )


    # ========================================================
    # STORE STAFF LOGIN
    # ========================================================

    def test_store_owner_can_use_staff_login(self):

        response = self.client.post(
            reverse(
                "staff_login"
            ),
            {
                "username":
                    self.store_owner.username,

                "password":
                    "StrongPass123!",
            },
        )

        self.assertRedirects(
            response,
            reverse(
                "admin_dashboard"
            ),
            fetch_redirect_response=False,
        )


    def test_superuser_cannot_use_staff_login(self):

        response = self.client.post(
            reverse(
                "staff_login"
            ),
            {
                "username":
                    self.superuser.username,

                "password":
                    "StrongPass123!",
            },
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertNotIn(
            "_auth_user_id",
            self.client.session,
        )

        self.assertContains(
            response,
            "System administrators must use",
        )


    # ========================================================
    # UI
    # ========================================================

    def test_store_owner_does_not_see_django_admin_link(self):

        self.client.force_login(
            self.store_owner
        )

        response = self.client.get(
            reverse(
                "admin_dashboard"
            )
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertNotContains(
            response,
            "Django Admin",
        )


    def test_superuser_sees_django_admin_link_on_store_dashboard(
        self
    ):

        self.client.force_login(
            self.superuser
        )

        response = self.client.get(
            reverse(
                "admin_dashboard"
            )
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertContains(
            response,
            "Django Admin",
        )


    # ========================================================
    # THREE LOGIN ENTRANCES
    # ========================================================

    def test_customer_staff_and_system_admin_urls_are_distinct(
        self
    ):

        self.assertEqual(
            reverse(
                "login"
            ),
            "/accounts/login/",
        )

        self.assertEqual(
            reverse(
                "staff_login"
            ),
            "/staff/login/",
        )

        self.assertEqual(
            reverse(
                "admin:login"
            ),
            "/admin/login/",
        )
''',
    encoding="utf-8",
)

print(
    "[CREATED] accounts/test_system_admin_separation.py"
)


# ============================================================
# 6. IGNORE LOCAL BACKUPS
# ============================================================

gitignore = ROOT / ".gitignore"

if gitignore.exists():

    ignore_text = gitignore.read_text(
        encoding="utf-8-sig"
    )

    entry = ".system_admin_backups/"

    if entry not in ignore_text:

        if not ignore_text.endswith("\n"):
            ignore_text += "\n"

        ignore_text += (
            "\n# Local security patch backups\n"
            + entry
            + "\n"
        )

        gitignore.write_text(
            ignore_text,
            encoding="utf-8",
        )


# ============================================================
# 7. TARGETED VALIDATION
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
        "accounts.test_system_admin_separation",
        "-v",
        "2",
    ],

    [
        sys.executable,
        "manage.py",
        "test",
        "accounts.test_auth_separation",
        "accounts.test_staff_management",
        "accounts.test_store_role_permissions",
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
    print("=" * 72)
    print(
        ">",
        " ".join(
            command
        )
    )
    print("=" * 72)

    result = subprocess.run(
        command,
        cwd=ROOT,
    )

    if result.returncode != 0:

        print()
        print("=" * 72)
        print(
            "SYSTEM ADMIN SEPARATION VALIDATION FAILED"
        )
        print("=" * 72)

        print()
        print(
            "Do not weaken the access rules."
        )

        print(
            "Send the exact failing test output."
        )

        print()
        print(
            "Backup directory:"
        )

        print(
            backup_dir
        )

        raise SystemExit(
            result.returncode
        )


print()
print("=" * 72)
print(
    "STRICT SYSTEM ADMIN SEPARATION PASSED"
)
print("=" * 72)

print()
print(
    "Customer:"
)
print(
    "  /accounts/login/"
)

print()
print(
    "Store Staff:"
)
print(
    "  /staff/login/"
)

print()
print(
    "System Administrator:"
)
print(
    "  /admin/login/"
)

print()
print(
    "Security rules:"
)

print(
    "  - Store Owner is NOT automatically a Django administrator."
)

print(
    "  - is_staff=True cannot enter Django Admin."
)

print(
    "  - Only is_superuser=True can enter Django Admin."
)

print(
    "  - Superusers cannot authenticate through Store Staff Login."
)

print(
    "  - Django Admin link is hidden from normal store staff."
)

print()
print(
    "Backup directory:"
)

print(
    backup_dir
)

print()
print(
    "FINAL FULL-SUITE COMMAND:"
)

print(
    "python manage.py test -v 1"
)

