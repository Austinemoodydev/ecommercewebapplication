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

stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
BACKUP = ROOT / ".auth_ux_backups" / stamp
BACKUP.mkdir(parents=True, exist_ok=True)


def backup(path):
    if not path.exists():
        return

    target = BACKUP / path.relative_to(ROOT)
    target.parent.mkdir(parents=True, exist_ok=True)

    shutil.copy2(
        path,
        target,
    )


def write(rel, content):

    path = ROOT / rel

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

    print("[UPDATED]", rel)


print("=" * 72)
print("PROFESSIONAL AUTHENTICATION UX")
print("=" * 72)
print()


# ============================================================
# 1. AUTH BASE
#    One consistent authentication design
# ============================================================

write(
    "templates/accounts/auth_base.html",
r'''{% load static %}
<!DOCTYPE html>

<html lang="en">

<head>

    <meta charset="UTF-8">

    <meta
        name="viewport"
        content="width=device-width, initial-scale=1"
    >

    <title>
        {% block title %}
        OnlineShop
        {% endblock %}
    </title>

    <meta
        name="description"
        content="Securely sign in or create your OnlineShop account."
    >

    <link
        href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.7/dist/css/bootstrap.min.css"
        rel="stylesheet"
    >

    <link
        href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.13.1/font/bootstrap-icons.min.css"
        rel="stylesheet"
    >

    <link
        href="{% static 'css/auth.css' %}"
        rel="stylesheet"
    >

</head>


<body>

<div class="container">

    <div
        class="row justify-content-center align-items-center"
        style="min-height: 100vh;"
    >

        <div class="col-lg-5 col-md-7">

            <div class="card shadow-lg border-0 rounded-4">

                <div class="card-body p-4 p-md-5">


                    <div class="text-center mb-4">

                        <a
                            href="{% url 'home' %}"
                            class="text-decoration-none"
                        >

                            <img
                                src="{% static 'images/logo.png' %}"
                                width="82"
                                alt="OnlineShop"
                            >

                        </a>


                        <h2 class="mt-3 mb-1">

                            OnlineShop

                        </h2>


                        <p class="text-muted mb-0">

                            Secure shopping.
                            Simple checkout.

                        </p>

                    </div>


                    {% if messages %}

                        {% for message in messages %}

                            <div
                                class="alert
                                {% if message.tags == 'error' %}
                                    alert-danger
                                {% elif message.tags == 'success' %}
                                    alert-success
                                {% elif message.tags == 'warning' %}
                                    alert-warning
                                {% else %}
                                    alert-info
                                {% endif %}
                                "
                                role="alert"
                            >

                                {{ message }}

                            </div>

                        {% endfor %}

                    {% endif %}


                    {% block content %}
                    {% endblock %}


                    <div
                        class="text-center mt-4 pt-3 border-top"
                    >

                        <a
                            href="{% url 'home' %}"
                            class="small text-muted"
                        >

                            <i class="bi bi-arrow-left me-1"></i>

                            Back to store

                        </a>

                    </div>


                </div>

            </div>

        </div>

    </div>

</div>


<script src="{% static 'js/auth.js' %}"></script>

</body>

</html>
'''
)


# ============================================================
# 2. CUSTOMER LOGIN
# ============================================================

