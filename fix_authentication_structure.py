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

stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
BACKUP = ROOT / ".auth_separation_backups" / stamp
BACKUP.mkdir(parents=True, exist_ok=True)


def backup(path):
    target = BACKUP / path.relative_to(ROOT)
    target.parent.mkdir(parents=True, exist_ok=True)

    if path.exists():
        shutil.copy2(path, target)


def write_file(relative_path, content):
    path = ROOT / relative_path

    if path.exists():
        backup(path)

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    path.write_text(
        content,
        encoding="utf-8",
    )

    print("[WRITE]", relative_path)


print("=" * 72)
print("AUTHENTICATION SEPARATION")
print("=" * 72)


# ============================================================
# 1. SETTINGS
# ============================================================

settings = ROOT / "config/settings.py"
backup(settings)

text = settings.read_text(
    encoding="utf-8-sig"
)

text = text.replace(
    'LOGIN_REDIRECT_URL = "/"',
    'LOGIN_REDIRECT_URL = "/shop/"',
)

if 'ACCOUNT_SIGNUP_REDIRECT_URL = "/shop/"' not in text:

    text = text.replace(
        'LOGIN_REDIRECT_URL = "/shop/"',
        '''LOGIN_REDIRECT_URL = "/shop/"
ACCOUNT_SIGNUP_REDIRECT_URL = "/shop/"
SOCIALACCOUNT_ADAPTER = "accounts.adapters.CustomerOnlySocialAccountAdapter"''',
        1,
    )

elif "SOCIALACCOUNT_ADAPTER" not in text:

    text += (
        '\nSOCIALACCOUNT_ADAPTER = '
        '"accounts.adapters.CustomerOnlySocialAccountAdapter"\n'
    )


settings.write_text(
    text,
    encoding="utf-8",
)

print("[UPDATE] config/settings.py")


# ============================================================
# 2. CUSTOMER-ONLY SOCIAL LOGIN ADAPTER
# ============================================================

write_file(
    "accounts/adapters.py",
'''from allauth.core.exceptions import ImmediateHttpResponse
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.shortcuts import redirect


class CustomerOnlySocialAccountAdapter(
    DefaultSocialAccountAdapter
):

    """
    Social login is customer-only.

    Staff and superusers must use their
    dedicated authentication entrances.
    """

    def _existing_user_for_social_login(
        self,
        sociallogin,
    ):

        user = sociallogin.user

        if getattr(user, "pk", None):
            return user

        email = (
            getattr(user, "email", "")
            or ""
        ).strip()

        if not email:

            email = (
                sociallogin
                .account
                .extra_data
                .get("email", "")
                or ""
            ).strip()

        if not email:
            return None

        User = get_user_model()

        return User.objects.filter(
            email__iexact=email
        ).first()


    def pre_social_login(
        self,
        request,
        sociallogin,
    ):

        super().pre_social_login(
            request,
            sociallogin,
        )

        existing = (
            self._existing_user_for_social_login(
                sociallogin
            )
        )

        if existing and (
            existing.is_staff
            or existing.is_superuser
            or getattr(
                existing,
                "role",
                None,
            ) == "admin"
        ):

            messages.error(
                request,
                (
                    "Store staff and system "
                    "administrators must use "
                    "their dedicated login."
                ),
            )

            raise ImmediateHttpResponse(
                redirect("staff_login")
            )


    def save_user(
        self,
        request,
        sociallogin,
        form=None,
    ):

        user = super().save_user(
            request,
            sociallogin,
            form=form,
        )

        # Google has verified the Google
        # account email. Keep this project's
        # custom verification flag synchronized.
        if (
            sociallogin.account.provider
            == "google"
            and user.email
            and not user.email_verified
        ):

            user.email_verified = True

            user.save(
                update_fields=[
                    "email_verified",
                ]
            )

        return user
'''
)


# ============================================================
# 3. STORE STAFF SECURITY DECORATOR
# ============================================================