write(
    "templates/accounts/login.html",
r'''{% extends "accounts/auth_base.html" %}
{% load socialaccount %}

{% block title %}
Sign in | OnlineShop
{% endblock %}


{% block content %}


<div class="text-center mb-4">

    <h3 class="mb-1">
        Welcome back
    </h3>

    <p class="text-muted mb-0">
        Sign in to continue shopping,
        track orders and manage your account.
    </p>

</div>


<form method="post">

    {% csrf_token %}


    {% if form.non_field_errors %}

        <div class="alert alert-danger">

            {% for error in form.non_field_errors %}

                <div>
                    {{ error }}
                </div>

            {% endfor %}

        </div>

    {% endif %}


    <div class="mb-3">

        <label
            for="{{ form.username.id_for_label }}"
            class="form-label"
        >
            Username
        </label>

        {{ form.username }}

        {% for error in form.username.errors %}

            <div class="text-danger small mt-1">
                {{ error }}
            </div>

        {% endfor %}

    </div>


    <div class="mb-2">

        <label
            for="{{ form.password.id_for_label }}"
            class="form-label"
        >
            Password
        </label>

        {{ form.password }}

        {% for error in form.password.errors %}

            <div class="text-danger small mt-1">
                {{ error }}
            </div>

        {% endfor %}

    </div>


    <div class="text-end mb-4">

        <a
            href="{% url 'password_reset' %}"
            class="small"
        >
            Forgot password?
        </a>

    </div>


    {% if next %}

        <input
            type="hidden"
            name="next"
            value="{{ next }}"
        >

    {% endif %}


    <button
        type="submit"
        class="btn btn-primary w-100 py-2"
    >

        Sign in

    </button>

</form>


<div
    class="d-flex align-items-center my-4"
>

    <hr class="flex-grow-1">

    <span class="text-muted small px-3">
        OR
    </span>

    <hr class="flex-grow-1">

</div>


<a
    class="btn btn-outline-secondary w-100 py-2"
    href="{% provider_login_url 'google' %}"
>

    <i class="bi bi-google me-2"></i>

    Continue with Google

</a>


<div
    class="text-center mt-4"
>

    <span class="text-muted">
        New to OnlineShop?
    </span>

    <a
        href="{% url 'register' %}"
        class="ms-1 fw-semibold"
    >
        Create an account
    </a>

</div>

{% endblock %}
'''
)


# ============================================================
# 3. CUSTOMER REGISTRATION
# ============================================================

write(
    "templates/accounts/register.html",
r'''{% extends "accounts/auth_base.html" %}
{% load socialaccount %}

{% block title %}
Create account | OnlineShop
{% endblock %}


{% block content %}


<div class="text-center mb-4">

    <h3 class="mb-1">
        Create your account
    </h3>

    <p class="text-muted mb-0">
        Join OnlineShop for faster checkout,
        order tracking and saved addresses.
    </p>

</div>


<form method="post">

    {% csrf_token %}


    {% if form.non_field_errors %}

        <div class="alert alert-danger">

            {% for error in form.non_field_errors %}

                <div>
                    {{ error }}
                </div>

            {% endfor %}

        </div>

    {% endif %}


    <div class="mb-3">

        <label class="form-label">
            Username
        </label>

        {{ form.username }}

        {% for error in form.username.errors %}
            <div class="text-danger small mt-1">
                {{ error }}
            </div>
        {% endfor %}

    </div>


    <div class="mb-3">

        <label class="form-label">
            Email address
        </label>

        {{ form.email }}

        {% for error in form.email.errors %}
            <div class="text-danger small mt-1">
                {{ error }}
            </div>
        {% endfor %}

    </div>


    <div class="mb-3">

        <label class="form-label">
            Phone
        </label>

        {{ form.phone }}

        {% for error in form.phone.errors %}
            <div class="text-danger small mt-1">
                {{ error }}
            </div>
        {% endfor %}

    </div>


    <div class="mb-3">

        <label class="form-label">
            Password
        </label>

        <div class="input-group">

            {{ form.password1 }}

            <button
                type="button"
                class="btn btn-outline-secondary"
                onclick="togglePassword('id_password1')"
                aria-label="Show password"
            >

                <i class="bi bi-eye"></i>

            </button>

        </div>

        {% for error in form.password1.errors %}
            <div class="text-danger small mt-1">
                {{ error }}
            </div>
        {% endfor %}

    </div>


    <div class="mb-3">

        <label class="form-label">
            Confirm password
        </label>

        <div class="input-group">

            {{ form.password2 }}

            <button
                type="button"
                class="btn btn-outline-secondary"
                onclick="togglePassword('id_password2')"
                aria-label="Show password"
            >

                <i class="bi bi-eye"></i>

            </button>

        </div>

        {% for error in form.password2.errors %}
            <div class="text-danger small mt-1">
                {{ error }}
            </div>
        {% endfor %}

    </div>


    <div class="form-check mb-4">

        <input
            class="form-check-input"
            type="checkbox"
            id="termsAccepted"
            required
        >

        <label
            class="form-check-label"
            for="termsAccepted"
        >

            I agree to the

            <a
                href="{% url 'terms' %}"
                target="_blank"
                rel="noopener"
            >
                Terms &amp; Conditions
            </a>

            and

            <a
                href="{% url 'privacy' %}"
                target="_blank"
                rel="noopener"
            >
                Privacy Policy
            </a>.

        </label>

    </div>


    <button
        type="submit"
        class="btn btn-primary w-100 py-2"
    >

        Create account

    </button>

</form>


<div
    class="d-flex align-items-center my-4"
>

    <hr class="flex-grow-1">

    <span class="text-muted small px-3">
        OR
    </span>

    <hr class="flex-grow-1">

</div>


<a
    class="btn btn-outline-secondary w-100 py-2"
    href="{% provider_login_url 'google' %}"
>

    <i class="bi bi-google me-2"></i>

    Sign up with Google

</a>


<div class="text-center mt-4">

    <span class="text-muted">
        Already have an account?
    </span>

    <a
        href="{% url 'login' %}"
        class="ms-1 fw-semibold"
    >
        Sign in
    </a>

</div>


{% endblock %}
'''
)


# ============================================================
# 4. STORE STAFF LOGIN
#    No public registration.
# ============================================================

write(
    "templates/accounts/staff_login.html",
r'''{% extends "accounts/auth_base.html" %}

{% block title %}
Store portal | OnlineShop
{% endblock %}


{% block content %}


<div class="text-center mb-4">

    <div
        class="d-inline-flex align-items-center
               justify-content-center
               bg-primary-subtle text-primary
               rounded-circle mb-3"
        style="width: 54px; height: 54px;"
    >

        <i class="bi bi-shop fs-4"></i>

    </div>


    <h3 class="mb-1">
        Store Portal
    </h3>

    <p class="text-muted mb-0">
        Secure access for authorized
        store owners and staff.
    </p>

</div>


<form method="post">

    {% csrf_token %}


    {% if form.non_field_errors %}

        <div class="alert alert-danger">

            {% for error in form.non_field_errors %}

                <div>
                    {{ error }}
                </div>

            {% endfor %}

        </div>

    {% endif %}


    <div class="mb-3">

        <label
            for="{{ form.username.id_for_label }}"
            class="form-label"
        >
            Username
        </label>

        {{ form.username }}

    </div>


    <div class="mb-4">

        <label
            for="{{ form.password.id_for_label }}"
            class="form-label"
        >
            Password
        </label>

        {{ form.password }}

    </div>


    {% if next %}

        <input
            type="hidden"
            name="next"
            value="{{ next }}"
        >

    {% endif %}


    <button
        type="submit"
        class="btn btn-primary w-100 py-2"
    >

        <i class="bi bi-shield-lock me-2"></i>

        Access Store Portal

    </button>

</form>


<div
    class="alert alert-light border mt-4 mb-0 small"
>

    <i class="bi bi-info-circle me-1 text-primary"></i>

    Staff accounts are created by an
    authorized administrator.
    Public staff registration is disabled.

</div>


<div class="text-center mt-4">

    <a href="{% url 'login' %}">
        Customer sign in
    </a>

</div>


{% endblock %}
'''
)


# ============================================================
# 5. FIX GOOGLE PRIVILEGED-EMAIL EXPERIENCE
# ============================================================

adapter = ROOT / "accounts/adapters.py"

if not adapter.exists():
    raise RuntimeError(
        "accounts/adapters.py was not found."
    )

backup(adapter)

text = adapter.read_text(
    encoding="utf-8-sig"
)


old_message = '''                    "Store staff and system "
                    "administrators must use "
                    "their dedicated login."'''

new_message = '''                    "This email belongs to a staff or "
                    "system administrator account. "
                    "For security, privileged accounts "
                    "cannot use customer Google sign-in. "
                    "Use the appropriate staff/admin portal, "
                    "or use a separate customer account "
                    "for shopping."'''

text = text.replace(
    old_message,
    new_message,
)


old_redirect = '''            raise ImmediateHttpResponse(
                redirect("staff_login")
            )'''

new_redirect = '''            raise ImmediateHttpResponse(
                redirect("login")
            )'''

if old_redirect not in text:

    if 'redirect("login")' in text:
        print(
            "[OK] Google privileged-account redirect "
            "already returns to customer login."
        )
    else:
        raise RuntimeError(
            "Could not safely locate privileged Google redirect."
        )

else:

    text = text.replace(
        old_redirect,
        new_redirect,
        1,
    )


adapter.write_text(
    text,
    encoding="utf-8",
)