write_file(
    "accounts/staff_auth.py",
'''from django.contrib.auth import REDIRECT_FIELD_NAME
from django.contrib.auth.decorators import user_passes_test


def staff_member_required(
    view_func=None,
    redirect_field_name=REDIRECT_FIELD_NAME,
    login_url="staff_login",
):

    """
    Protect store-management pages and redirect
    unauthenticated users to /staff/login/.
    """

    decorator = user_passes_test(
        lambda user: (
            user.is_active
            and user.is_staff
        ),
        login_url=login_url,
        redirect_field_name=redirect_field_name,
    )

    if view_func is not None:
        return decorator(view_func)

    return decorator
'''
)


# ============================================================
# 4. CUSTOMER + STAFF LOGIN VIEWS
# ============================================================

views = ROOT / "accounts/views.py"
backup(views)

text = views.read_text(
    encoding="utf-8-sig"
)

old = '''class RateLimitedLoginView(LoginView):
    template_name = "accounts/login.html"
'''

new = '''class RateLimitedLoginView(LoginView):
    template_name = "accounts/login.html"

    def form_valid(self, form):

        user = form.get_user()

        if (
            user.is_staff
            or user.is_superuser
            or getattr(
                user,
                "role",
                None,
            ) == "admin"
        ):

            form.add_error(
                None,
                (
                    "Store staff and system "
                    "administrators must use "
                    "their dedicated login."
                ),
            )

            return self.form_invalid(form)

        return super().form_valid(form)


@method_decorator(
    ratelimit(
        key="ip",
        rate="5/m",
        method="POST",
        block=True,
    ),
    name="dispatch",
)
class StoreStaffLoginView(LoginView):

    template_name = "accounts/staff_login.html"

    def form_valid(self, form):

        user = form.get_user()

        if not user.is_staff:

            form.add_error(
                None,
                (
                    "This login is only for "
                    "the store owner and "
                    "authorized staff."
                ),
            )

            return self.form_invalid(form)

        return super().form_valid(form)

    def get_success_url(self):

        return reverse(
            "admin_dashboard"
        )
'''

if old in text:

    text = text.replace(
        old,
        new,
        1,
    )

elif "class StoreStaffLoginView" not in text:

    raise RuntimeError(
        "Could not safely patch "
        "RateLimitedLoginView."
    )


views.write_text(
    text,
    encoding="utf-8",
)

print("[UPDATE] accounts/views.py")


# ============================================================
# 5. STAFF URL
# ============================================================

write_file(
    "accounts/staff_urls.py",
'''from django.urls import path

from .views import StoreStaffLoginView


urlpatterns = [

    path(
        "login/",
        StoreStaffLoginView.as_view(),
        name="staff_login",
    ),

]
'''
)


# ============================================================
# 6. ROOT URL
# ============================================================

urls = ROOT / "config/urls.py"
backup(urls)

text = urls.read_text(
    encoding="utf-8-sig"
)

admin_route = (
    "    path('admin/', admin.site.urls),"
)

if 'include("accounts.staff_urls")' not in text:

    if admin_route not in text:
        raise RuntimeError(
            "Could not locate Django admin URL."
        )

    text = text.replace(
        admin_route,
        '''    path(
        "staff/",
        include("accounts.staff_urls"),
    ),

''' + admin_route,
        1,
    )


urls.write_text(
    text,
    encoding="utf-8",
)

print("[UPDATE] config/urls.py")


# ============================================================
# 7. STAFF LOGIN PAGE
# ============================================================

write_file(
    "templates/accounts/staff_login.html",
'''{% extends "base.html" %}

{% block content %}

<div
    class="container py-5"
    style="max-width: 430px;"
>

    <div class="card border-0 shadow-sm">

        <div class="card-body p-4">

            <h2 class="mb-2">
                Store Staff Login
            </h2>

            <p class="text-muted mb-4">
                For the store owner and
                authorized staff only.
            </p>

            <form method="post">

                {% csrf_token %}

                {{ form.as_p }}

                <button
                    type="submit"
                    class="btn btn-primary w-100"
                >
                    Sign in to Store Dashboard
                </button>

            </form>

            <div class="text-center mt-3">

                <a href="{% url 'login' %}">
                    Customer login
                </a>

            </div>

        </div>

    </div>

</div>

{% endblock %}
'''
)


# ============================================================
# 8. CHANGE STORE MANAGEMENT DECORATORS
# ============================================================

packages = [
    "dashboard",
    "crm",
    "delivery",
    "inventory",
    "payments",
    "core",
]

changed = []