print(
    "[UPDATED] accounts/adapters.py"
)


# ============================================================
# 6. IMPROVE AUTH FORM INPUT CLASSES
# ============================================================

forms = ROOT / "accounts/forms.py"
backup(forms)

text = forms.read_text(
    encoding="utf-8-sig"
)


register_marker = '''    class Meta:

        model = CustomUser

        fields = (
            "username",
            "email",
            "phone",
            "password1",
            "password2",
        )
'''

register_replacement = '''    class Meta:

        model = CustomUser

        fields = (
            "username",
            "email",
            "phone",
            "password1",
            "password2",
        )

        widgets = {
            "username": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "autocomplete": "username",
                    "placeholder": "Choose a username",
                }
            ),
            "email": forms.EmailInput(
                attrs={
                    "class": "form-control",
                    "autocomplete": "email",
                    "placeholder": "you@example.com",
                }
            ),
            "phone": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "autocomplete": "tel",
                    "placeholder": "07XXXXXXXX",
                }
            ),
        }

    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)

        self.fields["password1"].widget.attrs.update(
            {
                "class": "form-control",
                "autocomplete": "new-password",
                "placeholder": "Create a password",
            }
        )

        self.fields["password2"].widget.attrs.update(
            {
                "class": "form-control",
                "autocomplete": "new-password",
                "placeholder": "Confirm your password",
            }
        )
'''

if register_marker in text:

    text = text.replace(
        register_marker,
        register_replacement,
        1,
    )

elif '"placeholder": "Choose a username"' in text:

    print(
        "[OK] RegisterForm styling already present."
    )

else:

    raise RuntimeError(
        "Could not safely update RegisterForm widgets."
    )


forms.write_text(
    text,
    encoding="utf-8",
)

print(
    "[UPDATED] accounts/forms.py"
)


# ============================================================
# 7. ADD AUTH UX TESTS
# ============================================================

write(
    "accounts/test_auth_ux.py",
r'''from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse


User = get_user_model()


class AuthenticationUXTests(TestCase):

    def test_customer_login_has_registration(self):

        response = self.client.get(
            reverse("login")
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertContains(
            response,
            "Create an account",
        )

        self.assertContains(
            response,
            "Continue with Google",
        )

        self.assertNotContains(
            response,
            "Store Staff Login",
        )


    def test_register_page_exists(self):

        response = self.client.get(
            reverse("register")
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertContains(
            response,
            "Create your account",
        )

        self.assertContains(
            response,
            "Terms &amp; Conditions",
        )


    def test_staff_login_has_no_public_registration(self):

        response = self.client.get(
            reverse("staff_login")
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertContains(
            response,
            "Store Portal",
        )

        self.assertContains(
            response,
            "Public staff registration is disabled",
        )

        self.assertNotContains(
            response,
            "Create an account",
        )


    def test_customer_cannot_use_staff_login(self):

        customer = User.objects.create_user(
            username="auth-ux-customer",
            email="auth-ux@example.com",
            password="StrongPass123!",
            is_active=True,
            is_staff=False,
        )

        response = self.client.post(
            reverse("staff_login"),
            {
                "username": customer.username,
                "password": "StrongPass123!",
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
'''
)


# ============================================================
# 8. VALIDATION
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
        "accounts.test_auth_ux",
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


print()
print("=" * 72)
print("RUNNING AUTH VALIDATION")
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
        print("AUTH VALIDATION FAILED")
        print("=" * 72)

        print()
        print("Backup:")
        print(BACKUP)

        raise SystemExit(
            result.returncode
        )


print()
print("=" * 72)
print("PROFESSIONAL AUTH UX APPLIED")
print("=" * 72)

print()
print("CUSTOMERS")
print("  /accounts/login/")
print("  Password + Google")
print("  Public registration enabled")
print("  -> /shop/")

print()
print("STORE OWNER / STAFF")
print("  /staff/login/")
print("  Password only")
print("  No public registration")
print("  -> /dashboard/admin/")

print()
print("SYSTEM SUPERADMIN")
print("  /admin/login/")
print("  Password only")
print("  No public registration")
print("  -> /admin/")

print()
print(
    "IMPORTANT: A staff/superadmin email cannot "
    "be used for customer Google login."
)

print()
print("Backup:")
print(BACKUP)