for package in packages:

    folder = ROOT / package

    if not folder.exists():
        continue

    for path in folder.rglob("*.py"):

        original = path.read_text(
            encoding="utf-8-sig"
        )

        updated = original.replace(
            (
                "from django.contrib.admin.views."
                "decorators import"
            ),
            "from accounts.staff_auth import",
        )

        if updated != original:

            backup(path)

            path.write_text(
                updated,
                encoding="utf-8",
            )

            changed.append(
                str(path.relative_to(ROOT))
            )


print(
    "[UPDATE] Dedicated staff authentication "
    f"applied to {len(changed)} files"
)

for item in changed:
    print("   ", item)


# ============================================================
# 9. TESTS
# ============================================================

write_file(
    "accounts/test_auth_separation.py",
'''from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse


User = get_user_model()


class AuthenticationSeparationTests(TestCase):

    def setUp(self):

        self.customer = User.objects.create_user(
            username="customer-auth-test",
            email="customer-auth@example.com",
            password="StrongPass123!",
            is_active=True,
            is_staff=False,
        )

        self.staff = User.objects.create_user(
            username="staff-auth-test",
            email="staff-auth@example.com",
            password="StrongPass123!",
            is_active=True,
            is_staff=True,
            role="admin",
        )

        self.superuser = (
            User.objects.create_superuser(
                username="system-auth-test",
                email="system-auth@example.com",
                password="StrongPass123!",
            )
        )


    def test_customer_login_lands_on_shop(self):

        response = self.client.post(
            reverse("login"),
            {
                "username":
                    self.customer.username,
                "password":
                    "StrongPass123!",
            },
        )

        self.assertRedirects(
            response,
            reverse("shop"),
            fetch_redirect_response=False,
        )


    def test_staff_cannot_use_customer_login(self):

        response = self.client.post(
            reverse("login"),
            {
                "username":
                    self.staff.username,
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


    def test_staff_login_accepts_staff(self):

        response = self.client.post(
            reverse("staff_login"),
            {
                "username":
                    self.staff.username,
                "password":
                    "StrongPass123!",
            },
        )

        self.assertRedirects(
            response,
            reverse("admin_dashboard"),
            fetch_redirect_response=False,
        )


    def test_customer_cannot_use_staff_login(self):

        response = self.client.post(
            reverse("staff_login"),
            {
                "username":
                    self.customer.username,
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


    def test_store_dashboard_uses_staff_login(self):

        response = self.client.get(
            reverse("admin_dashboard")
        )

        self.assertEqual(
            response.status_code,
            302,
        )

        self.assertTrue(
            response.url.startswith(
                reverse("staff_login")
            )
        )


    def test_customer_cannot_open_store_dashboard(self):

        self.client.force_login(
            self.customer
        )

        response = self.client.get(
            reverse("admin_dashboard")
        )

        self.assertEqual(
            response.status_code,
            302,
        )

        self.assertTrue(
            response.url.startswith(
                reverse("staff_login")
            )
        )


    def test_customer_login_redirect_setting(self):

        self.assertEqual(
            settings.LOGIN_REDIRECT_URL,
            "/shop/",
        )

        self.assertEqual(
            settings.ACCOUNT_SIGNUP_REDIRECT_URL,
            "/shop/",
        )


    def test_customer_only_social_adapter(self):

        self.assertEqual(
            settings.SOCIALACCOUNT_ADAPTER,
            (
                "accounts.adapters."
                "CustomerOnlySocialAccountAdapter"
            ),
        )
'''
)


# ============================================================
# 10. VALIDATE
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


print()
print("=" * 72)
print("RUNNING AUTHENTICATION TESTS")
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
        print("VALIDATION FAILED")
        print("Backup:", BACKUP)

        raise SystemExit(
            result.returncode
        )


print()
print("=" * 72)
print("AUTHENTICATION SEPARATION PASSED")
print("=" * 72)

print()
print("Customer:")
print("  /accounts/login/")
print("  Google + password")
print("  -> /shop/")

print()
print("Store owner / staff:")
print("  /staff/login/")
print("  password only")
print("  -> /dashboard/admin/")

print()
print("System superadmin:")
print("  /admin/login/")
print("  Django admin authentication")

print()
print("Backup:")
print(BACKUP)

